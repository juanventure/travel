"""
Async database layer (SQLAlchemy 2.0 + asyncpg).

Provides the booking_leads table and helpers to persist leads. All operations
fail SOFT: if the DB is unreachable we log and return without raising, so a
booking is never blocked by a database hiccup (the email is still attempted).
"""
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


def _async_url(url: str) -> str:
    # SQLAlchemy async needs the asyncpg driver prefix.
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = _async_url(
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


engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
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
