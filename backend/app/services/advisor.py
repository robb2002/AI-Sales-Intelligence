"""AI Sales Advisor — grounded RAG over collected documents (API_CONTRACT §12)."""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.azure_openai import AzureOpenAIAdapter
from app.ai.adapters.embeddings import EmbeddingAdapter
from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationAppError
from app.repositories import advisor_sessions as sessions_repo
from app.repositories import ai_interactions as interactions_repo
from app.repositories import document_chunks as chunks_repo
from app.repositories import evidence as evidence_repo
from app.repositories import opportunities as opportunities_repo
from app.repositories import opportunity_scores as scores_repo
from app.repositories.documents import Document
from app.repositories.organizations import Organization
from app.repositories.sources import Source
from app.schemas.advisor import (
    AdvisorAnswerBody,
    AdvisorAnswerResponse,
    AdvisorSegment,
    AdvisorSessionResponse,
    AdvisorTurnAdvisor,
    AdvisorTurnUser,
)
from app.schemas.signals import EvidenceItem

logger = logging.getLogger("app.services.advisor")

_OUT_OF_SCOPE_PATTERNS = (
    re.compile(r"\b(draft|write)\b.{0,40}\b(email|outreach|cold call)\b", re.I),
    re.compile(r"\bcontact\b.{0,30}\b(cio|provost|someone|them)\b", re.I),
    re.compile(r"\b(predict|will there be|when will)\b.{0,40}\b(rfp|award|win)\b", re.I),
    re.compile(r"\b(canada|uk|united kingdom|europe|india|australia)\b", re.I),
)

_INSUFFICIENT_TEXT = (
    "Insufficient evidence in collected sources for this organization. "
    "Run a scan or ask about signals and documents already stored."
)
_OUT_OF_SCOPE_TEXT = (
    "That question is out of scope for the Advisor. Ask about this organization's "
    "collected signals, evidence, score, or recommended research — not outreach drafts, "
    "predictions, or organizations we do not track."
)
_UNAVAILABLE_TEXT = (
    "The AI Sales Advisor is temporarily unavailable. Scores and evidence below are unaffected."
)


