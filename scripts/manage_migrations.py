#!/usr/bin/env python3
"""
Скрипт для управления миграциями базы данных
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from src.core.database import DatabaseService
from src.core.migrations import MigrationService


async def show_status():
    """Показать статус миграций"""
    print("📊 Статус миграций")
    print("-" * 30)
    
    db_service = DatabaseService()
    migration_service = MigrationService(db_service)
    
    try:
        status = await migration_service.get_migration_status()
        
        print(f"Всего миграций: {status['total_migrations']}")
        print(f"Применено: {status['applied_migrations']}")
        print(f"Ожидает: {status['pending_migrations']}")
        
        if status['applied_list']:
            print("\n✅ Примененные миграции:")
            for version in status['applied_list']:
                print(f"  - {version}")
        
        if status['pending_list']:
            print("\n⏳ Ожидающие миграции:")
            for version in status['pending_list']:
                print(f"  - {version}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")
        return False


async def apply_migrations():
    """Применить все непримененные миграции"""
    print("🔄 Применение миграций")
    print("-" * 30)
    
    db_service = DatabaseService()
    migration_service = MigrationService(db_service)
    
    try:
        success = await migration_service.run_migrations()
        
        if success:
            print("✅ Все миграции успешно применены")
        else:
            print("❌ Ошибка применения миграций")
        
        return success
        
    except Exception as e:
        print(f"❌ Ошибка применения миграций: {e}")
        return False


async def create_backup():
    """Создать резервную копию базы данных"""
    print("💾 Создание резервной копии")
    print("-" * 30)
    
    db_service = DatabaseService()
    migration_service = MigrationService(db_service)
    
    try:
        backup_file = await migration_service.create_backup()
        
        if backup_file:
            print(f"✅ Резервная копия создана: {backup_file}")
        else:
            print("❌ Ошибка создания резервной копии")
        
        return backup_file is not None
        
    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {e}")
        return False


async def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python manage_migrations.py <команда>")
        print("\nДоступные команды:")
        print("  status    - Показать статус миграций")
        print("  apply     - Применить миграции")
        print("  backup    - Создать резервную копию")
        print("  all       - Показать статус, применить миграции и создать резервную копию")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        await show_status()
    elif command == "apply":
        await apply_migrations()
    elif command == "backup":
        await create_backup()
    elif command == "all":
        print("🚀 Полная проверка и обновление")
        print("=" * 50)
        
        # Показываем статус
        await show_status()
        print()
        
        # Применяем миграции
        await apply_migrations()
        print()
        
        # Создаем резервную копию
        await create_backup()
        
        print("\n✅ Операция завершена")
    else:
        print(f"❌ Неизвестная команда: {command}")


if __name__ == "__main__":
    asyncio.run(main())
