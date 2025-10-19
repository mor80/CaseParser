"""
Telegram бот для уведомлений о ценах на кейсы
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp

from src.core.database import DatabaseService


@dataclass
class TelegramConfig:
    """Конфигурация Telegram бота"""
    bot_token: str
    chat_id: str
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True


class TelegramBot:
    """Telegram бот для отправки уведомлений"""
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
    
    async def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """Отправка сообщения в Telegram"""
        if not self.session:
            self.logger.error("Сессия не инициализирована")
            return False
        
        chat_id = chat_id or self.config.chat_id
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": self.config.parse_mode,
                "disable_web_page_preview": self.config.disable_web_page_preview
            }
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    self.logger.info(f"Сообщение отправлено в чат {chat_id}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Ошибка отправки сообщения: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Исключение при отправке сообщения: {e}")
            return False
    
    async def send_alert(self, case_name: str, current_price: float, 
                        previous_price: float, price_change_percent: float) -> bool:
        """Отправка алерта о изменении цены"""
        emoji = "📈" if price_change_percent > 0 else "📉"
        
        message = f"""
{emoji} <b>АЛЕРТ: {case_name}</b>

💰 <b>Цена:</b> {current_price:.2f} руб.
📊 <b>Изменение:</b> {price_change_percent:+.2f}%
🔄 <b>Предыдущая цена:</b> {previous_price:.2f} руб.
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        return await self.send_message(message)
    
    async def send_market_summary(self, summary: Dict) -> bool:
        """Отправка сводки по рынку"""
        sentiment_emoji = {
            'bullish': '📈',
            'bearish': '📉', 
            'neutral': '➡️'
        }.get(summary.get('market_sentiment', 'neutral'), '➡️')
        
        message = f"""
{sentiment_emoji} <b>СВОДКА РЫНКА</b>

📊 <b>Всего кейсов:</b> {summary.get('total_cases', 0)}
💰 <b>Средняя цена:</b> {summary.get('average_price', 0):.2f} руб.
📈 <b>Рост за 24ч:</b> {summary.get('gainers_24h', 0)}
📉 <b>Падение за 24ч:</b> {summary.get('losers_24h', 0)}
🔄 <b>Настроение:</b> {summary.get('market_sentiment', 'unknown')}
        """.strip()
        
        return await self.send_message(message)
    
    async def send_top_movers(self, gainers: List[Dict], losers: List[Dict]) -> bool:
        """Отправка топ гейнеров и лузеров"""
        message = "<b>🏆 ТОП ДВИЖЕНИЯ ЦЕН</b>\n\n"
        
        if gainers:
            message += "<b>📈 ТОП ГЕЙНЕРЫ:</b>\n"
            for i, gainer in enumerate(gainers[:5], 1):
                message += f"{i}. {gainer['name']}: <b>+{gainer['price_change']:.2f}%</b>\n"
            message += "\n"
        
        if losers:
            message += "<b>📉 ТОП ЛУЗЕРЫ:</b>\n"
            for i, loser in enumerate(losers[:5], 1):
                message += f"{i}. {loser['name']}: <b>{loser['price_change']:.2f}%</b>\n"
        
        return await self.send_message(message)
    
    async def send_volatile_cases(self, volatile_cases: List[Dict]) -> bool:
        """Отправка волатильных кейсов"""
        if not volatile_cases:
            return True
        
        message = "<b>⚡ ВОЛАТИЛЬНЫЕ КЕЙСЫ</b>\n\n"
        
        for i, case in enumerate(volatile_cases[:5], 1):
            message += f"{i}. <b>{case['name']}</b>\n"
            message += f"   📊 Волатильность: {case['volatility']:.2f}\n"
            message += f"   💰 Средняя цена: {case['avg_price']:.2f} руб.\n"
            message += f"   📈 Диапазон: {case['min_price']:.2f} - {case['max_price']:.2f} руб.\n\n"
        
        return await self.send_message(message)
    
    async def send_error_notification(self, error_message: str) -> bool:
        """Отправка уведомления об ошибке"""
        message = f"""
🚨 <b>ОШИБКА СИСТЕМЫ</b>

❌ <b>Описание:</b> {error_message}
⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        return await self.send_message(message)
    
    async def send_startup_notification(self) -> bool:
        """Отправка уведомления о запуске системы"""
        message = """