async def ask(
    session: AsyncSession,
    *,
    settings: Settings,
    llm: AzureOpenAIAdapter,
    embedder: EmbeddingAdapter,
    scope_type: str,
    scope_id: uuid.UUID,
    message: str,
    session_id: uuid.UUID | None,
) -> AdvisorAnswerResponse:
    message = message.strip()
    if not message or len(message) > 2000:
        raise ValidationAppError(message="message must be 1 to 2000 characters")
    if scope_type not in ("organization", "opportunity"):
        raise ValidationAppError(message="scope_type must be organization or opportunity")

    organization, opportunity = await _resolve_scope(
        session, scope_type=scope_type, scope_id=scope_id
    )
    adv_session = await _get_or_create_session(
        session,
        session_id=session_id,
        scope_type=scope_type,
        scope_id=scope_id,
        organization_id=organization.organization_id,
    )

    await interactions_repo.create_interaction(
        session,
        kind="advisor_user",
        body_text=message,
        session_id=adv_session.session_id,
        organization_id=organization.organization_id,
        opportunity_id=opportunity.opportunity_id if opportunity else None,
    )
    await sessions_repo.touch_session(session, adv_session)

    if _looks_out_of_scope(message):
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="out_of_scope",
            text=_OUT_OF_SCOPE_TEXT,
            segments=[],
            evidence=[],
        )

    if not settings.embedding_configured:
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="unavailable",
            text=_UNAVAILABLE_TEXT,
            segments=[],
            evidence=[],
        )

    try:
        query_vecs = await embedder.embed_texts([message])
    except Exception:
        logger.exception("Advisor question embedding failed")
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="unavailable",
            text=_UNAVAILABLE_TEXT,
            segments=[],
            evidence=[],
        )

    if not query_vecs:
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="insufficient_evidence",
            text=_INSUFFICIENT_TEXT,
            segments=[],
            evidence=[],
        )

    hits = await chunks_repo.retrieve_similar(
        session,
        organization_id=organization.organization_id,
        query_embedding=query_vecs[0],
        embedding_model=settings.embedding_model,
        limit=6,
    )
    gate = settings.embedding_similarity_gate
    passing = [(chunk, sim) for chunk, sim in hits if sim >= gate]
    if not passing:
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="insufficient_evidence",
            text=_INSUFFICIENT_TEXT,
            segments=[],
            evidence=[],
        )

    allowed_chunk_ids = {str(chunk.chunk_id) for chunk, _ in passing}
    records = [
        {
            "chunk_id": str(chunk.chunk_id),
            "source_name": chunk.source_name,
            "source_url": chunk.source_url,
            "published_on": chunk.published_on.isoformat() if chunk.published_on else "unavailable",
            "chunk_text": chunk.chunk_text,
        }
        for chunk, _ in passing
    ]

    score_block = await _score_block(session, opportunity)
    history_block = await _history_block(session, adv_session.session_id)

    if not settings.llm_configured:
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="unavailable",
            text=_UNAVAILABLE_TEXT,
            segments=[],
            evidence=[],
        )

    try:
        raw = await llm.answer_advisor(
            organization_name=organization.name,
            scope_type=scope_type,
            scope_id=str(scope_id),
            message=message,
            records=records,
            score_block=score_block,
            history_block=history_block,
        )
    except Exception:
        logger.exception("Advisor LLM call failed")
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="unavailable",
            text=_UNAVAILABLE_TEXT,
            segments=[],
            evidence=[],
        )

    status = str(raw.get("advisor_status") or "answered")
    if status in ("insufficient_evidence", "out_of_scope", "unavailable"):
        text = {
            "insufficient_evidence": _INSUFFICIENT_TEXT,
            "out_of_scope": _OUT_OF_SCOPE_TEXT,
            "unavailable": _UNAVAILABLE_TEXT,
        }[status]
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status=status,
            text=text,
            segments=[],
            evidence=[],
        )

    chunk_by_id = {str(chunk.chunk_id): chunk for chunk, _ in passing}
    evidence_items: list[EvidenceItem] = []
    segment_models: list[AdvisorSegment] = []
    cited_evidence_ids: list[uuid.UUID] = []
    chunk_to_evidence: dict[str, uuid.UUID] = {}

    for seg in raw.get("segments") or []:
        layer = seg.get("content_layer") or "interpretation"
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        raw_ids = [cid for cid in (seg.get("chunk_ids") or []) if cid in allowed_chunk_ids]
        evidence_ids: list[uuid.UUID] = []
        for cid in raw_ids:
            if cid not in chunk_to_evidence:
                chunk = chunk_by_id[cid]
                ev = await evidence_repo.create_evidence(
                    session,
                    signal_id=None,
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    source_id=await _document_source_id(session, chunk.document_id),
                    source_url=chunk.source_url,
                    published_on=chunk.published_on,
                    snippet=chunk.chunk_text[:500],
                    relationship="Supports Advisor answer",
                    data_origin=chunk.data_origin,
                    retrieved_at=chunk.retrieved_at,
                )
                item = EvidenceItem(
                    evidence_id=ev.evidence_id,
                    source_name=chunk.source_name,
                    source_url=chunk.source_url,
                    date=chunk.published_on,
                    date_status="available" if chunk.published_on else "unavailable",
                    snippet=ev.snippet,
                    relationship=ev.relationship,
                    data_origin=ev.data_origin,
                    retrieved_at=ev.retrieved_at,
                )
                evidence_items.append(item)
                chunk_to_evidence[cid] = ev.evidence_id
                cited_evidence_ids.append(ev.evidence_id)
            evidence_ids.append(chunk_to_evidence[cid])

        if layer == "fact" and not evidence_ids:
            # Drop uncited FACT segments (AI_RAG_DESIGN grounding).
            continue
        segment_models.append(
            AdvisorSegment(
                text=text if layer != "interpretation" else text,
                content_layer=layer,
                evidence_ids=evidence_ids,
            )
        )

    if not segment_models:
        return await _finish(
            session,
            adv_session=adv_session,
            organization=organization,
            opportunity=opportunity,
            status="insufficient_evidence",
            text=_INSUFFICIENT_TEXT,
            segments=[],
            evidence=[],
        )

    answer_text = _compose_answer_text(segment_models)
    return await _finish(
        session,
        adv_session=adv_session,
        organization=organization,
        opportunity=opportunity,
        status="answered",
        text=answer_text,
        segments=segment_models,
        evidence=evidence_items,
        evidence_ids=cited_evidence_ids,
        data_origin=_data_origin(passing),
    )


async def get_session_payload(
    session: AsyncSession, session_id: uuid.UUID
) -> AdvisorSessionResponse:
    adv = await sessions_repo.get_session(session, session_id)
    if adv is None:
        raise NotFoundError("advisor_session", "Advisor session not found")
    turns_raw = await interactions_repo.list_session_turns(session, session_id, limit=8)
    turns: list[AdvisorTurnUser | AdvisorTurnAdvisor] = []
    for row in turns_raw:
        if row.kind == "advisor_user":
            turns.append(
                AdvisorTurnUser(
                    role="user",
                    text=row.body_text,
                    created_at=row.created_at,
                )
            )
        else:
            evidence_rows = await evidence_repo.list_by_ids(session, list(row.evidence_ids or []))
            evidence_items: list[EvidenceItem] = []
            for ev in evidence_rows:
                source_name = await _evidence_source_name(session, ev)
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=ev.evidence_id,
                        source_name=source_name,
                        source_url=ev.source_url,
                        date=ev.published_on,
                        date_status="available" if ev.published_on else "unavailable",
                        snippet=ev.snippet,
                        relationship=ev.relationship,
                        data_origin=ev.data_origin,
                        retrieved_at=ev.retrieved_at,
                    )
                )
            turns.append(
                AdvisorTurnAdvisor(
                    role="advisor",
                    answer=AdvisorAnswerBody(
                        text=row.body_text,
                        segments=[],
                    ),
                    advisor_status=row.advisor_status or "answered",
                    evidence=evidence_items,
                    created_at=row.created_at,
                )
            )
    return AdvisorSessionResponse(
        session_id=adv.session_id,
        scope_type=adv.scope_type,
        scope_id=adv.scope_id,
        turns=turns,
    )


