"""Trends read model (API_CONTRACT §10b). Stored validated target signals only. No model call."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationAppError
from app.repositories.organizations import ORGANIZATION_TYPES, Organization
from app.repositories.signals import SIGNAL_TYPES, Signal
from app.schemas.trends import (
    TrendsBucket,
    TrendsOrganizationTypeBucket,
    TrendsResponse,
    TrendsSignalTypeMonth,
    TrendsStateBucket,
    TrendsTotals,
    TrendsWindow,
)


def _month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def _month_keys(end: date, months: int) -> list[str]:
    keys: list[str] = []
    year, month = _add_months(end.year, end.month, -(months - 1))
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        year, month = _add_months(year, month, 1)
    return keys


def _empty_type_counts() -> dict[str, int]:
    return {signal_type: 0 for signal_type in SIGNAL_TYPES}


async def build_trends(session: AsyncSession, *, months: int) -> TrendsResponse:
    if months < 3 or months > 12:
        raise ValidationAppError(
            message="months must be between 3 and 12.",
            details={"months": "out_of_range"},
        )

    now = datetime.now(timezone.utc)
    today = now.date()
    month_keys = _month_keys(today, months)
    oldest_year, oldest_month = int(month_keys[0][:4]), int(month_keys[0][5:7])
    date_from = _month_start(oldest_year, oldest_month)
    date_to = today
    key_index = {key: i for i, key in enumerate(month_keys)}

    orgs = list(
        (
            await session.execute(
                select(Organization).where(Organization.market_role == "target")
            )
        )
        .scalars()
        .all()
    )
    org_by_id = {org.organization_id: org for org in orgs}
    org_ids = list(org_by_id.keys())

    signals: list[Signal] = []
    if org_ids:
        signals = list(
            (
                await session.execute(
                    select(Signal).where(
                        Signal.organization_id.in_(org_ids),
                        Signal.state == "validated",
                    )
                )
            )
            .scalars()
            .all()
        )

    # Counted: dated inside the window, or undated (no publication date).
    counted: list[Signal] = []
    for signal in signals:
        if signal.published_on is None:
            counted.append(signal)
        elif date_from <= signal.published_on <= date_to:
            counted.append(signal)

    by_type_months = [_empty_type_counts() for _ in month_keys]
    any_cached = False
    orgs_with_signal: set = set()

    for signal in counted:
        orgs_with_signal.add(signal.organization_id)
        if signal.data_origin == "cached":
            any_cached = True
        if signal.published_on is None:
            continue
        key = f"{signal.published_on.year:04d}-{signal.published_on.month:02d}"
        idx = key_index.get(key)
        if idx is None:
            continue
        if signal.signal_type in by_type_months[idx]:
            by_type_months[idx][signal.signal_type] += 1

    by_signal_type = [
        TrendsSignalTypeMonth(month=month_keys[i], counts=by_type_months[i])
        for i in range(len(month_keys))
    ]

    # State buckets: every state that has at least one target org (plus null).
    state_orgs: dict[str | None, list] = {}
    for org in orgs:
        state_orgs.setdefault(org.state_code, []).append(org)

    by_state: list[TrendsStateBucket] = []
    for state_code, state_org_list in state_orgs.items():
        bucket = _bucket_for_orgs(
            state_org_list,
            counted,
            month_keys=month_keys,
            key_index=key_index,
        )
        by_state.append(
            TrendsStateBucket(
                state_code=state_code,
                organizations=bucket.organizations,
                total=bucket.total,
                undated=bucket.undated,
                by_month=bucket.by_month,
            )
        )
    by_state.sort(
        key=lambda row: (-row.total, row.state_code or ""),
    )

    # Vertical buckets: every org type that has at least one target org.
    type_orgs: dict[str, list] = {t: [] for t in ORGANIZATION_TYPES}
    for org in orgs:
        if org.organization_type in type_orgs:
            type_orgs[org.organization_type].append(org)

    by_organization_type: list[TrendsOrganizationTypeBucket] = []
    for organization_type, type_org_list in type_orgs.items():
        if not type_org_list:
            continue
        bucket = _bucket_for_orgs(
            type_org_list,
            counted,
            month_keys=month_keys,
            key_index=key_index,
        )
        by_organization_type.append(
            TrendsOrganizationTypeBucket(
                organization_type=organization_type,
                organizations=bucket.organizations,
                total=bucket.total,
                undated=bucket.undated,
                by_month=bucket.by_month,
            )
        )
    by_organization_type.sort(
        key=lambda row: (-row.total, row.organization_type),
    )

    undated_total = sum(1 for signal in counted if signal.published_on is None)

    return TrendsResponse(
        generated_at=now,
        data_origin="cached" if any_cached else "live",
        window=TrendsWindow(months=months, date_from=date_from, date_to=date_to),
        month_keys=month_keys,
        totals=TrendsTotals(
            signals=len(counted),
            undated=undated_total,
            organizations=len(orgs_with_signal),
        ),
        by_signal_type=by_signal_type,
        by_state=by_state,
        by_organization_type=by_organization_type,
    )


def _bucket_for_orgs(
    orgs: list[Organization],
    counted: list[Signal],
    *,
    month_keys: list[str],
    key_index: dict[str, int],
) -> TrendsBucket:
    org_ids = {org.organization_id for org in orgs}
    by_month = [0] * len(month_keys)
    undated = 0
    for signal in counted:
        if signal.organization_id not in org_ids:
            continue
        if signal.published_on is None:
            undated += 1
            continue
        key = f"{signal.published_on.year:04d}-{signal.published_on.month:02d}"
        idx = key_index.get(key)
        if idx is not None:
            by_month[idx] += 1
    return TrendsBucket(
        organizations=len(orgs),
        total=sum(by_month) + undated,
        undated=undated,
        by_month=by_month,
    )