🚀 <b>СИСТЕМА ЗАПУЩЕНА</b>

✅ CaseParser успешно запущен
📊 Мониторинг цен активен
🔔 Уведомления включены
        """.strip()
        
        return await self.send_message(message)
    
    async def send_shutdown_notification(self) -> bool:
        """Отправка уведомления об остановке системы"""
        message = """
🛑 <b>СИСТЕМА ОСТАНОВЛЕНА</b>

❌ CaseParser остановлен
📊 Мониторинг цен приостановлен
        """.strip()
        
        return await self.send_message(message)
    
    async def test_connection(self) -> bool:
        """Тест подключения к Telegram API"""
        if not self.session:
            return False
        
        try:
            url = f"{self.base_url}/getMe"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        bot_info = data.get('result', {})
                        self.logger.info(f"Бот подключен: @{bot_info.get('username', 'unknown')}")
                        return True
                return False
        except Exception as e:
            self.logger.error(f"Ошибка тестирования подключения: {e}")
            return False


class TelegramNotificationService:
    """Сервис уведомлений через Telegram"""
    
    def __init__(self, db_service: DatabaseService, telegram_config: TelegramConfig):
        self.db_service = db_service
        self.telegram_config = telegram_config
        self.logger = logging.getLogger(__name__)
    
    async def send_price_alerts(self, alerts: List[Dict]) -> None:
        """Отправка алертов о ценах"""
        if not alerts:
            return
        
        async with TelegramBot(self.telegram_config) as bot:
            for alert in alerts:
                try:
                    success = await bot.send_alert(
                        case_name=alert['case_name'],
                        current_price=alert['current_price'],
                        previous_price=alert['previous_price'],
                        price_change_percent=alert['price_change_percent']
                    )
                    
                    if success:
                        self.logger.info(f"Алерт отправлен: {alert['case_name']}")
                    else:
                        self.logger.error(f"Ошибка отправки алерта: {alert['case_name']}")
                        
                except Exception as e:
                    self.logger.error(f"Исключение при отправке алерта: {e}")
    
    async def send_daily_summary(self) -> None:
        """Отправка ежедневной сводки"""
        try:
            from src.services.analytics import AnalyticsService
            analytics_service = AnalyticsService(self.db_service)
            
            # Получаем данные для сводки
            market_overview = await analytics_service.get_market_overview()
            top_gainers = await analytics_service.get_top_gainers(1, 5)  # За 24 часа
            top_losers = await analytics_service.get_top_losers(1, 5)
            volatile_cases = await analytics_service.get_most_volatile_cases(7, 5)
            
            async with TelegramBot(self.telegram_config) as bot:
                # Отправляем сводку по рынку
                await bot.send_market_summary(market_overview)
                await asyncio.sleep(1)  # Небольшая пауза между сообщениями
                
                # Отправляем топ движения
                await bot.send_top_movers(top_gainers, top_losers)
                await asyncio.sleep(1)
                
                # Отправляем волатильные кейсы
                await bot.send_volatile_cases(volatile_cases)
                
        except Exception as e:
            self.logger.error(f"Ошибка отправки ежедневной сводки: {e}")
    
    async def send_error_notification(self, error_message: str) -> None:
        """Отправка уведомления об ошибке"""
        async with TelegramBot(self.telegram_config) as bot:
            await bot.send_error_notification(error_message)
    
    async def send_startup_notification(self) -> None:
        """Отправка уведомления о запуске"""
        async with TelegramBot(self.telegram_config) as bot:
            await bot.send_startup_notification()
    
    async def send_shutdown_notification(self) -> None:
        """Отправка уведомления об остановке"""
        async with TelegramBot(self.telegram_config) as bot:
            await bot.send_shutdown_notification()
    
    async def test_connection(self) -> bool:
        """Тест подключения к Telegram"""
        async with TelegramBot(self.telegram_config) as bot:
            return await bot.test_connection()
