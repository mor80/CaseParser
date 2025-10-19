from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import desc, func, select

from src.core.database import DatabaseService
from src.models import Case, CaseStatistics, PriceHistory


class AnalyticsService:
    """Сервис для аналитики и статистики по кейсам"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def get_top_gainers(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Получение кейсов с наибольшим ростом цены за указанный период"""
        async with self.db_service.async_session() as session:
            # Получаем статистику с сортировкой по росту цены
            if days == 1:
                order_field = CaseStatistics.price_change_24h
            elif days == 7:
                order_field = CaseStatistics.price_change_7d
            else:
                order_field = CaseStatistics.price_change_30d
            
            stmt = (
                select(Case, CaseStatistics)
                .join(CaseStatistics, Case.id == CaseStatistics.case_id)
                .where(order_field.isnot(None))
                .order_by(desc(order_field))
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            cases_with_stats = result.all()
            
            return [
                {
                    'case_id': str(case.id),
                    'name': case.name,
                    'current_price': stats.current_price,
                    'price_change': getattr(stats, f'price_change_{days}d' if days > 1 else 'price_change_24h'),
                    'last_updated': stats.last_updated
                }
                for case, stats in cases_with_stats
            ]
    
    async def get_top_losers(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Получение кейсов с наибольшим падением цены за указанный период"""
        async with self.db_service.async_session() as session:
            # Получаем статистику с сортировкой по падению цены
            if days == 1:
                order_field = CaseStatistics.price_change_24h
            elif days == 7:
                order_field = CaseStatistics.price_change_7d
            else:
                order_field = CaseStatistics.price_change_30d
            
            stmt = (
                select(Case, CaseStatistics)
                .join(CaseStatistics, Case.id == CaseStatistics.case_id)
                .where(order_field.isnot(None))
                .order_by(order_field.asc())
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            cases_with_stats = result.all()
            
            return [
                {
                    'case_id': str(case.id),
                    'name': case.name,
                    'current_price': stats.current_price,
                    'price_change': getattr(stats, f'price_change_{days}d' if days > 1 else 'price_change_24h'),
                    'last_updated': stats.last_updated
                }
                for case, stats in cases_with_stats
            ]
    
    async def get_most_volatile_cases(self, days: int = 30, limit: int = 10) -> List[Dict]:
        """Получение наиболее волатильных кейсов (с наибольшим разбросом цен)"""
        async with self.db_service.async_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Подзапрос для расчета волатильности (стандартное отклонение)
            volatility_subquery = (
                select(
                    PriceHistory.case_id,
                    func.stddev(PriceHistory.price).label('volatility'),
                    func.avg(PriceHistory.price).label('avg_price'),
                    func.min(PriceHistory.price).label('min_price'),
                    func.max(PriceHistory.price).label('max_price')
                )
                .where(PriceHistory.timestamp >= start_date)
                .group_by(PriceHistory.case_id)
                .having(func.count(PriceHistory.id) > 5)  # Минимум 5 записей для расчета
                .subquery()
            )
            
            stmt = (
                select(Case, volatility_subquery)
                .join(volatility_subquery, Case.id == volatility_subquery.c.case_id)
                .order_by(desc(volatility_subquery.c.volatility))
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            cases_with_volatility = result.all()
            
            return [
                {
                    'case_id': str(case.id),
                    'name': case.name,
                    'volatility': float(volatility.volatility),
                    'avg_price': float(volatility.avg_price),
                    'min_price': float(volatility.min_price),
                    'max_price': float(volatility.max_price),
                    'price_range': float(volatility.max_price - volatility.min_price)
                }
                for case, volatility in cases_with_volatility
            ]
    
    async def get_market_overview(self) -> Dict:
        """Получение общего обзора рынка"""
        async with self.db_service.async_session() as session:
            # Общее количество кейсов
            total_cases_stmt = select(func.count(Case.id))
            total_cases_result = await session.execute(total_cases_stmt)
            total_cases = total_cases_result.scalar()
            
            # Количество кейсов со статистикой
            cases_with_stats_stmt = select(func.count(CaseStatistics.id))
            cases_with_stats_result = await session.execute(cases_with_stats_stmt)
            cases_with_stats = cases_with_stats_result.scalar()
            
            # Средняя цена всех кейсов
            avg_price_stmt = select(func.avg(CaseStatistics.current_price))
            avg_price_result = await session.execute(avg_price_stmt)
            avg_price = avg_price_result.scalar()
            
            # Количество кейсов с ростом за 24 часа
            gainers_24h_stmt = (
                select(func.count(CaseStatistics.id))
                .where(CaseStatistics.price_change_24h > 0)
            )
            gainers_24h_result = await session.execute(gainers_24h_stmt)
            gainers_24h = gainers_24h_result.scalar()
            
            # Количество кейсов с падением за 24 часа
            losers_24h_stmt = (
                select(func.count(CaseStatistics.id))
                .where(CaseStatistics.price_change_24h < 0)
            )
            losers_24h_result = await session.execute(losers_24h_stmt)
            losers_24h = losers_24h_result.scalar()
            
            # Последнее обновление
            last_update_stmt = select(func.max(CaseStatistics.last_updated))
            last_update_result = await session.execute(last_update_stmt)
            last_update = last_update_result.scalar()
            
            return {
                'total_cases': total_cases,
                'cases_with_statistics': cases_with_stats,
                'average_price': float(avg_price) if avg_price else 0,
                'gainers_24h': gainers_24h,
                'losers_24h': losers_24h,
                'last_update': last_update,
                'market_sentiment': 'bullish' if gainers_24h > losers_24h else 'bearish' if losers_24h > gainers_24h else 'neutral'
            }
    
    async def get_price_trends(self, case_id: str, days: int = 30) -> Dict:
        """Анализ трендов цены для конкретного кейса"""
        price_history = await self.db_service.get_price_history(case_id, days)
        
        if len(price_history) < 2:
            return {'trend': 'insufficient_data', 'message': 'Недостаточно данных для анализа'}
        
        prices = [p.price for p in price_history]
        
        # Простой анализ тренда
        first_half = prices[:len(prices)//2]
        second_half = prices[len(prices)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        trend_direction = 'up' if second_avg > first_avg else 'down' if second_avg < first_avg else 'sideways'
        trend_strength = abs(second_avg - first_avg) / first_avg * 100
        
        # Анализ волатильности
        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        volatility = sum(price_changes) / len(price_changes) if price_changes else 0
        
        return {
            'trend': trend_direction,
            'trend_strength': trend_strength,
            'volatility': volatility,
            'price_range': {
                'min': min(prices),
                'max': max(prices),
                'current': prices[-1]
            },
            'data_points': len(prices)
        }
    
    async def get_correlation_analysis(self, case_id_1: str, case_id_2: str, days: int = 30) -> Dict:
        """Анализ корреляции между двумя кейсами"""
        history_1 = await self.db_service.get_price_history(case_id_1, days)
        history_2 = await self.db_service.get_price_history(case_id_2, days)
        
        if len(history_1) < 2 or len(history_2) < 2:
            return {'correlation': 0, 'message': 'Недостаточно данных для анализа корреляции'}
        
        # Создаем словари для сопоставления по времени
        prices_1 = {p.timestamp.date(): p.price for p in history_1}
        prices_2 = {p.timestamp.date(): p.price for p in history_2}
        
        # Находим общие даты
        common_dates = set(prices_1.keys()) & set(prices_2.keys())
        
        if len(common_dates) < 2:
            return {'correlation': 0, 'message': 'Недостаточно общих дат для анализа'}
        
        # Вычисляем корреляцию
        prices_1_list = [prices_1[date] for date in sorted(common_dates)]
        prices_2_list = [prices_2[date] for date in sorted(common_dates)]
        
        # Простая корреляция Пирсона
        n = len(prices_1_list)
        sum_1 = sum(prices_1_list)
        sum_2 = sum(prices_2_list)
        sum_1_sq = sum(x*x for x in prices_1_list)
        sum_2_sq = sum(x*x for x in prices_2_list)
        sum_12 = sum(x*y for x, y in zip(prices_1_list, prices_2_list))
        
        numerator = n * sum_12 - sum_1 * sum_2
        denominator = ((n * sum_1_sq - sum_1**2) * (n * sum_2_sq - sum_2**2))**0.5
        
        correlation = numerator / denominator if denominator != 0 else 0
        
        return {
            'correlation': correlation,
            'common_dates': len(common_dates),
            'interpretation': 'strong_positive' if correlation > 0.7 else 'moderate_positive' if correlation > 0.3 else 'weak_positive' if correlation > 0 else 'weak_negative' if correlation > -0.3 else 'moderate_negative' if correlation > -0.7 else 'strong_negative'
        }