async def _resolve_scope(
    session: AsyncSession, *, scope_type: str, scope_id: uuid.UUID
) -> tuple[Organization, object | None]:
    if scope_type == "organization":
        org = await session.get(Organization, scope_id)
        if org is None:
            raise NotFoundError("organization")
        return org, None
    opportunity = await opportunities_repo.get_by_id(session, scope_id)
    if opportunity is None:
        raise NotFoundError("opportunity")
    org = await session.get(Organization, opportunity.organization_id)
    if org is None:
        raise NotFoundError("organization")
    return org, opportunity


async def _get_or_create_session(
    session: AsyncSession,
    *,
    session_id: uuid.UUID | None,
    scope_type: str,
    scope_id: uuid.UUID,
    organization_id: uuid.UUID,
):
    if session_id is None:
        return await sessions_repo.create_session(
            session,
            scope_type=scope_type,
            scope_id=scope_id,
            organization_id=organization_id,
        )
    existing = await sessions_repo.get_session(session, session_id)
    if existing is None:
        raise NotFoundError("advisor_session")
    if existing.scope_type != scope_type or existing.scope_id != scope_id:
        raise ValidationAppError(
            message="session_id scope does not match this request",
            details={"field": "session_id"},
        )
    return existing


def _looks_out_of_scope(message: str) -> bool:
    return any(p.search(message) for p in _OUT_OF_SCOPE_PATTERNS)


async def _score_block(session: AsyncSession, opportunity) -> str:
    if opportunity is None:
        return ""
    score = await scores_repo.latest_for_opportunity(session, opportunity.opportunity_id)
    if score is None:
        return "STORED_SCORE: none"
    return (
        f"STORED_SCORE (rules; do not change): value={score.value} band={score.band} "
        f"weight_version={score.weight_version}\n"
        f"FACTORS: procurement={score.procurement_relevance} "
        f"related={score.related_signal_strength} edtech={score.assessment_edtech_relevance} "
        f"recency={score.recency} reliability={score.source_reliability}\n"
        f"correlation: {opportunity.correlation_text[:500]}"
    )


async def _history_block(session: AsyncSession, session_id: uuid.UUID) -> str:
    turns = await interactions_repo.list_session_turns(session, session_id, limit=8)
    # Exclude the user turn we just wrote (last item if user).
    prior = turns[:-1] if turns and turns[-1].kind == "advisor_user" else turns
    if not prior:
        return ""
    lines = []
    for row in prior[-6:]:
        role = "user" if row.kind == "advisor_user" else "advisor"
        lines.append(f"{role}: {row.body_text[:400]}")
    return "Prior turns (not evidence):\n" + "\n".join(lines)


async def _finish(
    session: AsyncSession,
    *,
    adv_session,
    organization: Organization,
    opportunity,
    status: str,
    text: str,
    segments: list[AdvisorSegment],
    evidence: list[EvidenceItem],
    evidence_ids: list[uuid.UUID] | None = None,
    data_origin: str = "live",
) -> AdvisorAnswerResponse:
    await interactions_repo.create_interaction(
        session,
        kind="advisor_answer",
        body_text=text,
        session_id=adv_session.session_id,
        organization_id=organization.organization_id,
        opportunity_id=opportunity.opportunity_id if opportunity else None,
        prompt_id="advisor_answer_v1",
        prompt_version="v1",
        advisor_status=status,
        content_layer="interpretation" if status == "answered" else None,
        evidence_ids=evidence_ids or [],
    )
    await sessions_repo.touch_session(session, adv_session)
    await session.commit()
    return AdvisorAnswerResponse(
        session_id=adv_session.session_id,
        scope_type=adv_session.scope_type,
        scope_id=adv_session.scope_id,
        advisor_status=status,
        answer=AdvisorAnswerBody(text=text, segments=segments),
        evidence=evidence,
        data_origin=data_origin,
    )


def _compose_answer_text(segments: list[AdvisorSegment]) -> str:
    parts: list[str] = []
    for seg in segments:
        if seg.content_layer == "interpretation":
            parts.append(f"Interpretation: {seg.text}")
        elif seg.content_layer == "recommended_action":
            parts.append(f"Recommended research: {seg.text}")
        else:
            parts.append(seg.text)
    return "\n\n".join(parts)


def _data_origin(passing: list) -> str:
    if any(chunk.data_origin == "cached" for chunk, _ in passing):
        return "cached"
    return "live"


async def _document_source_id(
    session: AsyncSession, document_id: uuid.UUID
) -> uuid.UUID | None:
    doc = await session.get(Document, document_id)
    return doc.source_id if doc else None


async def _evidence_source_name(session: AsyncSession, ev) -> str:
    if ev.source_id is not None:
        source = await session.get(Source, ev.source_id)
        if source is not None:
            return source.name
    doc = await session.get(Document, ev.document_id)
    if doc and doc.organization_id:
        org = await session.get(Organization, doc.organization_id)
        if org:
            return f"{org.name} official website"
    return "Collected source"
