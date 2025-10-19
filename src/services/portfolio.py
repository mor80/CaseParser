"""
Сервис для управления портфелем кейсов
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, select

from src.core.database import DatabaseService
from src.models.models import Case
from src.models.portfolio import Portfolio, PortfolioStatistics


class PortfolioService:
    """Сервис для управления портфелем кейсов"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def add_to_portfolio(
        self, 
        case_id: str, 
        quantity: float, 
        purchase_price: float, 
        user_id: str = 'default',
        notes: str = None
    ) -> Portfolio:
        """Добавление кейсов в портфель"""
        async with self.db_service.async_session() as session:
            portfolio_entry = Portfolio(
                case_id=case_id,
                user_id=user_id,
                quantity=Decimal(str(quantity)),
                purchase_price=Decimal(str(purchase_price)),
                notes=notes,
                purchase_date=datetime.utcnow()
            )
            
            session.add(portfolio_entry)
            await session.commit()
            await session.refresh(portfolio_entry)
            
            # Обновляем статистику портфеля
            await self.update_portfolio_statistics(user_id)
            
            return portfolio_entry
    
    async def get_portfolio(self, user_id: str = 'default') -> List[Dict]:
        """Получение портфеля пользователя с текущими ценами"""
        async with self.db_service.async_session() as session:
            # Получаем все записи портфеля с информацией о кейсах
            stmt = (
                select(Portfolio, Case)
                .join(Case, Portfolio.case_id == Case.id)
                .where(Portfolio.user_id == user_id)
                .order_by(Portfolio.purchase_date.desc())
            )
            
            result = await session.execute(stmt)
            portfolio_entries = result.all()

        if not portfolio_entries:
            return []

        case_ids = [str(case.id) for _, case in portfolio_entries]
        latest_prices = await self.db_service.get_latest_prices_for_cases(case_ids)
            
        portfolio_data = []
        for portfolio, case in portfolio_entries:
            latest_price_entry = latest_prices.get(str(case.id))
            current_price = float(latest_price_entry.price) if latest_price_entry else None
            current_price_timestamp = latest_price_entry.timestamp if latest_price_entry else None
            
            quantity = Decimal(portfolio.quantity)
            purchase_price = Decimal(portfolio.purchase_price)
            total_investment = float(quantity * purchase_price)
            current_value = float(quantity * Decimal(str(current_price))) if current_price is not None else 0.0
            profit = current_value - total_investment
            profit_percentage = (profit / total_investment * 100) if total_investment > 0 else 0.0
            
            portfolio_data.append({
                'id': str(portfolio.id),
                'case_id': str(portfolio.case_id),
                'case_name': case.name,
                'quantity': float(quantity),
                'purchase_price': float(purchase_price),
                'purchase_date': portfolio.purchase_date,
                'current_price': current_price,
                'current_price_timestamp': current_price_timestamp,
                'total_investment': total_investment,
                'current_value': current_value,
                'profit': profit,
                'profit_percentage': profit_percentage,
                'notes': portfolio.notes
            })
        
        return portfolio_data
    
    async def get_current_price(self, case_id: str) -> Optional[float]:
        """Получение текущей цены кейса"""
        latest_prices = await self.db_service.get_latest_prices_for_cases([case_id])
        latest_entry = latest_prices.get(str(case_id))
        return float(latest_entry.price) if latest_entry else None
    
    async def get_portfolio_statistics(self, user_id: str = 'default') -> Dict:
        """Получение статистики портфеля"""
        async with self.db_service.async_session() as session:
            # Получаем или создаем статистику
            stmt = select(PortfolioStatistics).where(PortfolioStatistics.user_id == user_id)
            result = await session.execute(stmt)
            stats = result.scalar_one_or_none()
            
            if not stats:
                await self.update_portfolio_statistics(user_id)
                # Получаем обновленную статистику
                result = await session.execute(stmt)
                stats = result.scalar_one_or_none()
            
            if stats:
                return {
                    'total_investment': float(stats.total_investment),
                    'current_value': float(stats.current_value),
                    'total_profit': float(stats.total_profit),
                    'profit_percentage': float(stats.profit_percentage),
                    'total_cases': float(stats.total_cases),
                    'last_updated': stats.last_updated
                }
            
            return {
                'total_investment': 0,
                'current_value': 0,
                'total_profit': 0,
                'profit_percentage': 0,
                'total_cases': 0,
                'last_updated': datetime.utcnow()
            }
    
    async def update_portfolio_statistics(self, user_id: str = 'default'):
        """Обновление статистики портфеля"""
        async with self.db_service.async_session() as session:
            # Получаем все записи портфеля
            stmt = (
                select(Portfolio, Case)
                .join(Case, Portfolio.case_id == Case.id)
                .where(Portfolio.user_id == user_id)
            )
            
            result = await session.execute(stmt)
            portfolio_entries = result.all()

        if not portfolio_entries:
            # Если записей нет, то удаляем существующую статистику (если была)
            await self._reset_portfolio_statistics(user_id)
            return

        case_ids = [str(case.id) for _, case in portfolio_entries]
        latest_prices = await self.db_service.get_latest_prices_for_cases(case_ids)
            
        total_investment = Decimal('0')
        current_value = Decimal('0')
        total_cases = Decimal('0')
            
        for portfolio, case in portfolio_entries:
            # Рассчитываем инвестиции
            investment = portfolio.quantity * portfolio.purchase_price
            total_investment += investment
            total_cases += portfolio.quantity
            
            # Получаем текущую цену
            latest_price_entry = latest_prices.get(str(case.id))
            if latest_price_entry is not None:
                current_value += portfolio.quantity * Decimal(str(latest_price_entry.price))
            
        # Рассчитываем прибыль
        total_profit = current_value - total_investment
        profit_percentage = (total_profit / total_investment * 100) if total_investment > 0 else Decimal('0')
            
        # Обновляем или создаем статистику
        async with self.db_service.async_session() as session:
            stmt = select(PortfolioStatistics).where(PortfolioStatistics.user_id == user_id)
            result = await session.execute(stmt)
            stats = result.scalar_one_or_none()

            if stats:
                stats.total_investment = total_investment
                stats.current_value = current_value
                stats.total_profit = total_profit
                stats.profit_percentage = profit_percentage
                stats.total_cases = total_cases
                stats.last_updated = datetime.utcnow()
            else:
                stats = PortfolioStatistics(
                    user_id=user_id,
                    total_investment=total_investment,
                    current_value=current_value,
                    total_profit=total_profit,
                    profit_percentage=profit_percentage,
                    total_cases=total_cases,
                    last_updated=datetime.utcnow()
                )
                session.add(stats)

            await session.commit()

    async def _reset_portfolio_statistics(self, user_id: str):
        """Сброс статистики портфеля до нулевых значений"""
        async with self.db_service.async_session() as session:
            stmt = select(PortfolioStatistics).where(PortfolioStatistics.user_id == user_id)
            result = await session.execute(stmt)
            stats = result.scalar_one_or_none()

            if stats:
                stats.total_investment = Decimal('0')
                stats.current_value = Decimal('0')
                stats.total_profit = Decimal('0')
                stats.profit_percentage = Decimal('0')
                stats.total_cases = Decimal('0')
                stats.last_updated = datetime.utcnow()
            else:
                stats = PortfolioStatistics(
                    user_id=user_id,
                    total_investment=Decimal('0'),
                    current_value=Decimal('0'),
                    total_profit=Decimal('0'),
                    profit_percentage=Decimal('0'),
                    total_cases=Decimal('0'),
                    last_updated=datetime.utcnow()
                )
                session.add(stats)

            await session.commit()
    
    async def remove_from_portfolio(self, portfolio_id: str, user_id: str = 'default') -> bool:
        """Удаление записи из портфеля"""
        async with self.db_service.async_session() as session:
            stmt = select(Portfolio).where(
                and_(
                    Portfolio.id == portfolio_id,
                    Portfolio.user_id == user_id
                )
            )
            
            result = await session.execute(stmt)
            portfolio_entry = result.scalar_one_or_none()
            
            if portfolio_entry:
                await session.delete(portfolio_entry)
                await session.commit()
                
                # Обновляем статистику
                await self.update_portfolio_statistics(user_id)
                return True
            
            return False
    
    async def update_portfolio_entry(
        self, 
        portfolio_id: str, 
        quantity: float = None, 
        purchase_price: float = None,
        notes: str = None,
        user_id: str = 'default'
    ) -> bool:
        """Обновление записи в портфеле"""
        async with self.db_service.async_session() as session:
            stmt = select(Portfolio).where(
                and_(
                    Portfolio.id == portfolio_id,
                    Portfolio.user_id == user_id
                )
            )
            
            result = await session.execute(stmt)
            portfolio_entry = result.scalar_one_or_none()
            
            if portfolio_entry:
                if quantity is not None:
                    portfolio_entry.quantity = Decimal(str(quantity))
                if purchase_price is not None:
                    portfolio_entry.purchase_price = Decimal(str(purchase_price))
                if notes is not None:
                    portfolio_entry.notes = notes
                
                portfolio_entry.updated_at = datetime.utcnow()
                await session.commit()
                
                # Обновляем статистику
                await self.update_portfolio_statistics(user_id)
                return True
            
            return False
    
    async def get_portfolio_performance(self, user_id: str = 'default', days: int = 30) -> Dict:
        """Получение производительности портфеля за период"""
        async with self.db_service.async_session() as session:
            # Получаем статистику портфеля
            stats = await self.get_portfolio_statistics(user_id)
            
            # Рассчитываем изменение за период
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_date.replace(day=start_date.day - days)
            
            # Здесь можно добавить логику для расчета исторической производительности
            # Пока возвращаем текущую статистику
            
            return {
                'current_stats': stats,
                'period_days': days,
                'performance_rating': self.calculate_performance_rating(stats['profit_percentage'])
            }
    
    def calculate_performance_rating(self, profit_percentage: float) -> str:
        """Расчет рейтинга производительности портфеля"""
        if profit_percentage >= 50:
            return "Отличная"
        elif profit_percentage >= 20:
            return "Хорошая"
        elif profit_percentage >= 0:
            return "Положительная"
        elif profit_percentage >= -10:
            return "Нейтральная"
        else:
            return "Отрицательная"
