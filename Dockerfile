FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./ 
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y build-essential libffi-dev \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Создаем скрипт для запуска всех сервисов
RUN echo '#!/usr/bin/env python3\n\
import asyncio\n\
import subprocess\n\
import sys\n\
import time\n\
\n\
async def start_api():\n\
    """Запуск API сервера"""\n\
    return subprocess.Popen([\n\
        sys.executable, "-m", "uvicorn", \n\
        "src.api.api:app", \n\
        "--host", "0.0.0.0", \n\
        "--port", "8000"\n\
    ])\n\
\n\
async def start_frontend():\n\
    """Запуск фронтенда"""\n\
    return subprocess.Popen([\n\
        sys.executable, "-m", "uvicorn", \n\
        "src.api.dashboard_app:app", \n\
        "--host", "0.0.0.0", \n\
        "--port", "8001"\n\
    ])\n\
\n\
async def start_main():\n\
    """Запуск основного приложения"""\n\
    return subprocess.Popen([sys.executable, "main.py"])\n\
\n\
async def main():\n\
    """Запуск всех сервисов"""\n\
    print("🚀 Запуск всех сервисов CaseParser...")\n\
    \n\
    # Запускаем все сервисы\n\
    api_process = await start_api()\n\
    frontend_process = await start_frontend()\n\
    main_process = await start_main()\n\
    \n\
    print("✅ Все сервисы запущены!")\n\
    print("🌐 API: http://localhost:8000")\n\
    print("🎨 Frontend: http://localhost:8001")\n\
    \n\
    try:\n\
        # Ждем завершения процессов\n\
        while True:\n\
            time.sleep(1)\n\
    except KeyboardInterrupt:\n\
        print("🛑 Остановка сервисов...")\n\
        for process in [api_process, frontend_process, main_process]:\n\
            if process:\n\
                process.terminate()\n\
\n\
if __name__ == "__main__":\n\
    asyncio.run(main())\n\
' > /app/start_services.py

RUN chmod +x /app/start_services.py

CMD ["python", "start_services.py"]
