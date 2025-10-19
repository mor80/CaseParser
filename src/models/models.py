import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Case(Base):
    """Модель для хранения информации о кейсах"""

    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    steam_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    portfolio_entries = relationship(
        "Portfolio",
        back_populates="case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Индексы для оптимизации запросов
    __table_args__ = (
        Index("idx_case_name", "name"),
        Index("idx_case_created_at", "created_at"),
    )


class PriceHistory(Base):
    """Модель для хранения исторических данных о ценах"""

    __tablename__ = "price_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="RUB")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Индексы для оптимизации запросов
    __table_args__ = (
        Index("idx_price_case_id", "case_id"),
        Index("idx_price_timestamp", "timestamp"),
        Index("idx_price_case_timestamp", "case_id", "timestamp"),
    )


class CaseStatistics(Base):
    """Модель для хранения статистики по кейсам"""

    __tablename__ = "case_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    current_price = Column(Float)
    min_price_30d = Column(Float)
    max_price_30d = Column(Float)
    avg_price_30d = Column(Float)
    price_change_24h = Column(Float)
    price_change_7d = Column(Float)
    price_change_30d = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Индексы для оптимизации запросов
    __table_args__ = (
        Index("idx_stats_case_id", "case_id"),
        Index("idx_stats_last_updated", "last_updated"),
    )
