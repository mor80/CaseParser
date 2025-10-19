from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATABASE_URL
from src.models import Base, Case, CaseStatistics, PriceHistory


class DatabaseService:
    """Сервис для работы с базой данных"""
    
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_session(self) -> AsyncSession:
        """Получение сессии базы данных"""
        async with self.async_session() as session:
            yield session
    
    async def save_case(self, name: str, steam_url: Optional[str] = None) -> Case:
        """Сохранение или получение существующего кейса"""
        async with self.async_session() as session:
            # Проверяем, существует ли кейс
            stmt = select(Case).where(Case.name == name)
            result = await session.execute(stmt)
            case = result.scalar_one_or_none()
            
            if case is None:
                # Создаем новый кейс
                case = Case(name=name, steam_url=steam_url)
                session.add(case)
                await session.commit()
                await session.refresh(case)
            else:
                # Обновляем время последнего обновления
                if steam_url and case.steam_url != steam_url:
                    case.steam_url = steam_url
                case.updated_at = datetime.utcnow()
                await session.commit()
            
            return case
    
    async def save_price(self, case_id: str, price: float, currency: str = 'RUB') -> PriceHistory:
        """Сохранение цены в историю"""
        async with self.async_session() as session:
            price_history = PriceHistory(
                case_id=case_id,
                price=price,
                currency=currency,
                timestamp=datetime.utcnow()
            )
            session.add(price_history)
            await session.commit()
            await session.refresh(price_history)
            return price_history
    
    async def get_price_history(self, case_id: str, days: int = 30) -> List[PriceHistory]:
        """Получение истории цен за указанное количество дней"""
        async with self.async_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            stmt = (
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.case_id == case_id,
                        PriceHistory.timestamp >= start_date
                    )
                )
                .order_by(PriceHistory.timestamp.asc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_all_cases(self) -> List[Case]:
        """Получение всех кейсов"""
        async with self.async_session() as session:
            stmt = select(Case).order_by(Case.name)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_latest_prices(self) -> List[Tuple[Case, PriceHistory]]:
        """Получение последних цен для всех кейсов"""
        async with self.async_session() as session:
            # Подзапрос для получения последней цены каждого кейса
            latest_prices_subquery = (
                select(
                    PriceHistory.case_id,
                    func.max(PriceHistory.timestamp).label('latest_timestamp')
                )
                .group_by(PriceHistory.case_id)
                .subquery()
            )
            
            stmt = (
                select(Case, PriceHistory)
                .join(PriceHistory, Case.id == PriceHistory.case_id)
                .join(
                    latest_prices_subquery,
                    and_(
                        PriceHistory.case_id == latest_prices_subquery.c.case_id,
                        PriceHistory.timestamp == latest_prices_subquery.c.latest_timestamp
                    )
                )
                .order_by(Case.name)
            )
            
            result = await session.execute(stmt)
            return result.all()

    async def get_latest_prices_for_cases(self, case_ids: List[str]) -> Dict[str, PriceHistory]:
        """Получение последних цен для набора кейсов"""
        if not case_ids:
            return {}

        # Преобразуем идентификаторы кейсов к UUID и убираем дубликаты
        unique_case_ids = []
        seen = set()
        for case_id in case_ids:
            try:
                uuid_case_id = case_id if isinstance(case_id, UUID) else UUID(str(case_id))
            except (TypeError, ValueError):
                continue

            if uuid_case_id not in seen:
                seen.add(uuid_case_id)
                unique_case_ids.append(uuid_case_id)

        if not unique_case_ids:
            return {}

        async with self.async_session() as session:
            latest_prices_subquery = (
                select(
                    PriceHistory.case_id,
                    func.max(PriceHistory.timestamp).label('latest_timestamp')
                )
                .where(PriceHistory.case_id.in_(unique_case_ids))
                .group_by(PriceHistory.case_id)
                .subquery()
            )

            stmt = (
                select(PriceHistory)
                .join(
                    latest_prices_subquery,
                    and_(
                        PriceHistory.case_id == latest_prices_subquery.c.case_id,
                        PriceHistory.timestamp == latest_prices_subquery.c.latest_timestamp
                    )
                )
            )

            result = await session.execute(stmt)
            prices = result.scalars().all()
            return {str(price.case_id): price for price in prices}
    
    async def calculate_statistics(self, case_id: str) -> Dict:
        """Расчет статистики для кейса за последние 30 дней"""
        async with self.async_session() as session:
            start_date = datetime.utcnow() - timedelta(days=30)
            
            # Получаем данные за 30 дней
            stmt = (
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.case_id == case_id,
                        PriceHistory.timestamp >= start_date
                    )
                )
                .order_by(PriceHistory.timestamp)
            )
            result = await session.execute(stmt)
            prices = result.scalars().all()
            
            if not prices:
                return {}
            
            price_values = [p.price for p in prices]
            current_price = price_values[-1]
            
            # Статистика за 30 дней
            min_price_30d = min(price_values)
            max_price_30d = max(price_values)
            avg_price_30d = sum(price_values) / len(price_values)
            
            # Изменение за 24 часа
            day_ago = datetime.utcnow() - timedelta(days=1)
            day_ago_stmt = (
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.case_id == case_id,
                        PriceHistory.timestamp >= day_ago
                    )
                )
                .order_by(PriceHistory.timestamp)
                .limit(1)
            )
            day_ago_result = await session.execute(day_ago_stmt)
            day_ago_price = day_ago_result.scalar_one_or_none()
            
            price_change_24h = 0
            if day_ago_price:
                price_change_24h = ((current_price - day_ago_price.price) / day_ago_price.price) * 100
            
            # Изменение за 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_ago_stmt = (
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.case_id == case_id,
                        PriceHistory.timestamp >= week_ago
                    )
                )
                .order_by(PriceHistory.timestamp)
                .limit(1)
            )
            week_ago_result = await session.execute(week_ago_stmt)
            week_ago_price = week_ago_result.scalar_one_or_none()
            
            price_change_7d = 0
            if week_ago_price:
                price_change_7d = ((current_price - week_ago_price.price) / week_ago_price.price) * 100
            
            # Изменение за 30 дней
            price_change_30d = 0
            if len(price_values) > 1:
                price_change_30d = ((current_price - price_values[0]) / price_values[0]) * 100
            
            return {
                'current_price': current_price,
                'min_price_30d': min_price_30d,
                'max_price_30d': max_price_30d,
                'avg_price_30d': avg_price_30d,
                'price_change_24h': price_change_24h,
                'price_change_7d': price_change_7d,
                'price_change_30d': price_change_30d,
                'last_updated': datetime.utcnow()
            }
    
    async def update_case_statistics(self, case_id: str):
        """Обновление статистики для кейса"""
        async with self.async_session() as session:
            stats = await self.calculate_statistics(case_id)
            if not stats:
                return
            
            # Проверяем, существует ли статистика
            stmt = select(CaseStatistics).where(CaseStatistics.case_id == case_id)
            result = await session.execute(stmt)
            case_stats = result.scalar_one_or_none()
            
            if case_stats is None:
                case_stats = CaseStatistics(case_id=case_id, **stats)
                session.add(case_stats)
            else:
                for key, value in stats.items():
                    setattr(case_stats, key, value)
            
            await session.commit()
    
    async def get_case_statistics(self, case_id: str) -> Optional[CaseStatistics]:
        """Получение статистики кейса"""
        async with self.async_session() as session:
            stmt = select(CaseStatistics).where(CaseStatistics.case_id == case_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_latest_price_for_case(self, case_id: str) -> Optional[PriceHistory]:
        """Получение последней цены для кейса"""
        async with self.async_session() as session:
            stmt = select(PriceHistory).where(
                PriceHistory.case_id == case_id
            ).order_by(PriceHistory.timestamp.desc()).limit(1)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_all_statistics(self) -> List[CaseStatistics]:
        """Получение статистики всех кейсов"""
        async with self.async_session() as session:
            stmt = select(CaseStatistics).order_by(CaseStatistics.last_updated.desc())
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Очистка старых данных (старше указанного количества дней)"""
        async with self.async_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Удаляем старые записи истории цен
            stmt = select(PriceHistory).where(PriceHistory.timestamp < cutoff_date)
            result = await session.execute(stmt)
            old_prices = result.scalars().all()
            
            for price in old_prices:
                await session.delete(price)
            
            await session.commit()
            return len(old_prices)
