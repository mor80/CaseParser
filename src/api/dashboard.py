from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.core.database import DatabaseService
from src.services.analytics import AnalyticsService


class DashboardService:
    """Сервис для создания дашборда с аналитикой"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.analytics_service = AnalyticsService(db_service)
    
    async def get_dashboard_data(self) -> Dict:
        """Получение данных для дашборда"""
        # Обзор рынка
        market_overview = await self.analytics_service.get_market_overview()
        
        # Топ гейнеры и лузеры
        top_gainers = await self.analytics_service.get_top_gainers(7, 5)
        top_losers = await self.analytics_service.get_top_losers(7, 5)
        
        # Волатильные кейсы
        volatile_cases = await self.analytics_service.get_most_volatile_cases(30, 5)
        
        # Последние цены
        latest_prices = await self.db_service.get_latest_prices()
        
        return {
            'market_overview': market_overview,
            'top_gainers': top_gainers,
            'top_losers': top_losers,
            'volatile_cases': volatile_cases,
            'latest_prices': latest_prices,
            'last_update': datetime.utcnow().isoformat()
        }
    
    async def get_case_chart_data(self, case_id: str, days: int = 30) -> Dict:
        """Получение данных для графика конкретного кейса"""
        price_history = await self.db_service.get_price_history(case_id, days)
        
        if not price_history:
            return {'error': 'Данные не найдены'}
        
        # Подготавливаем данные для Chart.js
        labels = [p.timestamp.strftime('%Y-%m-%d %H:%M') for p in price_history]
        prices = [float(p.price) for p in price_history]
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Цена (руб.)',
                'data': prices,
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'tension': 0.1
            }]
        }


# HTML шаблон для дашборда
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CaseParser Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h3 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .stat-item:last-child {
            border-bottom: none;
        }
        .positive {
            color: #28a745;
            font-weight: bold;
        }
        .negative {
            color: #dc3545;
            font-weight: bold;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .refresh-btn:hover {
            background: #5a6fd8;
        }
        .loading {
            text-align: center;
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 CaseParser Dashboard</h1>
            <p>Мониторинг цен на кейсы CS:GO</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Обновить данные</button>
        </div>
        
        <div class="grid">
            <!-- Обзор рынка -->
            <div class="card">
                <h3>📈 Обзор рынка</h3>
                <div id="market-overview">
                    <div class="loading">Загрузка...</div>
                </div>
            </div>
            
            <!-- Топ гейнеры -->
            <div class="card">
                <h3>🚀 Топ гейнеры (7 дней)</h3>
                <div id="top-gainers">
                    <div class="loading">Загрузка...</div>
                </div>
            </div>
            
            <!-- Топ лузеры -->
            <div class="card">
                <h3>📉 Топ лузеры (7 дней)</h3>
                <div id="top-losers">
                    <div class="loading">Загрузка...</div>
                </div>
            </div>
            
            <!-- Волатильные кейсы -->
            <div class="card">
                <h3>⚡ Волатильные кейсы</h3>
                <div id="volatile-cases">
                    <div class="loading">Загрузка...</div>
                </div>
            </div>
        </div>
        
        <!-- График цен -->
        <div class="card">
            <h3>📊 График цен</h3>
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        let priceChart = null;
        
        async function loadDashboardData() {
            try {
                const response = await fetch('/dashboard/api/data');
                const data = await response.json();
                
                updateMarketOverview(data.market_overview);
                updateTopGainers(data.top_gainers);
                updateTopLosers(data.top_losers);
                updateVolatileCases(data.volatile_cases);
                
            } catch (error) {
                console.error('Ошибка загрузки данных:', error);
            }
        }
        
        function updateMarketOverview(overview) {
            const container = document.getElementById('market-overview');
            container.innerHTML = `
                <div class="stat-item">
                    <span>Всего кейсов:</span>
                    <span>${overview.total_cases}</span>
                </div>
                <div class="stat-item">
                    <span>Средняя цена:</span>
                    <span>${overview.average_price.toFixed(2)} руб.</span>
                </div>
                <div class="stat-item">
                    <span>Рост за 24ч:</span>
                    <span class="positive">${overview.gainers_24h}</span>
                </div>
                <div class="stat-item">
                    <span>Падение за 24ч:</span>
                    <span class="negative">${overview.losers_24h}</span>
                </div>
                <div class="stat-item">
                    <span>Настроение рынка:</span>
                    <span class="${overview.market_sentiment === 'bullish' ? 'positive' : overview.market_sentiment === 'bearish' ? 'negative' : ''}">
                        ${overview.market_sentiment === 'bullish' ? '📈 Бычий' : overview.market_sentiment === 'bearish' ? '📉 Медвежий' : '➡️ Нейтральный'}
                    </span>
                </div>
            `;
        }
        
        function updateTopGainers(gainers) {
            const container = document.getElementById('top-gainers');
            container.innerHTML = gainers.map(gainer => `
                <div class="stat-item">
                    <span>${gainer.name}</span>
                    <span class="positive">+${gainer.price_change.toFixed(2)}%</span>
                </div>
            `).join('');
        }
        
        function updateTopLosers(losers) {
            const container = document.getElementById('top-losers');
            container.innerHTML = losers.map(loser => `
                <div class="stat-item">
                    <span>${loser.name}</span>
                    <span class="negative">${loser.price_change.toFixed(2)}%</span>
                </div>
            `).join('');
        }
        
        function updateVolatileCases(volatile) {
            const container = document.getElementById('volatile-cases');
            container.innerHTML = volatile.map(vol => `
                <div class="stat-item">
                    <span>${vol.name}</span>
                    <span>Волатильность: ${vol.volatility.toFixed(2)}</span>
                </div>
            `).join('');
        }
        
        async function loadCaseChart(caseId) {
            try {
                const response = await fetch(`/dashboard/api/chart/${caseId}?days=30`);
                const data = await response.json();
                
                if (data.error) {
                    console.error('Ошибка загрузки графика:', data.error);
                    return;
                }
                
                if (priceChart) {
                    priceChart.destroy();
                }
                
                const ctx = document.getElementById('priceChart').getContext('2d');
                priceChart = new Chart(ctx, {
                    type: 'line',
                    data: data,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: false,
                                title: {
                                    display: true,
                                    text: 'Цена (руб.)'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Время'
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true
                            }
                        }
                    }
                });
                
            } catch (error) {
                console.error('Ошибка загрузки графика:', error);
            }
        }
        
        function refreshData() {
            loadDashboardData();
        }
        
        // Загружаем данные при загрузке страницы
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboardData();
            
            // Обновляем данные каждые 5 минут
            setInterval(loadDashboardData, 300000);
        });
    </script>
</body>
</html>
"""


def create_dashboard_app(db_service: DatabaseService) -> FastAPI:
    """Создание FastAPI приложения для дашборда"""
    app = FastAPI(title="CaseParser Dashboard")
    dashboard_service = DashboardService(db_service)
    
    # Подключение статических файлов
    frontend_path = Path(__file__).parent.parent.parent / "frontend"
    static_path = frontend_path / "static"
    
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        """Главная страница дашборда"""
        # Читаем HTML из файла
        template_path = frontend_path / "templates" / "index.html"
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        else:
            return DASHBOARD_HTML
    
    @app.get("/api/data")
    async def get_dashboard_data():
        """API для получения данных дашборда"""
        return await dashboard_service.get_dashboard_data()
    
    @app.get("/api/chart/{case_id}")
    async def get_case_chart(case_id: str, days: int = 30):
        """API для получения данных графика кейса"""
        return await dashboard_service.get_case_chart_data(case_id, days)
    
    return app
