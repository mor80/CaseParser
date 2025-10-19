"""Импорт всех моделей для правильной инициализации SQLAlchemy"""

from .models import Base, Case, CaseStatistics, PriceHistory
from .portfolio import Portfolio, PortfolioStatistics
from .user import User

__all__ = [
    'Base',
    'Case', 
    'CaseStatistics', 
    'PriceHistory', 
    'Portfolio',
    'PortfolioStatistics',
    'User'
]
