#!/usr/bin/env python3
"""
Скрипт для запуска всех сервисов CaseParser
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(command, description, background=False):
    """Запуск команды с описанием"""
    print(f"🚀 {description}...")
    try:
        if background:
            process = subprocess.Popen(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            return process
        else:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            print(f"✅ {description} - успешно")
            return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка в {description}: {e}")
        return None


def check_docker_services():
    """Проверка запущенных Docker сервисов"""
    print("🔍 Проверка Docker сервисов...")
    
    try:
        # Проверяем PostgreSQL
        result = subprocess.run(
            "docker-compose ps postgres", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        if "Up" in result.stdout:
            print("✅ PostgreSQL запущен")
        else:
            print("⚠️ PostgreSQL не запущен")
            return False
        
        # Проверяем Redis
        result = subprocess.run(
            "docker-compose ps redis", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        if "Up" in result.stdout:
            print("✅ Redis запущен")
        else:
            print("⚠️ Redis не запущен")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки Docker сервисов: {e}")
        return False


def start_docker_services():
    """Запуск Docker сервисов"""
    print("🐳 Запуск Docker сервисов...")
    
    # Запускаем PostgreSQL и Redis
    result = run_command(
        "docker-compose up -d postgres redis",
        "Запуск PostgreSQL и Redis"
    )
    
    if result is None:
        print("❌ Не удалось запустить Docker сервисы")
        return False
    
    # Ждем запуска сервисов
    print("⏳ Ожидание запуска сервисов...")
    time.sleep(10)
    
    return check_docker_services()


def run_migrations():
    """Запуск миграций"""
    print("🔄 Применение миграций...")
    
    result = run_command(
        "python -m src.core.migrations",
        "Применение миграций базы данных"
    )
    
    return result is not None


def start_main_app():
    """Запуск основного приложения"""
    print("📊 Запуск основного приложения...")
    
    process = run_command(
        "python main.py",
        "Основное приложение (парсинг цен)",
        background=True
    )
    
    return process


def start_api_server():
    """Запуск API сервера"""
    print("🌐 Запуск API сервера...")
    
    process = run_command(
        "python run_api.py",
        "API сервер",
        background=True
    )
    
    return process


def start_dashboard():
    """Запуск дашборда"""
    print("📈 Запуск дашборда...")
    
    process = run_command(
        "python run_dashboard.py",
        "Веб-дашборд",
        background=True
    )
    
    return process

def start_frontend():
    """Запуск фронтенда"""
    print("🎨 Запуск фронтенда...")
    
    process = run_command(
        "python run_frontend.py",
        "Фронтенд",
        background=True
    )
    
    return process


def main():
    """Основная функция"""
    print("🚀 Запуск всех сервисов CaseParser")
    print("=" * 50)
    
    # Проверяем, что мы в правильной директории
    if not Path("main.py").exists():
        print("❌ Файл main.py не найден. Запустите скрипт из корневой директории проекта.")
        sys.exit(1)
    
    # Проверяем Docker
    try:
        subprocess.run("docker --version", shell=True, check=True, capture_output=True)
        print("✅ Docker доступен")
    except subprocess.CalledProcessError:
        print("❌ Docker не установлен или недоступен")
        sys.exit(1)
    
    # Проверяем docker-compose
    try:
        subprocess.run("docker-compose --version", shell=True, check=True, capture_output=True)
        print("✅ Docker Compose доступен")
    except subprocess.CalledProcessError:
        print("❌ Docker Compose не установлен или недоступен")
        sys.exit(1)
    
    # Запускаем Docker сервисы
    if not start_docker_services():
        print("❌ Не удалось запустить Docker сервисы")
        sys.exit(1)
    
    # Применяем миграции
    if not run_migrations():
        print("❌ Не удалось применить миграции")
        sys.exit(1)
    
    # Запускаем приложения
    processes = []
    
    # Основное приложение
    main_process = start_main_app()
    if main_process:
        processes.append(("Основное приложение", main_process))
    
    # API сервер
    api_process = start_api_server()
    if api_process:
        processes.append(("API сервер", api_process))
    
    # Дашборд
    dashboard_process = start_dashboard()
    if dashboard_process:
        processes.append(("Дашборд", dashboard_process))
    
    # Фронтенд
    frontend_process = start_frontend()
    if frontend_process:
        processes.append(("Фронтенд", frontend_process))
    
    print("\n" + "=" * 50)
    print("✅ Все сервисы запущены!")
    print("\n📋 Доступные сервисы:")
    print("🌐 API сервер: http://localhost:8000")
    print("📊 Дашборд: http://localhost:8001")
    print("🎨 Фронтенд: http://localhost:8001")
    print("📚 API документация: http://localhost:8000/docs")
    print("\n⏳ Ожидание запуска сервисов...")
    time.sleep(5)
    
    print("\n🔍 Проверка доступности сервисов...")
    
    # Проверяем API
    try:
        import requests
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ API сервер доступен")
        else:
            print(f"⚠️ API сервер вернул статус: {response.status_code}")
    except Exception as e:
        print(f"⚠️ API сервер недоступен: {e}")
    
    # Проверяем дашборд
    try:
        response = requests.get("http://localhost:8001/", timeout=5)
        if response.status_code == 200:
            print("✅ Дашборд доступен")
        else:
            print(f"⚠️ Дашборд вернул статус: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Дашборд недоступен: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 CaseParser успешно запущен!")
    print("\n📖 Полезные команды:")
    print("• Просмотр логов: docker-compose logs -f")
    print("• Остановка сервисов: docker-compose down")
    print("• Тестирование функций: python test_features.py")
    print("\n⚠️ Для остановки нажмите Ctrl+C")
    
    try:
        # Ждем завершения процессов
        while True:
            time.sleep(1)
            # Проверяем, что процессы еще работают
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️ {name} завершился неожиданно")
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервисов...")
        
        # Останавливаем процессы
        for name, process in processes:
            try:
                process.terminate()
                print(f"✅ {name} остановлен")
            except Exception as e:
                print(f"❌ Ошибка остановки {name}: {e}")
        
        print("👋 До свидания!")


if __name__ == "__main__":
    main()
