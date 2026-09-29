"""Sales Persona: a daily sales copilot (briefings, account research, call prep, email drafts,
competitor updates) that answers from stored project data and allow-listed live lookups only.

Sits beside the scoped Advisor and never changes the scan/scoring pipeline: it only reads stored
signals, scores and chunks, and (optionally) fetches allow-listed official pages. Emails are drafts.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.embeddings import EmbeddingAdapter
from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.repositories import document_chunks as chunks_repo
from app.repositories import evidence as evidence_repo
from app.repositories import opportunities as opportunities_repo
from app.repositories import opportunity_scores as scores_repo
from app.repositories import signals as signals_repo
from app.repositories.organizations import Organization
from app.schemas.persona import (
    PersonaAnswer,
    PersonaBlock,
    PersonaBulletItem,
    PersonaHistoryTurn,
    PersonaResponse,
    PersonaSource,
    PersonaUsed,
)
from app.services import competitors as competitors_service
from app.services import dashboard as dashboard_service
from app.services import persona_lookup
from app.services.advisor import _strip_internal_ids

logger = logging.getLogger("app.services.persona")

_MAX_FOCUS_ORGS = 3
_SIGNALS_PER_ORG = 6
_RAG_POOL_PER_ORG = 8
_RAG_CHUNKS_PER_ORG = 3
_RAG_MIN_CHUNK_CHARS = 40
# Stricter than the Advisor gate: the persona mixes several sources, so weak matches are noise.
_RAG_MIN_SIMILARITY = 0.78
_RAG_KEYWORD_BONUS = 0.05
_CONTEXT_CHUNK_CHARS = 350
_MAX_CONTEXT_CHARS = 10_000
_MAX_BLOCKS = 8
_MAX_ITEMS = 12
_MAX_TABLE_COLS = 6
_MAX_TABLE_ROWS = 8
_LAYERS = frozenset({"fact", "interpretation", "potential_opportunity", "recommended_action"})
_WEB_WORDS = re.compile(
    r"\b(latest|news|recent|recently|today|search|look ?up|online|web|what'?s new|announce\w*)\b",
    re.I,
)
_COMPETITOR_WORDS = re.compile(r"\b(competitors?|vendors?|rivals?)\b", re.I)
_EMAIL_REQUEST = re.compile(
    r"\b(e-?mails?|draft|outreach|cold (call|email)|follow[- ]?up|reach out|write (to|a|an))\b",
    re.I,
)
_TOKEN = re.compile(r"[a-z0-9]{3,}")
_SOURCE_TAG = re.compile(r"\s*\[S?\d+(?:\s*[,;]\s*S?\d+)*\]")
_UNAVAILABLE_TEXT = (
    "The Sales Persona is temporarily unavailable. Your dashboard, signals and scores are unaffected."
)
_EMPTY_TEXT = (
    "I could not build a grounded answer from the stored data. Name a tracked organization, or run "
    "a scan first, and I will draft from the evidence."
)


class _PersonaLlm(Protocol):
    async def compose_persona_answer(
        self,
        *,
        mode: str,
        message: str,
        context_block: str,
        history_block: str,
        scope_note: str = "",
    ) -> dict[str, Any]: ...



@dataclass
class _Context:
    sources: list[PersonaSource] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    live_lookup: bool = False
    cached: bool = False

    def add_source(
        self, *, kind: str, label: str, url: str | None = None, snippet: str | None = None
    ) -> int:
        for source in self.sources:
            if source.kind == kind and source.label == label and source.url == url:
                return source.ref
        ref = len(self.sources) + 1
        self.sources.append(
            PersonaSource(
                ref=ref, kind=kind, label=label[:160], url=url, snippet=(snippet or "")[:280] or None
            )
        )
        return ref

    def block(self) -> str:
        return "\n".join(self.lines)


async def reply(
    session: AsyncSession,
    *,
    settings: Settings,
    llm: _PersonaLlm,
    embedder: EmbeddingAdapter,
    message: str,
    history: list[PersonaHistoryTurn],
    organization_id,
    mode: str,
    scope: str = "auto",
) -> PersonaResponse:
    message = message.strip()
    organizations = list((await session.execute(select(Organization))).scalars().all())

    if scope == "organization":
        # The user picked one organization: use it and nothing else, whatever the message names.
        focus = [org for org in organizations if org.organization_id == organization_id]
        if not focus:
            raise ValidationAppError(message="Choose a tracked organization first.")
    elif scope == "general":
        focus = []  # Outside data: never scoped to an organization, even if one is named.
    else:
        focus = _focus_organizations(organizations, organization_id, message, history)
    ctx = _Context(organizations=[org.name for org in focus])

    for org in focus:
        await _add_organization_context(session, ctx, org)
    if focus and settings.embedding_configured:
        await _add_retrieved_chunks(session, ctx, settings, embedder, focus, message)

    # With an organization selected or named, use ONLY that organization's data: no portfolio
    # figures, no other organizations, no competitor news. Without one, the persona is portfolio-wide.
    scoped = bool(focus)
    if scope == "organization" and not ctx.sources:
        # Advisor rule: nothing stored about this organization means no answer and no model call.
        return _insufficient(ctx, focus[0])
    if not scoped:
        if mode in ("daily_briefing", "auto", "research", "email"):
            await _add_portfolio_snapshot(session, ctx)
        if mode == "competitor" or _COMPETITOR_WORDS.search(message):
            await _add_competitor_digest(session, ctx)

    await _add_live_lookups(settings, ctx, organizations, focus, message, mode, scoped=scoped)

    if not (settings.persona_gemini_configured or settings.llm_configured):
        return _unavailable(ctx)
    try:
        context_block = ctx.block()
        if len(context_block) > _MAX_CONTEXT_CHARS:
            context_block = context_block[:_MAX_CONTEXT_CHARS] + "\n…(context truncated for speed)"
        raw = await llm.compose_persona_answer(
            mode=mode,
            message=message,
            context_block=context_block,
            history_block=_history_block(history),
            scope_note=_scope_note(focus) if scoped else "",
        )
    except Exception:
        logger.exception("Persona LLM call failed")
        return _unavailable(ctx)

    blocks = _clean_blocks(raw.get("blocks") or [], valid_refs={s.ref for s in ctx.sources})
    if mode != "email" and not _EMAIL_REQUEST.search(message):
        blocks = [block for block in blocks if block.type != "email"]  # Drafts only on request.
    if not blocks:
        blocks = [PersonaBlock(type="paragraph", text=_EMPTY_TEXT)]
    blocks, sources = _renumber(blocks, ctx.sources)
    return PersonaResponse(
        status="answered",
        answer=PersonaAnswer(text=_flatten(blocks), blocks=blocks),
        sources=sources,
        follow_ups=_clean_follow_ups(raw.get("follow_ups") or []),
        used=PersonaUsed(organizations=ctx.organizations, live_lookup=ctx.live_lookup),
        data_origin="cached" if ctx.cached else "live",
    )


# --- focus detection ----------------------------------------------------------------------


def _focus_organizations(
    organizations: list[Organization], organization_id, message: str, history: list[PersonaHistoryTurn]
) -> list[Organization]:
    chosen: list[Organization] = []
    if organization_id is not None:
        chosen += [org for org in organizations if org.organization_id == organization_id]
    recent_user_text = " ".join(turn.text for turn in history[-4:] if turn.role == "user")
    for text in (message, recent_user_text):
        for org in organizations:
            if org in chosen:
                continue
            if _mentions(text, org.name):
                chosen.append(org)
        if chosen:
            break
    return chosen[:_MAX_FOCUS_ORGS]


def _mentions(text: str, organization_name: str) -> bool:
    lowered = text.lower()
    return any(
        re.search(rf"\b{re.escape(needle)}\b", lowered) for needle in _needles(organization_name)
    )


def _needles(name: str) -> set[str]:
    lower = name.lower()
    needles = {lower}
    for suffix in (" university", " college"):
        if lower.endswith(suffix) and len(lower) > len(suffix) + 3:
            needles.add(lower[: -len(suffix)])
    words = [w for w in re.findall(r"[a-z]+", lower) if w not in {"of", "the", "at", "and"}]
    if len(words) == 2 and len(words[0]) >= 5 and words[1] == "learning":
        needles.add(words[0])  # "Meazure Learning" is also called "Meazure"
    if len(words) >= 3:
        needles.add("".join(word[0] for word in words))
    return {needle for needle in needles if len(needle) >= 3}


# --- context builders -----------------------------------------------------------------------


async def _add_organization_context(session: AsyncSession, ctx: _Context, org: Organization) -> None:
    is_competitor = org.market_role == "competitor"
    if is_competitor:
        ctx.lines.append(
            f"\nCOMPETITOR: {org.name} (assessment/EdTech vendor; competitive context only, "
            f"never a customer opportunity)"
        )
        opportunity = None
    else:
        ctx.lines.append(
            f"\nORGANIZATION: {org.name} ({org.organization_type}"
            f"{', ' + org.state_code if org.state_code else ''}), tracking={org.tracking_status}"
        )
        opportunity = await opportunities_repo.get_by_organization(session, org.organization_id)
    if is_competitor:
        pass
    elif opportunity is None:
        ctx.lines.append("No potential opportunity exists yet for this organization.")
    else:
        if opportunity.data_origin == "cached":
            ctx.cached = True
        score = await scores_repo.latest_for_opportunity(session, opportunity.opportunity_id)
        if score is not None:
            ref = ctx.add_source(
                kind="system_data", label=f"Opportunity score: {org.name}", snippet=None
            )
            ctx.lines.append(
                f"[S{ref}] Stored rules score: {score.value}/100 ({score.band}). Factors: "
                f"procurement {score.procurement_relevance}/30, related signals "
                f"{score.related_signal_strength}/25, assessment/EdTech relevance "
                f"{score.assessment_edtech_relevance}/20, recency {score.recency}/15, "
                f"source reliability {score.source_reliability}/10."
            )
        ctx.lines.append(
            f"Stored correlation (AI interpretation of validated signals): "
            f"{opportunity.correlation_text[:600]}"
        )
        if opportunity.recommended_action_text:
            ctx.lines.append(f"Stored recommended action: {opportunity.recommended_action_text[:400]}")

    signals, _total = await signals_repo.list_signals(
        session,
        organization_id=org.organization_id,
        signal_types=None,
        states=["validated"],
        q=None,
        limit=_SIGNALS_PER_ORG,
        offset=0,
    )
    first_evidence = await evidence_repo.first_for_signals(
        session, [signal.signal_id for signal in signals]
    )
    for signal in signals:
        if signal.data_origin == "cached":
            ctx.cached = True
        found = first_evidence.get(signal.signal_id)
        if found is None:
            continue
        ev, source_name = found
        ref = ctx.add_source(
            kind="stored_evidence" if ev.source_id else "official_website",
            label=source_name or f"{org.name} official website",
            url=ev.source_url,
            snippet=ev.snippet,
        )
        when = signal.published_on.isoformat() if signal.published_on else "date unavailable"
        ctx.lines.append(
            f"[S{ref}] Validated signal ({signal.signal_type}, {when}): {signal.title}. "
            f"{signal.summary[:240]}"
        )


async def _add_retrieved_chunks(
    session: AsyncSession,
    ctx: _Context,
    settings: Settings,
    embedder: EmbeddingAdapter,
    focus: list[Organization],
    message: str,
) -> None:
    try:
        vectors = await embedder.embed_texts([message])
    except Exception:
        logger.warning("Persona question embedding failed; continuing without retrieval")
        return
    if not vectors:
        return
    threshold = max(settings.embedding_similarity_gate, _RAG_MIN_SIMILARITY)
    query_tokens = set(_TOKEN.findall(message.lower()))
    for org in focus:
        hits = await chunks_repo.retrieve_similar(
            session,
            organization_id=org.organization_id,
            query_embedding=vectors[0],
            embedding_model=settings.embedding_model,
            limit=_RAG_POOL_PER_ORG,
        )
        ranked: list[tuple[float, Any]] = []
        for chunk, similarity in hits:
            text = (chunk.chunk_text or "").strip()
            if len(text) < _RAG_MIN_CHUNK_CHARS:
                continue
            if similarity < threshold:
                continue
            bonus = _keyword_overlap_bonus(query_tokens, text)
            ranked.append((float(similarity) + bonus, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        for _, chunk in ranked[:_RAG_CHUNKS_PER_ORG]:
            if chunk.data_origin == "cached":
                ctx.cached = True
            ref = ctx.add_source(
                kind="official_website",
                label=chunk.source_name,
                url=chunk.source_url,
                snippet=chunk.chunk_text,
            )
            ctx.lines.append(
                f"[S{ref}] Collected page text ({org.name}): "
                f"{chunk.chunk_text[:_CONTEXT_CHUNK_CHARS]}"
            )


def _keyword_overlap_bonus(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    chunk_tokens = set(_TOKEN.findall(text.lower()))
    if not chunk_tokens:
        return 0.0
    overlap = len(query_tokens & chunk_tokens) / len(query_tokens)
    return min(_RAG_KEYWORD_BONUS, overlap * _RAG_KEYWORD_BONUS)


async def _add_portfolio_snapshot(session: AsyncSession, ctx: _Context) -> None:
    snapshot = await dashboard_service.build_dashboard(session)
    ref = ctx.add_source(kind="system_data", label="Portfolio dashboard snapshot")
    if snapshot.data_origin == "cached":
        ctx.cached = True
    scan = snapshot.scan_status
    ctx.lines.append(
        f"\nPORTFOLIO SNAPSHOT [S{ref}]: {snapshot.opportunities.total} potential opportunities "
        f"(bands {snapshot.opportunities.by_band}), {snapshot.opportunities.new_count} new in the "
        f"last 7 days; {snapshot.signals.validated_total} validated signals "
        f"({snapshot.signals.recent_count} in the last {snapshot.signals.recent_window_days} days); "
        f"scan state {scan.state}, last finished {scan.last_finished_at}, "
        f"{scan.sources_failed} failed source(s)."
    )
    for item in snapshot.prioritized_opportunities:
        ctx.lines.append(
            f"[S{ref}] Top opportunity: {item.organization_name} score {item.score.value} "
            f"({item.score.band}), {item.signal_count} signals."
        )
    for signal in snapshot.recent_signals:
        when = signal.date.isoformat() if signal.date else "date unavailable"
        ctx.lines.append(
            f"[S{ref}] Recent signal: {signal.organization_name} ({signal.signal_type}, {when}): "
            f"{signal.title}"
        )
    if snapshot.opportunities.total == 0:
        ctx.lines.append(f"[S{ref}] No opportunities exist yet. A scan has to run first.")


async def _add_competitor_digest(session: AsyncSession, ctx: _Context) -> None:
    digest = await competitors_service.build_competitors(session)
    if digest.totals.validated_signals == 0:
        ctx.lines.append(
            "\nSTORED COMPETITOR SIGNALS: none collected yet. Say so; do not invent competitor news."
        )
        return
    ctx.lines.append("\nSTORED COMPETITOR SIGNALS (validated, from scans):")
    for competitor in digest.competitors:
        for signal in competitor.signals[:3]:
            if not signal.evidence:
                continue
            ev = signal.evidence[0]
            if signal.data_origin == "cached":
                ctx.cached = True
            ref = ctx.add_source(
                kind="stored_evidence", label=ev.source_name, url=ev.source_url, snippet=ev.snippet
            )
            when = signal.date.isoformat() if signal.date else "date unavailable"
            ctx.lines.append(
                f"[S{ref}] {competitor.name} ({when}): {signal.title}. {signal.summary[:240]}"
            )


async def _add_live_lookups(
    settings: Settings,
    ctx: _Context,
    organizations: list[Organization],
    focus: list[Organization],
    message: str,
    mode: str,
    *,
    scoped: bool = False,
) -> None:
    if not settings.persona_live_lookup_enabled:
        return
    websites = [org.website_url for org in organizations if org.website_url]
    allowed = persona_lookup.allowed_hosts(settings, websites)

    # Scoped to an organization: only that organization's own site, never competitor domains.
    # Skip live fetch when we already have stored/RAG sources unless the user clearly asks for
    # latest web news — live homepage crawls are the main Persona latency cost.
    domains = [] if scoped else _competitor_domains(settings, message, mode)
    wants_web = bool(_WEB_WORDS.search(message))
    if scoped and ctx.sources and not wants_web:
        return
    if wants_web:
        domains += [
            host
            for org in focus
            if org.website_url and (host := persona_lookup.extract_registrable_host(org.website_url))
        ]
    if not domains:
        return

    # One page per domain when answering quickly from chat; still allowlisted.
    results = await persona_lookup.lookup_domains(
        settings,
        domains=domains,
        allowed=allowed,
        query=message,
        max_pages_override=1 if scoped else None,
    )
    failures: list[str] = []
    for result in results:
        failures += result.failures
        for hit in result.hits:
            ctx.live_lookup = True
            ref = ctx.add_source(
                kind="live_lookup", label=f"{hit.title} ({hit.domain})", url=hit.url, snippet=hit.excerpt
            )
            ctx.lines.append(
                f"[S{ref}] Live official page {hit.domain} (fetched now, verbatim excerpt): "
                f"{hit.excerpt[:700]}"
            )
    if failures:
        ctx.lines.append("LIVE LOOKUP COULD NOT READ: " + "; ".join(failures[:6]))


def _competitor_domains(settings: Settings, message: str, mode: str) -> list[str]:
    lowered = message.lower()
    named = [
        domain
        for domain in settings.persona_domains
        if any(
            re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in _brand_aliases(domain)
        )
    ]
    if named:
        return named
    if mode == "competitor" or _COMPETITOR_WORDS.search(message):
        return list(settings.persona_domains)
    return []


def _brand_aliases(domain: str) -> set[str]:
    brand = domain.split(".")[0]
    aliases = {brand}
    if brand.endswith("learning"):
        aliases.add(brand[: -len("learning")])
    return aliases


def _scope_note(focus: list[Organization]) -> str:
    names = ", ".join(org.name for org in focus)
    return (
        f"Use ONLY the CONTEXT about {names}. Do not use or mention any other organization, the wider "
        f"portfolio, market trends, or competitor news. If the request needs anything outside "
        f"{names}, say it is outside this organization's data."
    )


def _history_block(history: list[PersonaHistoryTurn]) -> str:
    return "\n".join(
        f"{'User' if turn.role == 'user' else 'Assistant'}: {turn.text[:600]}"
        for turn in history[-6:]
    )


# --- validating what the model returned ------------------------------------------------------


def _clean_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return _SOURCE_TAG.sub("", _strip_internal_ids(value)).strip()


def _clean_refs(value, valid_refs: set[int]) -> list[int]:
    if not isinstance(value, list):
        return []
    refs: list[int] = []
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool) and item in valid_refs:
            if item not in refs:
                refs.append(item)
    return refs


def _clean_layer(value, *, default: str | None) -> str | None:
    return value if isinstance(value, str) and value in _LAYERS else default


def _clean_blocks(raw_blocks: list, *, valid_refs: set[int]) -> list[PersonaBlock]:
    blocks: list[PersonaBlock] = []
    for raw in raw_blocks[:_MAX_BLOCKS]:
        if not isinstance(raw, dict):
            continue
        kind = raw.get("type")
        if kind == "heading":
            text = _clean_text(raw.get("text"))
            if text:
                blocks.append(PersonaBlock(type="heading", text=text[:160]))
        elif kind == "paragraph":
            text = _clean_text(raw.get("text"))
            layer = _clean_layer(raw.get("layer"), default="interpretation")
            refs = _clean_refs(raw.get("refs"), valid_refs)
            if text and not (layer == "fact" and not refs):
                blocks.append(PersonaBlock(type="paragraph", text=text, layer=layer, refs=refs))
        elif kind == "bullets":
            items = _clean_items(raw.get("items"), valid_refs)
            if items:
                blocks.append(PersonaBlock(type="bullets", items=items))
        elif kind == "table":
            headers, rows = _clean_table(raw.get("headers"), raw.get("rows"))
            layer = _clean_layer(raw.get("layer"), default="interpretation")
            refs = _clean_refs(raw.get("refs"), valid_refs)
            if headers and rows and not (layer == "fact" and not refs):
                blocks.append(
                    PersonaBlock(
                        type="table", headers=headers, rows=rows, layer=layer, refs=refs
                    )
                )
        elif kind == "email":
            subject = _clean_text(raw.get("subject"))
            body = _clean_email_body(raw.get("body"))
            if subject and body:
                blocks.append(PersonaBlock(type="email", subject=subject[:200], body=body))
    return blocks


def _clean_table(raw_headers, raw_rows) -> tuple[list[str], list[list[str]]]:
    if not isinstance(raw_headers, list) or not isinstance(raw_rows, list):
        return [], []
    headers = [_clean_text(h)[:80] for h in raw_headers[:_MAX_TABLE_COLS]]
    headers = [h for h in headers if h]
    if not headers:
        return [], []
    width = len(headers)
    rows: list[list[str]] = []
    for raw in raw_rows[:_MAX_TABLE_ROWS]:
        if not isinstance(raw, list):
            continue
        cells = [_clean_text(c)[:120] for c in raw[:width]]
        while len(cells) < width:
            cells.append("")
        if any(cells):
            rows.append(cells)
    return headers, rows


def _clean_items(raw_items, valid_refs: set[int]) -> list[PersonaBulletItem]:
    if not isinstance(raw_items, list):
        return []
    items: list[PersonaBulletItem] = []
    for raw in raw_items[:_MAX_ITEMS]:
        if isinstance(raw, str):
            raw = {"text": raw}
        if not isinstance(raw, dict):
            continue
        text = _clean_text(raw.get("text"))
        layer = _clean_layer(raw.get("layer"), default="interpretation")
        refs = _clean_refs(raw.get("refs"), valid_refs)
        if not text or (layer == "fact" and not refs):
            continue  # An uncited fact is dropped, as in the Advisor.
        items.append(PersonaBulletItem(text=text, layer=layer, refs=refs))
    return items


def _clean_email_body(value) -> str:
    if not isinstance(value, str):
        return ""
    body = _SOURCE_TAG.sub("", _strip_internal_ids(value))
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def _clean_follow_ups(raw: list) -> list[str]:
    cleaned = [_clean_text(item)[:120] for item in raw if isinstance(item, str)]
    return [item for item in cleaned if item][:3]


def _renumber(
    blocks: list[PersonaBlock], sources: list[PersonaSource]
) -> tuple[list[PersonaBlock], list[PersonaSource]]:
    """Keep only sources that are actually cited and number them 1..n in order of first use."""
    by_ref = {source.ref: source for source in sources}
    mapping: dict[int, int] = {}

    def remap(refs: list[int]) -> list[int]:
        out: list[int] = []
        for ref in refs:
            if ref not in mapping:
                mapping[ref] = len(mapping) + 1
            out.append(mapping[ref])
        return out

    for block in blocks:
        block.refs = remap(block.refs)
        for item in block.items:
            item.refs = remap(item.refs)

    kept = [
        by_ref[old].model_copy(update={"ref": new})
        for old, new in sorted(mapping.items(), key=lambda pair: pair[1])
    ]
    return blocks, kept


def _flatten(blocks: list[PersonaBlock]) -> str:
    lines: list[str] = []
    for block in blocks:
        if block.type == "heading":
            lines.append(block.text or "")
        elif block.type == "paragraph":
            lines.append(block.text or "")
        elif block.type == "bullets":
            lines += [f"• {item.text}" for item in block.items]
        elif block.type == "table":
            if block.headers:
                lines.append(" | ".join(block.headers))
            for row in block.rows:
                lines.append(" | ".join(row))
        elif block.type == "email":
            lines.append(f"Subject: {block.subject}\n\n{block.body}")
    return "\n".join(line for line in lines if line)


def _insufficient(ctx: _Context, org: Organization) -> PersonaResponse:
    text = (
        f"Insufficient evidence in collected sources for {org.name}. Run a scan for this organization "
        f"first, or switch to general questions."
    )
    return PersonaResponse(
        status="answered",
        answer=PersonaAnswer(
            text=text, blocks=[PersonaBlock(type="paragraph", text=text, layer="interpretation")]
        ),
        sources=[],
        follow_ups=[],
        used=PersonaUsed(organizations=ctx.organizations, live_lookup=False),
        data_origin="live",
    )


def _unavailable(ctx: _Context) -> PersonaResponse:
    return PersonaResponse(
        status="unavailable",
        answer=PersonaAnswer(text=_UNAVAILABLE_TEXT, blocks=[]),
        sources=[],
        follow_ups=[],
        used=PersonaUsed(organizations=ctx.organizations, live_lookup=ctx.live_lookup),
        data_origin="live",
    )
