"""Extract, validate, and store signals + evidence from organization documents (M5)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.base import ExtractedSignalCandidate, LLMProviderAdapter
from app.ingestion.collectors.sam_gov import organization_match_needles
from app.repositories import documents as documents_repo
from app.repositories import evidence as evidence_repo
from app.repositories import signals as signals_repo
from app.repositories.documents import Document
from app.repositories.organizations import Organization
from app.repositories.scans import ScanRun
from app.repositories.signals import SIGNAL_TYPES
from app.services import signal_dedup

logger = logging.getLogger("app.services.signal_extraction")

_MAX_DOCS_PER_SCAN = 20


@dataclass
class ExtractionRunResult:
    created: int = 0
    updated: int = 0
    rejected: int = 0
    skipped_docs: int = 0
    processed_docs: int = 0


async def extract_organization_signals(
    session: AsyncSession,
    *,
    llm: LLMProviderAdapter,
    scan: ScanRun,
    org: Organization,
    document_ids: list[UUID] | None = None,
) -> ExtractionRunResult:
    """Run after documents are collected. Empty extraction is a successful outcome.

    When `document_ids` is provided, only those documents are considered (inserted/updated
    in this scan). Unchanged bodies are not sent to the LLM again.
    """
    result = ExtractionRunResult()
    if document_ids is not None:
        docs = await documents_repo.list_by_ids(session, document_ids)
        docs = [d for d in docs if d.organization_id == org.organization_id]
    else:
        docs = await documents_repo.list_for_organization(session, org.organization_id)

    if not docs:
        detail = (
            "0 changed documents to extract"
            if document_ids is not None
            else "0 documents to extract"
        )
        scan.sources = list(scan.sources or []) + [
            {
                "source_name": "Signal extraction",
                "status": "succeeded",
                "detail": detail,
            }
        ]
        await session.flush()
        return result

    scan.stage = "extracting"
    await session.commit()

    registry_names: dict[UUID, str] = {}
    for doc in docs[:_MAX_DOCS_PER_SCAN]:
        if not doc.body_text or not doc.body_text.strip():
            result.skipped_docs += 1
            continue
        # Tier 1: same content_hash already produced validated signals — skip LLM.
        if await signal_dedup.document_already_extracted(
            session, organization_id=org.organization_id, content_hash=doc.content_hash
        ):
            result.skipped_docs += 1
            continue

        source_name = await _source_name(session, org, doc, registry_names)
        try:
            candidates = await llm.extract_signals(
                organization_name=org.name,
                organization_id=str(org.organization_id),
                source_name=source_name,
                source_url=doc.source_url,
                title=doc.title,
                body_text=doc.body_text,
                published_on=doc.published_on.isoformat() if doc.published_on else None,
            )
        except Exception:
            logger.exception("Signal extraction LLM failed for document %s", doc.document_id)
            scan.sources = list(scan.sources or []) + [
                {
                    "source_name": "Signal extraction",
                    "status": "failed",
                    "detail": f"llm_error on {doc.source_url[:80]}",
                }
            ]
            await session.commit()
            continue

        result.processed_docs += 1
        for candidate in candidates:
            outcome = await _persist_candidate(
                session, org=org, doc=doc, candidate=candidate
            )
            if outcome == "created":
                result.created += 1
            elif outcome in ("merged", "updated"):
                result.updated += 1
            elif outcome == "rejected":
                result.rejected += 1

        await session.commit()

    scan.signals_created = int(scan.signals_created or 0) + result.created
    scan.signals_updated = int(scan.signals_updated or 0) + result.updated
    scan.sources = list(scan.sources or []) + [
        {
            "source_name": "Signal extraction",
            "status": "succeeded",
            "detail": (
                f"{result.processed_docs} docs, {result.created} validated, "
                f"{result.updated} merged, {result.rejected} rejected, "
                f"{result.skipped_docs} skipped"
            ),
        }
    ]
    await session.flush()
    return result


async def _persist_candidate(
    session: AsyncSession,
    *,
    org: Organization,
    doc: Document,
    candidate: ExtractedSignalCandidate,
) -> str:
    rejection = _validate(org=org, doc=doc, candidate=candidate)
    published_on = doc.published_on

    if rejection:
        signal = await signals_repo.create_signal(
            session,
            organization_id=org.organization_id,
            signal_type=candidate.signal_type
            if candidate.signal_type in SIGNAL_TYPES
            else "strategic_announcement",
            state="rejected",
            title=(candidate.title or "Rejected candidate")[:500],
            summary=(candidate.summary or rejection)[:4000],
            published_on=published_on,
            rejection_reason=rejection,
            ai_summary=candidate.relationship[:2000] if candidate.relationship else None,
            data_origin=doc.data_origin,
        )
        if candidate.snippet and candidate.snippet in doc.body_text:
            await evidence_repo.create_evidence(
                session,
                signal_id=signal.signal_id,
                document_id=doc.document_id,
                source_id=doc.source_id,
                source_url=doc.source_url,
                published_on=published_on,
                snippet=candidate.snippet[:4000],
                relationship=candidate.relationship[:2000] or rejection,
                data_origin=doc.data_origin,
                retrieved_at=doc.retrieved_at,
            )
        return "rejected"

    survivor = await signal_dedup.find_survivor_for_candidate(
        session,
        organization_id=org.organization_id,
        signal_type=candidate.signal_type,
        document=doc,
        title=candidate.title,
        snippet=candidate.snippet,
        published_on=published_on,
    )
    if survivor is not None:
        outcome = await signal_dedup.merge_into_survivor(
            session,
            survivor=survivor,
            document=doc,
            title=candidate.title,
            summary=candidate.summary,
            snippet=candidate.snippet,
            relationship=candidate.relationship,
            published_on=published_on,
            data_origin=doc.data_origin,
        )
        return "updated" if outcome in ("merged", "unchanged") else outcome

    signal = await signals_repo.create_signal(
        session,
        organization_id=org.organization_id,
        signal_type=candidate.signal_type,
        state="validated",
        title=candidate.title[:500],
        summary=candidate.summary[:4000],
        published_on=published_on,
        rejection_reason=None,
        ai_summary=candidate.relationship[:2000],
        data_origin=doc.data_origin,
    )
    await evidence_repo.create_evidence(
        session,
        signal_id=signal.signal_id,
        document_id=doc.document_id,
        source_id=doc.source_id,
        source_url=doc.source_url,
        published_on=published_on,
        snippet=candidate.snippet[:4000],
        relationship=candidate.relationship[:2000],
        data_origin=doc.data_origin,
        retrieved_at=doc.retrieved_at,
    )
    return "created"


def _validate(
    *, org: Organization, doc: Document, candidate: ExtractedSignalCandidate
) -> str | None:
    if candidate.signal_type not in SIGNAL_TYPES:
        return "INVALID_SIGNAL_TYPE"
    if not doc.body_text or not candidate.snippet:
        return "NO_EVIDENCE"
    if candidate.snippet not in doc.body_text:
        return "SNIPPET_NOT_IN_SOURCE"
    if candidate.source_url and candidate.source_url.strip() != doc.source_url:
        return "URL_NOT_FROM_SOURCE"
    if not _about_organization(org=org, doc=doc):
        return "NOT_ABOUT_ORGANIZATION"
    return None


def _about_organization(*, org: Organization, doc: Document) -> bool:
    # Already scoped to this organization_id on the document.
    if doc.organization_id != org.organization_id:
        return False
    # SAM / API rows matched earlier via external_id.
    if doc.external_id:
        return True
    body = (doc.body_text or "").lower()
    title = (doc.title or "").lower()
    haystack = f"{title}\n{body}"
    needles = organization_match_needles(org.name)
    if any(n in haystack for n in needles if len(n) >= 6):
        return True
    # Short branded forms from website host, e.g. "ucf" from ucf.edu.
    if org.website_url:
        host = re.sub(r"^www\.", "", re.split(r"[/:]", org.website_url.split("://")[-1])[0]).lower()
        brand = host.split(".")[0]
        if len(brand) >= 3 and re.search(rf"\b{re.escape(brand)}\b", haystack):
            return True
    return False


async def _source_name(
    session: AsyncSession,
    org: Organization,
    doc: Document,
    cache: dict[UUID, str],
) -> str:
    if doc.source_id is not None:
        if doc.source_id not in cache:
            from app.repositories.sources import Source

            row = await session.get(Source, doc.source_id)
            cache[doc.source_id] = row.name if row is not None else "Unknown source"
        return cache[doc.source_id]
    return f"{org.name} official website"
