#!/usr/bin/env python3
"""
Скрипт для настройки Telegram бота
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from src.notifications.telegram_bot import TelegramBot, TelegramConfig


async def test_telegram_connection(bot_token: str, chat_id: str):
    """Тест подключения к Telegram"""
    print("🔍 Тестирование подключения к Telegram...")
    
    config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id
    )
    
    async with TelegramBot(config) as bot:
        success = await bot.test_connection()
        
        if success:
            print("✅ Подключение к Telegram успешно")
            return True
        else:
            print("❌ Ошибка подключения к Telegram")
            return False


async def send_test_message(bot_token: str, chat_id: str):
    """Отправка тестового сообщения"""
    print("📤 Отправка тестового сообщения...")
    
    config = TelegramConfig(
        bot_token=bot_token,
        chat_id=chat_id
    )
    
    async with TelegramBot(config) as bot:
        success = await bot.send_message("🤖 Тестовое сообщение от CaseParser бота!")
        
        if success:
            print("✅ Тестовое сообщение отправлено")
            return True
        else:
            print("❌ Ошибка отправки тестового сообщения")
            return False


def update_env_file(bot_token: str, chat_id: str):
    """Обновление .env файла"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ Файл .env не найден. Создайте его из .env_template")
        return False
    
    # Читаем текущий .env файл
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Обновляем или добавляем настройки Telegram
    updated_lines = []
    telegram_token_found = False
    telegram_chat_found = False
    
    for line in lines:
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            updated_lines.append(f'TELEGRAM_BOT_TOKEN={bot_token}\n')
            telegram_token_found = True
        elif line.startswith('TELEGRAM_CHAT_ID='):
            updated_lines.append(f'TELEGRAM_CHAT_ID={chat_id}\n')
            telegram_chat_found = True
        else:
            updated_lines.append(line)
    
    # Добавляем настройки, если их нет
    if not telegram_token_found:
        updated_lines.append(f'TELEGRAM_BOT_TOKEN={bot_token}\n')
    if not telegram_chat_found:
        updated_lines.append(f'TELEGRAM_CHAT_ID={chat_id}\n')
    
    # Записываем обновленный файл
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print("✅ Файл .env обновлен")
    return True


async def main():
    """Основная функция настройки"""
    print("🤖 Настройка Telegram бота для CaseParser")
    print("=" * 50)
    
    # Получаем токен бота
    bot_token = input("Введите токен бота (получите у @BotFather): ").strip()
    if not bot_token:
        print("❌ Токен бота не может быть пустым")
        return
    
    # Получаем Chat ID
    chat_id = input("Введите Chat ID (получите, написав боту): ").strip()
    if not chat_id:
        print("❌ Chat ID не может быть пустым")
        return
    
    # Тестируем подключение
    if not await test_telegram_connection(bot_token, chat_id):
        print("❌ Не удалось подключиться к Telegram. Проверьте токен и Chat ID")
        return
    
    # Отправляем тестовое сообщение
    if not await send_test_message(bot_token, chat_id):
        print("❌ Не удалось отправить тестовое сообщение")
        return
    
    # Обновляем .env файл
    if not update_env_file(bot_token, chat_id):
        print("❌ Не удалось обновить .env файл")
        return
    
    print("\n" + "=" * 50)
    print("✅ Telegram бот успешно настроен!")
    print("\n📋 Следующие шаги:")
    print("1. Перезапустите приложение для применения настроек")
    print("2. Проверьте, что уведомления приходят в Telegram")
    print("3. Настройте пороговые значения алертов при необходимости")


if __name__ == "__main__":
    asyncio.run(main())
