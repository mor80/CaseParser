"""
Система миграций для CaseParser
"""

import asyncio
from typing import List, Optional

from sqlalchemy import text

from src.core.database import DatabaseService


class MigrationService:
    """Сервис для управления миграциями базы данных"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.migrations = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Регистрация всех миграций"""
        # Миграция 1: Создание таблицы миграций
        self.migrations.append({
            'version': '001',
            'name': 'create_migrations_table',
            'description': 'Создание таблицы для отслеживания миграций',
            'up': '''
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(10) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''',
            'down': 'DROP TABLE IF EXISTS migrations;'
        })
        
        # Миграция 2: Добавление индексов для оптимизации
        self.migrations.append({
            'version': '002',
            'name': 'add_performance_indexes',
            'description': 'Добавление дополнительных индексов для оптимизации запросов',
            'up': '''
                CREATE INDEX IF NOT EXISTS idx_price_history_case_timestamp_desc 
                ON price_history (case_id, timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_case_statistics_last_updated 
                ON case_statistics (last_updated DESC);
                
                CREATE INDEX IF NOT EXISTS idx_cases_updated_at 
                ON cases (updated_at DESC);
            ''',
            'down': '''
                DROP INDEX IF EXISTS idx_price_history_case_timestamp_desc;
                DROP INDEX IF EXISTS idx_case_statistics_last_updated;
                DROP INDEX IF EXISTS idx_cases_updated_at;
            '''
        })
        
        # Миграция 3: Добавление таблицы алертов
        self.migrations.append({
            'version': '003',
            'name': 'create_alerts_table',
            'description': 'Создание таблицы для хранения истории алертов',
            'up': '''
                CREATE TABLE IF NOT EXISTS alerts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    case_id UUID NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    price_change_percent DECIMAL(10,2) NOT NULL,
                    current_price DECIMAL(10,2) NOT NULL,
                    previous_price DECIMAL(10,2) NOT NULL,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_alerts_case_id ON alerts (case_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at);
                CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts (alert_type);
            ''',
            'down': 'DROP TABLE IF EXISTS alerts;'
        })
        
        # Миграция 4: Добавление таблицы настроек
        self.migrations.append({
            'version': '004',
            'name': 'create_settings_table',
            'description': 'Создание таблицы для хранения настроек системы',
            'up': '''
                CREATE TABLE IF NOT EXISTS settings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    key VARCHAR(255) NOT NULL UNIQUE,
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                INSERT INTO settings (key, value, description) VALUES
                ('alert_threshold_high', '10.0', 'Пороговое значение для высоких алертов (%)'),
                ('alert_threshold_medium', '5.0', 'Пороговое значение для средних алертов (%)'),
                ('alert_threshold_low', '2.0', 'Пороговое значение для низких алертов (%)'),
                ('data_retention_days', '30', 'Количество дней для хранения данных'),
                ('email_notifications', 'false', 'Включить email уведомления'),
                ('dashboard_refresh_interval', '300', 'Интервал обновления дашборда (секунды)')
                ON CONFLICT (key) DO NOTHING;
            ''',
            'down': 'DROP TABLE IF EXISTS settings;'
        })
        
        # Миграция 5: Добавление таблиц портфеля
        self.migrations.append({
            'version': '005',
            'name': 'create_portfolio_tables',
            'description': 'Создание таблиц для управления портфелем',
            'up': '''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    case_id UUID NOT NULL,
                    user_id VARCHAR(255) NOT NULL DEFAULT 'default',
                    quantity NUMERIC(10,2) NOT NULL,
                    purchase_price NUMERIC(10,2) NOT NULL,
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    notes VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS portfolio_statistics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL DEFAULT 'default',
                    total_investment NUMERIC(15,2) NOT NULL DEFAULT 0,
                    current_value NUMERIC(15,2) NOT NULL DEFAULT 0,
                    total_profit NUMERIC(15,2) NOT NULL DEFAULT 0,
                    profit_percentage NUMERIC(5,2) NOT NULL DEFAULT 0,
                    total_cases NUMERIC(10,2) NOT NULL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio (user_id);
                CREATE INDEX IF NOT EXISTS idx_portfolio_case_id ON portfolio (case_id);
                CREATE INDEX IF NOT EXISTS idx_portfolio_purchase_date ON portfolio (purchase_date);
                CREATE INDEX IF NOT EXISTS idx_portfolio_stats_user_id ON portfolio_statistics (user_id);
                CREATE INDEX IF NOT EXISTS idx_portfolio_stats_last_updated ON portfolio_statistics (last_updated);
            ''',
            'down': '''
                DROP TABLE IF EXISTS portfolio_statistics;
                DROP TABLE IF EXISTS portfolio;
            '''
        })

        # Миграция 6: Добавление таблицы пользователей
        self.migrations.append({
            'version': '006',
            'name': 'create_users_table',
            'description': 'Создание таблицы пользователей для аутентификации',
            'up': '''
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) NOT NULL UNIQUE,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    hashed_password VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
            ''',
            'down': '''
                DROP INDEX IF EXISTS idx_users_username;
                DROP INDEX IF EXISTS idx_users_email;
                DROP TABLE IF EXISTS users;
            '''
        })

        # Миграция 7: Добавление внешних ключей для статистики и истории цен
        self.migrations.append({
            'version': '007',
            'name': 'add_case_foreign_keys',
            'description': 'Добавление внешних ключей для таблиц price_history и case_statistics',
            'up': '''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'fk_price_history_case'
                    ) THEN
                        ALTER TABLE price_history
                        ADD CONSTRAINT fk_price_history_case
                        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE;
                    END IF;
                END $$;

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'fk_case_statistics_case'
                    ) THEN
                        ALTER TABLE case_statistics
                        ADD CONSTRAINT fk_case_statistics_case
                        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE;
                    END IF;
                END $$;
            ''',
            'down': '''
                ALTER TABLE price_history DROP CONSTRAINT IF EXISTS fk_price_history_case;
                ALTER TABLE case_statistics DROP CONSTRAINT IF EXISTS fk_case_statistics_case;
            '''
        })
    
    async def get_applied_migrations(self) -> List[str]:
        """Получение списка примененных миграций"""
        async with self.db_service.async_session() as session:
            try:
                result = await session.execute(text("SELECT version FROM migrations ORDER BY version"))
                return [row[0] for row in result.fetchall()]
            except Exception:
                # Если таблица миграций не существует, возвращаем пустой список
                return []
    
    async def apply_migration(self, migration: dict) -> bool:
        """Применение конкретной миграции"""
        async with self.db_service.async_session() as session:
            try:
                # Выполняем миграцию
                await session.execute(text(migration['up']))
                
                # Записываем в таблицу миграций
                await session.execute(text("""
                    INSERT INTO migrations (version, name, description) 
                    VALUES (:version, :name, :description)
                """), {
                    'version': migration['version'],
                    'name': migration['name'],
                    'description': migration['description']
                })
                
                await session.commit()
                print(f"✅ Миграция {migration['version']} ({migration['name']}) применена")
                return True
                
            except Exception as e:
                print(f"❌ Ошибка применения миграции {migration['version']}: {e}")
                await session.rollback()
                return False
    
    async def rollback_migration(self, migration: dict) -> bool:
        """Откат конкретной миграции"""
        async with self.db_service.async_session() as session:
            try:
                # Выполняем откат
                await session.execute(text(migration['down']))
                
                # Удаляем запись из таблицы миграций
                await session.execute(text("""
                    DELETE FROM migrations WHERE version = :version
                """), {'version': migration['version']})
                
                await session.commit()
                print(f"✅ Миграция {migration['version']} ({migration['name']}) откачена")
                return True
                
            except Exception as e:
                print(f"❌ Ошибка отката миграции {migration['version']}: {e}")
                await session.rollback()
                return False
    
    async def run_migrations(self) -> bool:
        """Запуск всех непримененных миграций"""
        print("🔄 Проверка миграций...")
        
        applied_migrations = await self.get_applied_migrations()
        pending_migrations = [
            m for m in self.migrations 
            if m['version'] not in applied_migrations
        ]
        
        if not pending_migrations:
            print("✅ Все миграции применены")
            return True
        
        print(f"📋 Найдено {len(pending_migrations)} непримененных миграций")
        
        success_count = 0
        for migration in pending_migrations:
            if await self.apply_migration(migration):
                success_count += 1
            else:
                print(f"❌ Остановка из-за ошибки в миграции {migration['version']}")
                break
        
        if success_count == len(pending_migrations):
            print(f"✅ Все миграции успешно применены ({success_count}/{len(pending_migrations)})")
            return True
        else:
            print(f"⚠️ Применено {success_count} из {len(pending_migrations)} миграций")
            return False
    
    async def get_migration_status(self) -> dict:
        """Получение статуса миграций"""
        applied_migrations = await self.get_applied_migrations()
        total_migrations = len(self.migrations)
        
        return {
            'total_migrations': total_migrations,
            'applied_migrations': len(applied_migrations),
            'pending_migrations': total_migrations - len(applied_migrations),
            'applied_list': applied_migrations,
            'pending_list': [
                m['version'] for m in self.migrations 
                if m['version'] not in applied_migrations
            ]
        }
    
    async def reset_database(self) -> bool:
        """Полный сброс базы данных (ОСТОРОЖНО!)"""
        print("⚠️ ВНИМАНИЕ: Полный сброс базы данных!")
        print("Это удалит ВСЕ данные. Продолжить? (y/N)")
        
        # В реальном приложении здесь должен быть интерактивный ввод
        # Для автоматизации пропускаем этот шаг
        return False
    
    async def create_backup(self) -> Optional[str]:
        """Создание резервной копии базы данных"""
        try:
            import subprocess
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"caseparser_backup_{timestamp}.sql"
            
            # Команда для создания дампа PostgreSQL
            cmd = [
                'pg_dump',
                '--host=localhost',
                '--port=5432',
                '--username=caseparser',
                '--dbname=caseparser',
                '--file=' + backup_filename,
                '--verbose'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Резервная копия создана: {backup_filename}")
                return backup_filename
            else:
                print(f"❌ Ошибка создания резервной копии: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка создания резервной копии: {e}")
            return None


async def main():
    """Основная функция для управления миграциями"""
    db_service = DatabaseService()
    migration_service = MigrationService(db_service)
    
    # Инициализируем базу данных
    await db_service.init_db()
    
    # Запускаем миграции
    await migration_service.run_migrations()
    
    # Показываем статус
    status = await migration_service.get_migration_status()
    print("\n📊 Статус миграций:")
    print(f"Всего миграций: {status['total_migrations']}")
    print(f"Применено: {status['applied_migrations']}")
    print(f"Ожидает: {status['pending_migrations']}")


if __name__ == "__main__":
    asyncio.run(main())
