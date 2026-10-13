"""
Async database layer (SQLAlchemy 2.0 + asyncpg).

Provides the booking_leads table and helpers to persist leads. All operations
fail SOFT: if the DB is unreachable we log and return without raising, so a
booking is never blocked by a database hiccup (the email is still attempted).
"""
import os
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy import String, Integer, Text, Boolean, DateTime, select, text, JSON
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
    num_passengers: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cruise_length: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    travel_dates: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
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
    num_passengers: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cruise_length: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    travel_dates: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CallbackRequest(Base):
    __tablename__ = "callback_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(64))
    trip_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="requested")
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ItineraryRecord(Base):
    __tablename__ = "itineraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    voyage_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cruise_line: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ship_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sail_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    itinerary_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# pool_pre_ping + a modest recycle keep connections healthy against serverless
# Postgres (e.g. Neon) that may drop idle connections / auto-suspend.
engine = create_async_engine(
    DATABASE_URL, pool_pre_ping=True, pool_recycle=300, connect_args=_CONNECT_ARGS
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create tables if missing, and add newer columns to existing tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migration: create_all does NOT alter existing tables, so add
        # columns that post-date the original schema. Idempotent via IF NOT EXISTS.
        new_cols = (
            ("num_passengers", "VARCHAR(64)"),
            ("cruise_length", "VARCHAR(64)"),
            ("travel_dates", "VARCHAR(128)"),
        )
        for table_name in ("booking_leads", "consultation_inquiries"):
            for col, ddl in new_cols:
                await conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col} {ddl}")
                )


async def save_booking_lead(full_name: str, email: str, cruise_id: str,
                            cruise_details: Optional[str] = None,
                            session_id: Optional[str] = None,
                            num_passengers: Optional[str] = None,
                            cruise_length: Optional[str] = None,
                            travel_dates: Optional[str] = None) -> Optional[int]:
    """Insert a lead and return its id, or None if the write failed."""
    try:
        async with AsyncSessionLocal() as session:
            lead = BookingLead(
                full_name=full_name, email=email, cruise_id=cruise_id,
                cruise_details=cruise_details, session_id=session_id,
                num_passengers=num_passengers, cruise_length=cruise_length,
                travel_dates=travel_dates,
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
                            num_passengers: Optional[str] = None,
                            cruise_length: Optional[str] = None,
                            travel_dates: Optional[str] = None,
                            message: Optional[str] = None) -> Optional[int]:
    """Insert a consultation inquiry and return its id, or None if the write failed."""
    try:
        async with AsyncSessionLocal() as session:
            inquiry = ConsultationInquiry(
                first_name=first_name, last_name=last_name, email=email,
                phone=phone, destination=destination, budget=budget,
                num_passengers=num_passengers, cruise_length=cruise_length,
                travel_dates=travel_dates, message=message,
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


async def save_callback_request(name: str, phone: str,
                                trip_summary: Optional[str] = None,
                                session_id: Optional[str] = None) -> Optional[int]:
    """Insert a callback request and return its id, or None if the write failed."""
    try:
        async with AsyncSessionLocal() as session:
            req = CallbackRequest(
                name=name, phone=phone, trip_summary=trip_summary, session_id=session_id,
            )
            session.add(req)
            await session.commit()
            await session.refresh(req)
            print(f"[db] saved callback request #{req.id} ({name}, {phone})")
            return req.id
    except Exception as exc:  # noqa: BLE001 - never block a request on DB errors
        print(f"[db] failed to save callback request: {exc!r}")
        return None


async def mark_callback_notified(req_id: Optional[int], notified: bool) -> None:
    """Update whether the team was notified for a callback request."""
    if req_id is None:
        return
    try:
        async with AsyncSessionLocal() as session:
            req = await session.get(CallbackRequest, req_id)
            if req is not None:
                req.notified = notified
                await session.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to update callback #{req_id}: {exc!r}")


async def list_callback_requests(limit: int = 500) -> list["CallbackRequest"]:
    """Return recent callback requests (newest first). Empty list on DB error."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CallbackRequest)
                .order_by(CallbackRequest.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to list callback requests: {exc!r}")
        return []


async def save_itinerary(itinerary_data: dict,
                         token: Optional[str] = None,
                         client_email: Optional[str] = None) -> tuple[str, Optional[int]]:
    """
    Persist an itinerary JSON record. Generates a unique secure URL-safe token
    if not provided. Returns (token, record_id).
    """
    token = token or secrets.token_urlsafe(12)
    # Extract indexable metadata fields from the itinerary schema
    client_obj = itinerary_data.get("client", {})
    client_name = client_obj.get("leadGuest") if isinstance(client_obj, dict) else None
    booking_obj = itinerary_data.get("booking", {})
    cruise_line = booking_obj.get("cruiseLine") if isinstance(booking_obj, dict) else None
    ship_name = booking_obj.get("ship") if isinstance(booking_obj, dict) else None
    embarks = booking_obj.get("embarks", {}) if isinstance(booking_obj, dict) else {}
    sail_date = embarks.get("date") if isinstance(embarks, dict) else None
    voyage_id = itinerary_data.get("id")

    try:
        async with AsyncSessionLocal() as session:
            # Check if record with token already exists (update)
            result = await session.execute(
                select(ItineraryRecord).where(ItineraryRecord.token == token)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.itinerary_data = itinerary_data
                existing.client_name = client_name or existing.client_name
                existing.cruise_line = cruise_line or existing.cruise_line
                existing.ship_name = ship_name or existing.ship_name
                existing.sail_date = sail_date or existing.sail_date
                existing.voyage_id = voyage_id or existing.voyage_id
                if client_email:
                    existing.client_email = client_email
                await session.commit()
                print(f"[db] updated itinerary #{existing.id} (token={token})")
                return token, existing.id
            else:
                record = ItineraryRecord(
                    token=token,
                    voyage_id=voyage_id,
                    client_name=client_name,
                    client_email=client_email,
                    cruise_line=cruise_line,
                    ship_name=ship_name,
                    sail_date=sail_date,
                    itinerary_data=itinerary_data,
                )
                session.add(record)
                await session.commit()
                await session.refresh(record)
                print(f"[db] saved itinerary #{record.id} (token={token})")
                return token, record.id
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to save itinerary: {exc!r}")
        return token, None


async def get_itinerary_by_token(token: str) -> Optional[dict]:
    """Retrieve itinerary data dictionary by unique token."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ItineraryRecord).where(ItineraryRecord.token == token)
            )
            record = result.scalar_one_or_none()
            if record:
                return record.itinerary_data
            return None
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to get itinerary for token={token}: {exc!r}")
        return None


async def list_itineraries(limit: int = 100) -> list[dict]:
    """Return recent itineraries for administrative overview."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ItineraryRecord).order_by(ItineraryRecord.created_at.desc()).limit(limit)
            )
            records = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "token": r.token,
                    "voyage_id": r.voyage_id,
                    "client_name": r.client_name,
                    "client_email": r.client_email,
                    "cruise_line": r.cruise_line,
                    "ship_name": r.ship_name,
                    "sail_date": r.sail_date,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
    except Exception as exc:  # noqa: BLE001
        print(f"[db] failed to list itineraries: {exc!r}")
        return []

