"""
Async database layer (SQLAlchemy 2.0 + asyncpg).

Provides the booking_leads table and helpers to persist leads. All operations
fail SOFT: if the DB is unreachable we log and return without raising, so a
booking is never blocked by a database hiccup (the email is still attempted).
"""
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy import String, Integer, Text, Boolean, DateTime, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


def _prepare_db_url(url: str) -> tuple[str, dict]:
    """
    Return (sqlalchemy_url, connect_args) for the asyncpg driver.

    Managed Postgres (Neon, Supabase, RDS, …) hand out libpq-style URLs with
    query params like `?sslmode=require` / `channel_binding`, but asyncpg does
    NOT accept those as connect args and will raise. So we strip the libpq-only
    params and translate SSL intent into asyncpg's own `ssl` connect arg.
    """
    # SQLAlchemy async needs the asyncpg driver prefix.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    connect_args: dict = {}

    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)  # libpq-only; asyncpg rejects it
    if sslmode in ("require", "prefer", "allow", "verify-ca", "verify-full"):
        connect_args["ssl"] = True

    cleaned = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    return cleaned, connect_args


DATABASE_URL, _CONNECT_ARGS = _prepare_db_url(
    os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/travel_db")
)


class Base(DeclarativeBase):
    pass


class BookingLead(Base):
    __tablename__ = "booking_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    cruise_id: Mapped[str] = mapped_column(String(64))
    cruise_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ConsultationInquiry(Base):
    __tablename__ = "consultation_inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    budget: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# pool_pre_ping + a modest recycle keep connections healthy against serverless
# Postgres (e.g. Neon) that may drop idle connections / auto-suspend.
engine = create_async_engine(
    DATABASE_URL, pool_pre_ping=True, pool_recycle=300, connect_args=_CONNECT_ARGS
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create tables if they don't exist. Call on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_booking_lead(full_name: str, email: str, cruise_id: str,
                            cruise_details: Optional[str] = None,
                            session_id: Optional[str] = None) -> Optional[int]:
    """Insert a lead and return its id, or None if the write failed."""
    try:
        async with AsyncSessionLocal() as session:
            lead = BookingLead(
                full_name=full_name, email=email, cruise_id=cruise_id,
                cruise_details=cruise_details, session_id=session_id,
            )
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
            print(f"[db] saved booking lead #{lead.id} ({email}, {cruise_id})")
            return lead.id
    except Exception as exc:  # noqa: BLE001 - never block a booking on DB errors
        print(f"[db] failed to save booking lead: {exc!r}")
        return None


async def mark_lead_emailed(lead_id: Optional[int], sent: bool) -> None:
    """Update whether the agency notification email was sent for a lead."""
    if lead_id is None:
        return
    try:
        async with AsyncSessionLocal() as session:
            lead = await session.get(BookingLead, lead_id)
            if lead is not None:
                lead.email_sent = sent
                await session.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to update lead #{lead_id}: {exc!r}")


async def list_booking_leads(limit: int = 500) -> list["BookingLead"]:
    """Return recent booking leads (newest first). Empty list on DB error."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BookingLead).order_by(BookingLead.created_at.desc()).limit(limit)
            )
            return list(result.scalars().all())
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to list booking leads: {exc!r}")
        return []


async def list_consultations(limit: int = 500) -> list["ConsultationInquiry"]:
    """Return recent consultation inquiries (newest first). Empty list on DB error."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ConsultationInquiry)
                .order_by(ConsultationInquiry.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to list consultations: {exc!r}")
        return []


async def save_consultation(first_name: str, last_name: str, email: str,
                            phone: Optional[str] = None,
                            destination: Optional[str] = None,
                            budget: Optional[str] = None,
                            message: Optional[str] = None) -> Optional[int]:
    """Insert a consultation inquiry and return its id, or None if the write failed."""
    try:
        async with AsyncSessionLocal() as session:
            inquiry = ConsultationInquiry(
                first_name=first_name, last_name=last_name, email=email,
                phone=phone, destination=destination, budget=budget, message=message,
            )
            session.add(inquiry)
            await session.commit()
            await session.refresh(inquiry)
            print(f"[db] saved consultation inquiry #{inquiry.id} ({email})")
            return inquiry.id
    except Exception as exc:  # noqa: BLE001 - never block a submit on DB errors
        print(f"[db] failed to save consultation inquiry: {exc!r}")
        return None


async def mark_consultation_emailed(inquiry_id: Optional[int], sent: bool) -> None:
    """Update whether the agency notification email was sent for an inquiry."""
    if inquiry_id is None:
        return
    try:
        async with AsyncSessionLocal() as session:
            inquiry = await session.get(ConsultationInquiry, inquiry_id)
            if inquiry is not None:
                inquiry.email_sent = sent
                await session.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to update inquiry #{inquiry_id}: {exc!r}")
