#!/usr/bin/env python3
"""
Скрипт для тестирования новых функций CaseParser
"""

import asyncio
import sys
from datetime import datetime

from src.core.cache import CacheManager, CacheService
from src.core.database import DatabaseService
from src.core.migrations import MigrationService
from src.notifications.notifications import NotificationService
from src.services.analytics import AnalyticsService


async def test_database_connection():
    """Тест подключения к базе данных"""
    print("🔍 Тестирование подключения к базе данных...")
    try:
        db_service = DatabaseService()
        await db_service.init_db()
        print("✅ Подключение к базе данных успешно")
        return db_service
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return None


async def test_migrations(db_service):
    """Тест системы миграций"""
    print("\n🔄 Тестирование системы миграций...")
    try:
        migration_service = MigrationService(db_service)
        status = await migration_service.get_migration_status()
        print("📊 Статус миграций:")
        print(f"   Всего миграций: {status['total_migrations']}")
        print(f"   Применено: {status['applied_migrations']}")
        print(f"   Ожидает: {status['pending_migrations']}")
        
        if status['pending_migrations'] > 0:
            print("🔄 Применение непримененных миграций...")
            success = await migration_service.run_migrations()
            if success:
                print("✅ Миграции успешно применены")
            else:
                print("❌ Ошибка применения миграций")
        else:
            print("✅ Все миграции применены")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования миграций: {e}")


async def test_analytics(db_service):
    """Тест аналитических функций"""
    print("\n📈 Тестирование аналитических функций...")
    try:
        analytics_service = AnalyticsService(db_service)
        
        # Тест обзора рынка
        print("   📊 Получение обзора рынка...")
        market_overview = await analytics_service.get_market_overview()
        print(f"   ✅ Обзор рынка: {market_overview['total_cases']} кейсов")
        
        # Тест топ гейнеров
        print("   🚀 Получение топ гейнеров...")
        top_gainers = await analytics_service.get_top_gainers(7, 5)
        print(f"   ✅ Топ гейнеров: {len(top_gainers)} результатов")
        
        # Тест топ лузеров
        print("   📉 Получение топ лузеров...")
        top_losers = await analytics_service.get_top_losers(7, 5)
        print(f"   ✅ Топ лузеров: {len(top_losers)} результатов")
        
        # Тест волатильных кейсов
        print("   ⚡ Получение волатильных кейсов...")
        volatile_cases = await analytics_service.get_most_volatile_cases(30, 5)
        print(f"   ✅ Волатильные кейсы: {len(volatile_cases)} результатов")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования аналитики: {e}")


async def test_notifications(db_service):
    """Тест системы уведомлений"""
    print("\n🔔 Тестирование системы уведомлений...")
    try:
        notification_service = NotificationService(db_service)
        
        # Тест проверки алертов
        print("   🔍 Проверка алертов...")
        alerts = await notification_service.check_price_alerts()
        print(f"   ✅ Найдено алертов: {len(alerts)}")
        
        # Тест консольных уведомлений
        if alerts:
            print("   📢 Отправка консольных уведомлений...")
            for alert in alerts[:3]:  # Показываем только первые 3
                await notification_service.send_console_alert(alert)
        
    except Exception as e:
        print(f"❌ Ошибка тестирования уведомлений: {e}")


async def test_cache():
    """Тест системы кэширования"""
    print("\n⚡ Тестирование системы кэширования...")
    try:
        cache_service = CacheService()
        cache_manager = CacheManager(cache_service)
        
        # Тест базовых операций кэша
        print("   💾 Тест базовых операций кэша...")
        test_data = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
        
        await cache_service.set("test_key", test_data, 60)
        cached_data = await cache_service.get("test_key")
        
        if cached_data and cached_data["test"] == "data":
            print("   ✅ Базовые операции кэша работают")
        else:
            print("   ❌ Ошибка базовых операций кэша")
        
        # Тест статистики кэша
        stats = await cache_service.get_stats()
        print(f"   📊 Статистика кэша: {stats}")
        
        # Очистка тестовых данных
        await cache_service.delete("test_key")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования кэша: {e}")


async def test_api_endpoints():
    """Тест API эндпоинтов"""
    print("\n🌐 Тестирование API эндпоинтов...")
    try:
        import requests
        
        # Тест основного API
        print("   🔍 Проверка основного API...")
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                print("   ✅ Основной API доступен")
            else:
                print(f"   ⚠️ Основной API вернул статус: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Основной API недоступен (сервер не запущен)")
        
        # Тест дашборда
        print("   📊 Проверка дашборда...")
        try:
            response = requests.get("http://localhost:8001/", timeout=5)
            if response.status_code == 200:
                print("   ✅ Дашборд доступен")
            else:
                print(f"   ⚠️ Дашборд вернул статус: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Дашборд недоступен (сервер не запущен)")
            
    except ImportError:
        print("   ⚠️ requests не установлен, пропускаем тест API")
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")


async def main():
    """Основная функция тестирования"""
    print("🧪 Запуск тестирования новых функций CaseParser")
    print("=" * 50)
    
    # Тест подключения к базе данных
    db_service = await test_database_connection()
    if not db_service:
        print("\n❌ Не удалось подключиться к базе данных. Завершение тестирования.")
        sys.exit(1)
    
    # Тест миграций
    await test_migrations(db_service)
    
    # Тест аналитики
    await test_analytics(db_service)
    
    # Тест уведомлений
    await test_notifications(db_service)
    
    # Тест кэширования
    await test_cache()
    
    # Тест API
    await test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")
    print("\n📋 Следующие шаги:")
    print("1. Запустите основное приложение: python main.py")
    print("2. Запустите API сервер: python run_api.py")
    print("3. Запустите дашборд: python run_dashboard.py")
    print("4. Откройте дашборд: http://localhost:8001")
    print("5. Проверьте API документацию: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
