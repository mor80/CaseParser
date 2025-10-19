# CaseParser - Мониторинг цен на кейсы CS:GO

Система для автоматического мониторинга цен на кейсы CS:GO с аналитикой, уведомлениями через Telegram и веб-дашбордом.

## Возможности

### Аналитика и статистика
- **Топ гейнеры и лузеры** - кейсы с наибольшим ростом/падением цен
- **Волатильные кейсы** - анализ волатильности цен
- **Обзор рынка** - общая статистика по всем кейсам
- **Анализ трендов** - определение направления движения цен
- **Корреляционный анализ** - связь между ценами разных кейсов

### Уведомления
- **Telegram бот** для отправки уведомлений
- **Автоматические алерты** при значительных изменениях цен
- **Ежедневные сводки** по рынку
- **Настраиваемые пороговые значения** для алертов

### Управление портфелем
- **Добавление кейсов** в портфель с ценой покупки
- **Отслеживание прибыли** в реальном времени
- **Статистика портфеля** с общими показателями
- **История покупок** с детальной информацией

### Веб-интерфейс
- **Интерактивный дашборд** с графиками цен
- **REST API** для интеграции
- **Экспорт данных** в CSV
- **Реальное время** обновления

### Производительность
- **Redis кэширование** для быстрого доступа
- **PostgreSQL** для надежного хранения данных
- **Асинхронная обработка** для высокой производительности
- **Система миграций** для обновления БД

## Быстрый старт

### Запуск через Docker (одна команда!)

1. **Клонирование репозитория**
```bash
git clone <repository-url>
cd CaseParser
```

2. **Настройка переменных окружения**
```bash
cp .env_template .env
# Отредактируйте .env файл с вашими настройками
```

3. **Запуск всех сервисов одной командой**
```bash
docker-compose up -d
```

4. **Проверка работы**
- API: http://localhost:8000
- Фронтенд: http://localhost:8001
- API документация: http://localhost:8000/docs

**Всё! Система запущена и готова к работе.**

### Настройка Telegram уведомлений

1. **Создание бота**
   - Напишите @BotFather в Telegram
   - Создайте нового бота командой `/newbot`
   - Получите токен бота

2. **Получение Chat ID**
   - Напишите боту любое сообщение
   - Перейдите по ссылке: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Найдите `chat.id` в ответе

3. **Настройка в .env**
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Структура проекта

```
CaseParser/
├── src/                    # Исходный код
│   ├── api/               # API эндпоинты
│   ├── core/              # Основные модули (БД, кэш, миграции)
│   ├── models/            # Модели базы данных
│   ├── notifications/     # Система уведомлений
│   ├── services/          # Бизнес-логика
│   └── utils/             # Утилиты
├── tests/                 # Тесты
├── docs/                  # Документация
├── scripts/               # Скрипты
├── docker-compose.yml     # Docker конфигурация
├── requirements.txt       # Python зависимости
└── README.md             # Документация
```

## API Endpoints

### Основные
- `GET /` - Информация о API
- `GET /cases` - Список всех кейсов
- `GET /cases/{case_id}` - Информация о кейсе
- `GET /cases/{case_id}/prices` - История цен
- `GET /cases/{case_id}/statistics` - Статистика кейса

### Аналитика
- `GET /analytics/top-gainers` - Топ гейнеры
- `GET /analytics/top-losers` - Топ лузеры
- `GET /analytics/volatile-cases` - Волатильные кейсы
- `GET /analytics/market-overview` - Обзор рынка
- `GET /analytics/price-trends/{case_id}` - Анализ трендов

### Портфель
- `POST /portfolio/add` - Добавление кейса в портфель
- `GET /portfolio` - Получение портфеля пользователя
- `GET /portfolio/statistics` - Статистика портфеля
- `PUT /portfolio/{id}` - Обновление записи в портфеле
- `DELETE /portfolio/{id}` - Удаление из портфеля

### Синхронизация
- `POST /sync/sheets` - Синхронизация с Google Sheets
- `GET /sync/sheets/status` - Статус подключения к Google Sheets

### Экспорт
- `GET /export/cases/csv` - Экспорт кейсов в CSV
- `GET /export/statistics/csv` - Экспорт статистики в CSV

## Конфигурация

### Переменные окружения (.env)

```env
# Google Sheets
GOOGLE_SHEET_NAME=Your Sheet Name
GOOGLE_CREDS_FILE=path/to/credentials.json

# Steam API
CONCURRENCY=5
STEAM_CURRENCY=5
STEAM_COUNTRY=RU
UPDATE_PERIOD_MIN=5

# База данных
DATABASE_URL=postgresql://caseparser:caseparser123@localhost:5432/caseparser

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram (опционально)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Управление

### Миграции базы данных
```bash
# Применение миграций
python -m src.core.migrations

# Проверка статуса
python -c "
import asyncio
from src.core.migrations import MigrationService
from src.core.database import DatabaseService

async def check():
    db = DatabaseService()
    migration = MigrationService(db)
    status = await migration.get_migration_status()
    print(f'Применено: {status[\"applied_migrations\"]}/{status[\"total_migrations\"]}')

asyncio.run(check())
"
```

### Очистка данных
```bash
# Очистка старых данных (старше 30 дней)
curl -X POST "http://localhost:8000/cleanup?days_to_keep=30"
```

### Мониторинг
```bash
# Проверка статуса сервисов
docker-compose ps

# Просмотр логов
docker-compose logs -f

# Проверка Redis
redis-cli ping

# Проверка PostgreSQL
psql -h localhost -U caseparser -d caseparser -c "SELECT 1;"
```

## Разработка

### Локальная разработка

1. **Установка зависимостей**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

2. **Запуск базы данных**
```bash
docker-compose up -d postgres redis
```

3. **Применение миграций**
```bash
python -m src.core.migrations
```

4. **Запуск приложения**
```bash
python main.py
```

### Тестирование
```bash
# Запуск тестов
python test_features.py

# Проверка API
curl http://localhost:8000/

# Проверка дашборда
curl http://localhost:8001/
```

## Мониторинг и алерты

### Типы алертов
- **Высокая волатильность**: изменение цены ≥ 10%
- **Средняя волатильность**: изменение цены ≥ 5%
- **Низкая волатильность**: изменение цены ≥ 2%

### Telegram уведомления
- Алерты о значительных изменениях цен
- Ежедневные сводки по рынку
- Уведомления об ошибках системы
- Уведомления о запуске/остановке

## Производительность

### Кэширование
- Redis для кэширования аналитических данных
- In-memory fallback если Redis недоступен
- Настраиваемые TTL для разных типов данных

### Оптимизация
- Индексы БД для быстрых запросов
- Батчевая обработка для больших объемов
- Асинхронные операции для параллельной обработки

## Безопасность

- Переменные окружения для чувствительных данных
- Валидация входных данных в API
- Ограничения на размер запросов
- Логирование всех операций

## Логирование

Система ведет логи по следующим событиям:
- Обновление цен
- Применение миграций
- Отправка уведомлений
- Ошибки в работе системы

## Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## Лицензия

MIT License - см. файл LICENSE для деталей.

## Поддержка

При возникновении проблем:
1. Проверьте логи приложения
2. Убедитесь, что все сервисы запущены
3. Проверьте настройки в .env файле
4. Создайте Issue в репозитории

---

**CaseParser** - профессиональный инструмент для мониторинга рынка кейсов CS:GO!