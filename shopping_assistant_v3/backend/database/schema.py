"""SQLAlchemy models for Shopping Assistant V3.

Six core tables matching the architecture guide:
  jobs, conversations, messages, agent_runs, products, price_estimates.
Schema is created via Base.metadata.create_all() — no Alembic for MVP.
"""

import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="conversation")


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, default="chat")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=True, index=True
    )
    request_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    conversation: Mapped["Conversation | None"] = relationship(back_populates="jobs")
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Agent Runs
# ---------------------------------------------------------------------------

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=False, index=True
    )
    component: Mapped[str] = mapped_column(String(100), nullable=False)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="agent_runs")


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sale_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_source_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    job: Mapped["Job"] = relationship(back_populates="products")
    price_estimates: Mapped[list["PriceEstimate"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Price Estimates
# ---------------------------------------------------------------------------

class PriceEstimate(Base):
    __tablename__ = "price_estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    estimated_value_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    deal_score: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    product: Mapped["Product"] = relationship(back_populates="price_estimates")
