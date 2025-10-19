import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .models import Base


class Portfolio(Base):
    """Модель для хранения портфеля пользователя"""
    __tablename__ = "portfolio"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), nullable=False)
    user_id = Column(String(255), nullable=False, default='default')  # Для поддержки множественных пользователей
    quantity = Column(Numeric(10, 2), nullable=False)  # Количество кейсов
    purchase_price = Column(Numeric(10, 2), nullable=False)  # Цена покупки за штуку
    purchase_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(String(500))  # Заметки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    case = relationship("Case", back_populates="portfolio_entries")
    
    # Индексы
    __table_args__ = (
        Index('idx_portfolio_user_id', 'user_id'),
        Index('idx_portfolio_case_id', 'case_id'),
        Index('idx_portfolio_purchase_date', 'purchase_date'),
    )


class PortfolioStatistics(Base):
    """Модель для хранения статистики портфеля"""
    __tablename__ = "portfolio_statistics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, default='default')
    total_investment = Column(Numeric(15, 2), nullable=False, default=0)  # Общие инвестиции
    current_value = Column(Numeric(15, 2), nullable=False, default=0)  # Текущая стоимость
    total_profit = Column(Numeric(15, 2), nullable=False, default=0)  # Общая прибыль
    profit_percentage = Column(Numeric(5, 2), nullable=False, default=0)  # Процент прибыли
    total_cases = Column(Numeric(10, 2), nullable=False, default=0)  # Общее количество кейсов
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Индексы
    __table_args__ = (
        Index('idx_portfolio_stats_user_id', 'user_id'),
        Index('idx_portfolio_stats_last_updated', 'last_updated'),
    )
