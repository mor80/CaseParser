import asyncio
import os
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import UPDATE_PERIOD_MIN
from src.core.database import DatabaseService
from src.notifications.notifications import AlertScheduler, NotificationService
from src.notifications.telegram_bot import TelegramConfig
from src.services.analytics import AnalyticsService
from src.services.portfolio import PortfolioService
from src.services.price_fetcher import PriceFetcher
from src.services.sheet_client import GoogleSheetClient
from src.services.sheet_sync import SheetSyncService

sheet_client = GoogleSheetClient()
price_fetcher = PriceFetcher()
db_service = DatabaseService()
analytics_service = AnalyticsService(db_service)
portfolio_service = PortfolioService(db_service)
sheet_sync_service = SheetSyncService(db_service)

# Настройка Telegram (опционально)
telegram_config = None
if os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
    telegram_config = TelegramConfig(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        chat_id=os.getenv('TELEGRAM_CHAT_ID')
    )

notification_service = NotificationService(db_service, telegram_config)
alert_scheduler = AlertScheduler(notification_service)


def normalize_price_value(price: str) -> Optional[float]:
    """Преобразует строковое значение цены в float."""
    if price is None:
        return None
    if isinstance(price, (int, float)):
        return float(price)

    price_str = str(price).strip()
    if not price_str or price_str.upper() == "N/A":
        return None

    # Удаляем лишние символы и приводим к формату float
    cleaned = (
        price_str.replace("руб.", "")
        .replace("₽", "")
        .replace("\u200e", "")
        .replace("\u00a0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        return float(cleaned)
    except ValueError:
        return None


async def update_prices_job():
    print("Обновление цен…")
    rows = sheet_client.read_rows()
    prices_by_row = await price_fetcher.fetch_prices_in_batches(rows)

    # Сохраняем данные в базу данных
    for row_idx, price in prices_by_row.items():
        row_data = rows[row_idx - 2] if 0 <= (row_idx - 2) < len(rows) else {}
        case_name = str(row_data.get("Name", "")).strip()
        steam_url = row_data.get("Steam URL") or None

        if not case_name:
            print(f"Пропуск строки {row_idx}: не указано имя кейса")
            continue

        try:
            case = await db_service.save_case(case_name, steam_url=steam_url)
        except Exception as exc:
            print(f"Ошибка сохранения кейса {case_name}: {exc}")
            continue

        numeric_price = normalize_price_value(price)
        sheet_price_value = price

        if numeric_price is None:
            fallback_price = normalize_price_value(row_data.get("Price"))
            if fallback_price is not None:
                numeric_price = fallback_price
                sheet_price_value = row_data.get("Price")

        if numeric_price is not None:
            try:
                await db_service.save_price(str(case.id), numeric_price)
                await db_service.update_case_statistics(str(case.id))
                print(f"row {row_idx}: {numeric_price} (saved to DB)")
            except Exception as exc:
                print(f"Error saving price to DB for row {row_idx}: {exc}")
        else:
            print(f"row {row_idx}: price '{price}' пропущена (нет данных)")

        # Обновляем Google Sheets исходным значением
        try:
            value_for_sheet = sheet_price_value if sheet_price_value is not None else ""
            sheet_client.update_price(row_idx, value_for_sheet)
        except Exception as exc:
            print(f"Ошибка обновления Google Sheets в строке {row_idx}: {exc}")
        else:
            print(f"row {row_idx}: {sheet_price_value}")

    print("Готово!")


async def initial_price_parsing():
    """Первоначальный парсинг цен при запуске"""
    print("🚀 Начальный парсинг цен...")
    try:
        # Сначала синхронизируем кейсы из Google Sheets
        print("📋 Синхронизация кейсов из Google Sheets...")
        sync_result = await sheet_sync_service.full_sync()
        if sync_result['success']:
            print(f"✅ Синхронизировано {sync_result['total_synced']} записей")
        else:
            print(f"❌ Ошибка синхронизации: {sync_result}")
        
        # Затем парсим цены
        print("💰 Парсинг цен...")
        await update_prices_job()
        print("✅ Первоначальный парсинг завершен")
    except Exception as e:
        print(f"❌ Ошибка при первоначальном парсинге: {e}")


async def cleanup_old_data_job():
    """Задача для очистки старых данных (старше 30 дней)"""
    print("Очистка старых данных...")
    try:
        deleted_count = await db_service.cleanup_old_data(30)
        print(f"Удалено {deleted_count} старых записей")
    except Exception as e:
        print(f"Ошибка при очистке данных: {e}")


async def update_all_statistics_job():
    """Задача для обновления статистики всех кейсов"""
    print("Обновление статистики...")
    try:
        cases = await db_service.get_all_cases()
        for case in cases:
            await db_service.update_case_statistics(str(case.id))
        print(f"Статистика обновлена для {len(cases)} кейсов")
    except Exception as e:
        print(f"Ошибка при обновлении статистики: {e}")


async def check_alerts_job():
    """Задача для проверки алертов"""
    print("Проверка алертов...")
    try:
        await notification_service.process_alerts()
        print("Проверка алертов завершена")
    except Exception as e:
        print(f"Ошибка при проверке алертов: {e}")


async def sync_google_sheets_job():
    """Задача для синхронизации с Google Sheets"""
    print("Синхронизация с Google Sheets...")
    try:
        result = await sheet_sync_service.full_sync()
        if result['success']:
            print(f"✅ Синхронизация завершена: {result['total_synced']} записей")
        else:
            print(f"❌ Ошибка синхронизации: {result}")
    except Exception as e:
        print(f"Ошибка при синхронизации с Google Sheets: {e}")


async def init_database():
    """Инициализация базы данных"""
    try:
        await db_service.init_db()
        print("База данных инициализирована")
    except Exception as e:
        print(f"Ошибка инициализации базы данных: {e}")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Инициализация базы данных
    loop.run_until_complete(init_database())

    scheduler = AsyncIOScheduler(event_loop=loop)

    # Основная задача обновления цен
    scheduler.add_job(
        update_prices_job,
        trigger="interval",
        minutes=UPDATE_PERIOD_MIN,
        id="update_prices",
    )

    # Задача очистки старых данных (каждые 6 часов)
    scheduler.add_job(
        cleanup_old_data_job, trigger="interval", hours=6, id="cleanup_old_data"
    )

    # Задача обновления статистики (каждые 2 часа)
    scheduler.add_job(
        update_all_statistics_job, trigger="interval", hours=2, id="update_statistics"
    )

    # Задача проверки алертов (каждые 30 минут)
    scheduler.add_job(
        check_alerts_job, trigger="interval", minutes=30, id="check_alerts"
    )
    
    # Задача синхронизации с Google Sheets (каждые 10 минут)
    scheduler.add_job(
        sync_google_sheets_job, trigger="interval", minutes=10, id="sync_sheets"
    )

    scheduler.start()

    # запуск первоначального парсинга
    loop.create_task(initial_price_parsing())

    print(f"Скрипт запущен, обновление каждые {UPDATE_PERIOD_MIN} мин.")
    print("Доступные задачи:")
    print("- Обновление цен: каждые 5 минут")
    print("- Очистка старых данных: каждые 6 часов")
    print("- Обновление статистики: каждые 2 часа")
    print("- Проверка алертов: каждые 30 минут")

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Остановлено пользователем.")


if __name__ == "__main__":
    main()
