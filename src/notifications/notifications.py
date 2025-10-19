import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, select

from src.core.database import DatabaseService
from src.models.models import Case, CaseStatistics, PriceHistory
from src.notifications.telegram_bot import TelegramConfig, TelegramNotificationService


@dataclass
class AlertThreshold:
    """Пороговые значения для алертов"""
    price_change_percent: float  # Процент изменения цены
    min_price: Optional[float] = None  # Минимальная цена для алерта
    max_price: Optional[float] = None  # Максимальная цена для алерта


@dataclass
class Alert:
    """Структура алерта"""
    case_id: str
    case_name: str
    current_price: float
    previous_price: float
    price_change_percent: float
    alert_type: str  # 'price_increase', 'price_decrease', 'price_threshold'
    timestamp: datetime


class NotificationService:
    """Сервис для отправки уведомлений о значительных изменениях цен"""
    
    def __init__(self, db_service: DatabaseService, telegram_config: Optional[TelegramConfig] = None):
        self.db_service = db_service
        self.alert_thresholds = {
            'high_volatility': AlertThreshold(price_change_percent=10.0),
            'medium_volatility': AlertThreshold(price_change_percent=5.0),
            'low_volatility': AlertThreshold(price_change_percent=2.0)
        }
        self.telegram_config = telegram_config
        self.telegram_service = None
        self.logger = logging.getLogger(__name__)
        
        if telegram_config:
            self.telegram_service = TelegramNotificationService(db_service, telegram_config)
    
    async def check_price_alerts(self) -> List[Alert]:
        """Проверка цен на предмет значительных изменений"""
        alerts = []
        
        async with self.db_service.async_session() as session:
            # Получаем все кейсы со статистикой
            stmt = (
                select(Case, CaseStatistics)
                .join(CaseStatistics, Case.id == CaseStatistics.case_id)
                .where(CaseStatistics.current_price.isnot(None))
            )
            result = await session.execute(stmt)
            cases_with_stats = result.all()
            
            for case, stats in cases_with_stats:
                # Проверяем изменения за 24 часа
                if stats.price_change_24h is not None:
                    alert = await self._check_price_change_alert(
                        case, stats, stats.price_change_24h, '24h'
                    )
                    if alert:
                        alerts.append(alert)
                
                # Проверяем изменения за 7 дней
                if stats.price_change_7d is not None:
                    alert = await self._check_price_change_alert(
                        case, stats, stats.price_change_7d, '7d'
                    )
                    if alert:
                        alerts.append(alert)
        
        return alerts
    
    async def _check_price_change_alert(
        self, 
        case: Case, 
        stats: CaseStatistics, 
        price_change: float, 
        period: str
    ) -> Optional[Alert]:
        """Проверка конкретного изменения цены на предмет алерта"""
        
        # Определяем пороговое значение в зависимости от периода
        if period == '24h':
            threshold = self.alert_thresholds['medium_volatility'].price_change_percent
        elif period == '7d':
            threshold = self.alert_thresholds['high_volatility'].price_change_percent
        else:
            threshold = self.alert_thresholds['low_volatility'].price_change_percent
        
        # Проверяем, превышает ли изменение пороговое значение
        if abs(price_change) >= threshold:
            # Получаем предыдущую цену для расчета
            previous_price = await self._get_previous_price(case.id, period)
            
            if previous_price:
                return Alert(
                    case_id=str(case.id),
                    case_name=case.name,
                    current_price=stats.current_price,
                    previous_price=previous_price,
                    price_change_percent=price_change,
                    alert_type='price_increase' if price_change > 0 else 'price_decrease',
                    timestamp=datetime.utcnow()
                )
        
        return None
    
    async def _get_previous_price(self, case_id: str, period: str) -> Optional[float]:
        """Получение предыдущей цены для сравнения"""
        async with self.db_service.async_session() as session:
            if period == '24h':
                # Цена 24 часа назад
                day_ago = datetime.utcnow() - timedelta(days=1)
                stmt = (
                    select(PriceHistory)
                    .where(
                        and_(
                            PriceHistory.case_id == case_id,
                            PriceHistory.timestamp >= day_ago
                        )
                    )
                    .order_by(PriceHistory.timestamp.asc())
                    .limit(1)
                )
            elif period == '7d':
                # Цена 7 дней назад
                week_ago = datetime.utcnow() - timedelta(days=7)
                stmt = (
                    select(PriceHistory)
                    .where(
                        and_(
                            PriceHistory.case_id == case_id,
                            PriceHistory.timestamp >= week_ago
                        )
                    )
                    .order_by(PriceHistory.timestamp.asc())
                    .limit(1)
                )
            else:
                return None
            
            result = await session.execute(stmt)
            price_history = result.scalar_one_or_none()
            
            return price_history.price if price_history else None
    
    async def send_telegram_alert(self, alert: Alert):
        """Отправка алерта через Telegram"""
        if not self.telegram_service:
            self.logger.warning("Telegram не настроен. Алерт: {alert.case_name} - {alert.price_change_percent:.2f}%")
            return
        
        try:
            await self.telegram_service.send_price_alerts([{
                'case_name': alert.case_name,
                'current_price': alert.current_price,
                'previous_price': alert.previous_price,
                'price_change_percent': alert.price_change_percent
            }])
            self.logger.info(f"Telegram алерт отправлен: {alert.case_name}")
        except Exception as e:
            self.logger.error(f"Ошибка отправки Telegram алерта: {e}")
    
    async def send_console_alert(self, alert: Alert):
        """Отправка алерта в консоль"""
        emoji = "📈" if alert.price_change_percent > 0 else "📉"
        self.logger.info(f"{emoji} АЛЕРТ: {alert.case_name} - {alert.price_change_percent:+.2f}% "
                        f"({alert.previous_price:.2f} → {alert.current_price:.2f} руб.)")
    
    async def process_alerts(self):
        """Обработка всех алертов"""
        alerts = await self.check_price_alerts()
        
        if not alerts:
            self.logger.info("Алертов не найдено")
            return
        
        self.logger.info(f"Найдено {len(alerts)} алертов")
        
        for alert in alerts:
            # Отправляем в консоль
            await self.send_console_alert(alert)
            
            # Отправляем через Telegram (если настроено)
            await self.send_telegram_alert(alert)
    
    def configure_telegram(self, bot_token: str, chat_id: str):
        """Настройка Telegram уведомлений"""
        self.telegram_config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id
        )
        self.telegram_service = TelegramNotificationService(self.db_service, self.telegram_config)
        self.logger.info(f"Telegram уведомления настроены для чата: {chat_id}")
    
    async def send_daily_summary(self):
        """Отправка ежедневной сводки"""
        if self.telegram_service:
            await self.telegram_service.send_daily_summary()
    
    async def send_startup_notification(self):
        """Отправка уведомления о запуске"""
        if self.telegram_service:
            await self.telegram_service.send_startup_notification()
    
    async def send_shutdown_notification(self):
        """Отправка уведомления об остановке"""
        if self.telegram_service:
            await self.telegram_service.send_shutdown_notification()
    
    async def test_telegram_connection(self) -> bool:
        """Тест подключения к Telegram"""
        if self.telegram_service:
            return await self.telegram_service.test_connection()
        return False
    
    async def get_alert_history(self, days: int = 7) -> List[Dict]:
        """Получение истории алертов (заглушка - в реальном проекте нужно сохранять в БД)"""
        # В реальном проекте здесь должен быть запрос к таблице с историей алертов
        return []


class AlertScheduler:
    """Планировщик для регулярной проверки алертов"""
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.is_running = False
    
    async def start_monitoring(self, interval_minutes: int = 30):
        """Запуск мониторинга алертов"""
        self.is_running = True
        print(f"Мониторинг алертов запущен (интервал: {interval_minutes} мин)")
        
        while self.is_running:
            try:
                await self.notification_service.process_alerts()
                await asyncio.sleep(interval_minutes * 60)
            except Exception as e:
                print(f"Ошибка в мониторинге алертов: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        print("Мониторинг алертов остановлен")
