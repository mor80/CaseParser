from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select

from src.core.database import DatabaseService
from src.models.models import Case
from src.models.user import User
from src.services.analytics import AnalyticsService
from src.services.auth import AuthService
from src.services.portfolio import PortfolioService
from src.services.sheet_sync import SheetSyncService
from config import API_ALLOWED_ORIGINS

app = FastAPI(title="CaseParser API", version="1.0.0")
db_service = DatabaseService()
analytics_service = AnalyticsService(db_service)
auth_service = AuthService(db_service)
portfolio_service = PortfolioService(db_service)
sheet_sync_service = SheetSyncService(db_service)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# CORS
allow_origins = ["*"] if API_ALLOWED_ORIGINS == ["*"] else API_ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.options("/{full_path:path}")
async def preflight_handler(full_path: str) -> Response:
    """Явная обработка CORS preflight-запросов (OPTIONS)."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    user = await auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )
    return user


class CaseResponse(BaseModel):
    id: str
    name: str
    steam_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class PriceHistoryResponse(BaseModel):
    id: str
    case_id: str
    price: float
    currency: str
    timestamp: datetime


class CaseStatisticsResponse(BaseModel):
    id: str
    case_id: str
    current_price: Optional[float]
    min_price_30d: Optional[float]
    max_price_30d: Optional[float]
    avg_price_30d: Optional[float]
    price_change_24h: Optional[float]
    price_change_7d: Optional[float]
    price_change_30d: Optional[float]
    last_updated: datetime


class CaseWithLatestPrice(BaseModel):
    case: CaseResponse
    latest_price: Optional[PriceHistoryResponse]
    statistics: Optional[CaseStatisticsResponse]


class SimpleCaseResponse(BaseModel):
    id: str
    name: str
    steam_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    latest_price: Optional[float]
    latest_price_timestamp: Optional[datetime]
    price_change_24h: Optional[float] = None
    price_change_7d: Optional[float] = None
    price_change_30d: Optional[float] = None
    min_price_30d: Optional[float] = None
    max_price_30d: Optional[float] = None
    avg_price_30d: Optional[float] = None


class TopGainerResponse(BaseModel):
    case_id: str
    name: str
    current_price: float
    price_change: float
    last_updated: datetime


class TopLoserResponse(BaseModel):
    case_id: str
    name: str
    current_price: float
    price_change: float
    last_updated: datetime


class VolatileCaseResponse(BaseModel):
    case_id: str
    name: str
    volatility: float
    avg_price: float
    min_price: float
    max_price: float
    price_range: float


class MarketOverviewResponse(BaseModel):
    total_cases: int
    cases_with_statistics: int
    average_price: float
    gainers_24h: int
    losers_24h: int
    last_update: Optional[datetime]
    market_sentiment: str


class PriceTrendResponse(BaseModel):
    trend: str
    trend_strength: float
    volatility: float
    price_range: dict
    data_points: int


class CorrelationResponse(BaseModel):
    correlation: float
    common_dates: int
    interpretation: str


# ========== МОДЕЛИ ПОРТФЕЛЯ ==========

class PortfolioEntryRequest(BaseModel):
    case_id: str
    quantity: float
    purchase_price: float
    notes: Optional[str] = None


class PortfolioEntryResponse(BaseModel):
    id: str
    case_id: str
    case_name: str
    quantity: float
    purchase_price: float
    purchase_date: datetime
    current_price: Optional[float]
    current_price_timestamp: Optional[datetime]
    total_investment: float
    current_value: float
    profit: float
    profit_percentage: float
    notes: Optional[str]


class PortfolioStatisticsResponse(BaseModel):
    total_investment: float
    current_value: float
    total_profit: float
    profit_percentage: float
    total_cases: float
    last_updated: datetime


class SheetSyncResponse(BaseModel):
    success: bool
    message: str
    synced_count: int
    errors: List[str] = []


class PortfolioUpdateRequest(BaseModel):
    quantity: Optional[float] = None
    purchase_price: Optional[float] = None
    notes: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime
    updated_at: datetime


class AuthRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(AuthRequest):
    username: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@app.on_event("startup")
async def startup_event():
    """Инициализация базы данных при запуске"""
    await db_service.init_db()


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"message": "CaseParser API", "version": "1.0.0"}


@app.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest):
    """Регистрация нового пользователя"""
    try:
        user = await auth_service.register_user(
            email=payload.email,
            password=payload.password,
            username=payload.username
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    token = auth_service.create_access_token(user_id=str(user.id))
    return AuthResponse(access_token=token, user=user_to_response(user))


@app.post("/auth/login", response_model=AuthResponse)
async def login_user(payload: AuthRequest):
    """Аутентификация пользователя"""
    user = await auth_service.authenticate_user(
        email=payload.email,
        password=payload.password
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    token = auth_service.create_access_token(user_id=str(user.id))
    return AuthResponse(access_token=token, user=user_to_response(user))


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return user_to_response(current_user)


@app.get("/cases", response_model=List[SimpleCaseResponse])
async def get_all_cases():
    """Получение всех кейсов с последними ценами"""
    cases = await db_service.get_all_cases()
    
    if not cases:
        return []

    case_ids = [str(case.id) for case in cases]
    latest_prices = await db_service.get_latest_prices_for_cases(case_ids)
    statistics = await db_service.get_all_statistics()
    statistics_map = {str(stat.case_id): stat for stat in statistics}

    case_data = []
    
    for case in cases:
        # Получаем последнюю цену для кейса
        latest_price = latest_prices.get(str(case.id))
        stats = statistics_map.get(str(case.id))
        
        case_data.append(SimpleCaseResponse(
            id=str(case.id),
            name=case.name,
            steam_url=case.steam_url,
            created_at=case.created_at,
            updated_at=case.updated_at,
            latest_price=float(latest_price.price) if latest_price else None,
            latest_price_timestamp=latest_price.timestamp if latest_price else None,
            price_change_24h=float(stats.price_change_24h) if stats and stats.price_change_24h is not None else None,
            price_change_7d=float(stats.price_change_7d) if stats and stats.price_change_7d is not None else None,
            price_change_30d=float(stats.price_change_30d) if stats and stats.price_change_30d is not None else None,
            min_price_30d=float(stats.min_price_30d) if stats and stats.min_price_30d is not None else None,
            max_price_30d=float(stats.max_price_30d) if stats and stats.max_price_30d is not None else None,
            avg_price_30d=float(stats.avg_price_30d) if stats and stats.avg_price_30d is not None else None
        ))
    
    return case_data


@app.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str):
    """Получение конкретного кейса по ID"""
    async with db_service.async_session() as session:
        stmt = select(Case).where(Case.id == case_id)
        result = await session.execute(stmt)
        case = result.scalar_one_or_none()
        
        if case is None:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return CaseResponse(
            id=str(case.id),
            name=case.name,
            steam_url=case.steam_url,
            created_at=case.created_at,
            updated_at=case.updated_at
        )


@app.get("/cases/{case_id}/detail", response_model=CaseWithLatestPrice)
async def get_case_detail(case_id: str):
    """Получение детальной информации о кейсе"""
    async with db_service.async_session() as session:
        stmt = select(Case).where(Case.id == case_id)
        result = await session.execute(stmt)
        case = result.scalar_one_or_none()

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    latest_price = await db_service.get_latest_price_for_case(case_id)
    statistics = await db_service.get_case_statistics(case_id)

    case_response = CaseResponse(
        id=str(case.id),
        name=case.name,
        steam_url=case.steam_url,
        created_at=case.created_at,
        updated_at=case.updated_at
    )

    price_response = None
    if latest_price:
        price_response = PriceHistoryResponse(
            id=str(latest_price.id),
            case_id=str(latest_price.case_id),
            price=latest_price.price,
            currency=latest_price.currency,
            timestamp=latest_price.timestamp
        )

    statistics_response = None
    if statistics:
        statistics_response = CaseStatisticsResponse(
            id=str(statistics.id),
            case_id=str(statistics.case_id),
            current_price=statistics.current_price,
            min_price_30d=statistics.min_price_30d,
            max_price_30d=statistics.max_price_30d,
            avg_price_30d=statistics.avg_price_30d,
            price_change_24h=statistics.price_change_24h,
            price_change_7d=statistics.price_change_7d,
            price_change_30d=statistics.price_change_30d,
            last_updated=statistics.last_updated
        )

    return CaseWithLatestPrice(
        case=case_response,
        latest_price=price_response,
        statistics=statistics_response
    )


@app.get("/cases/{case_id}/prices", response_model=List[PriceHistoryResponse])
async def get_case_price_history(
    case_id: str,
    days: int = Query(30, ge=1, le=365, description="Количество дней для получения истории")
):
    """Получение истории цен для конкретного кейса"""
    price_history = await db_service.get_price_history(case_id, days)
    return [PriceHistoryResponse(
        id=str(price.id),
        case_id=str(price.case_id),
        price=price.price,
        currency=price.currency,
        timestamp=price.timestamp
    ) for price in price_history]


@app.get("/cases/{case_id}/statistics", response_model=CaseStatisticsResponse)
async def get_case_statistics(case_id: str):
    """Получение статистики для конкретного кейса"""
    statistics = await db_service.get_case_statistics(case_id)
    
    if statistics is None:
        raise HTTPException(status_code=404, detail="Statistics not found for this case")
    
    return CaseStatisticsResponse(
        id=str(statistics.id),
        case_id=str(statistics.case_id),
        current_price=statistics.current_price,
        min_price_30d=statistics.min_price_30d,
        max_price_30d=statistics.max_price_30d,
        avg_price_30d=statistics.avg_price_30d,
        price_change_24h=statistics.price_change_24h,
        price_change_7d=statistics.price_change_7d,
        price_change_30d=statistics.price_change_30d,
        last_updated=statistics.last_updated
    )


@app.get("/cases/with-prices", response_model=List[CaseWithLatestPrice])
async def get_cases_with_latest_prices():
    """Получение всех кейсов с их последними ценами"""
    cases_with_prices = await db_service.get_latest_prices()
    
    result = []
    for case, price_history in cases_with_prices:
        # Получаем статистику для кейса
        statistics = await db_service.get_case_statistics(str(case.id))
        
        case_response = CaseResponse(
            id=str(case.id),
            name=case.name,
            steam_url=case.steam_url,
            created_at=case.created_at,
            updated_at=case.updated_at
        )
        
        price_response = PriceHistoryResponse(
            id=str(price_history.id),
            case_id=str(price_history.case_id),
            price=price_history.price,
            currency=price_history.currency,
            timestamp=price_history.timestamp
        )
        
        statistics_response = None
        if statistics:
            statistics_response = CaseStatisticsResponse(
                id=str(statistics.id),
                case_id=str(statistics.case_id),
                current_price=statistics.current_price,
                min_price_30d=statistics.min_price_30d,
                max_price_30d=statistics.max_price_30d,
                avg_price_30d=statistics.avg_price_30d,
                price_change_24h=statistics.price_change_24h,
                price_change_7d=statistics.price_change_7d,
                price_change_30d=statistics.price_change_30d,
                last_updated=statistics.last_updated
            )
        
        result.append(CaseWithLatestPrice(
            case=case_response,
            latest_price=price_response,
            statistics=statistics_response
        ))
    
    return result


@app.get("/statistics", response_model=List[CaseStatisticsResponse])
async def get_all_statistics():
    """Получение статистики всех кейсов"""
    statistics = await db_service.get_all_statistics()
    return [CaseStatisticsResponse(
        id=str(stat.id),
        case_id=str(stat.case_id),
        current_price=stat.current_price,
        min_price_30d=stat.min_price_30d,
        max_price_30d=stat.max_price_30d,
        avg_price_30d=stat.avg_price_30d,
        price_change_24h=stat.price_change_24h,
        price_change_7d=stat.price_change_7d,
        price_change_30d=stat.price_change_30d,
        last_updated=stat.last_updated
    ) for stat in statistics]


@app.post("/cases/{case_id}/update-statistics")
async def update_case_statistics(case_id: str):
    """Обновление статистики для конкретного кейса"""
    await db_service.update_case_statistics(case_id)
    return {"message": "Statistics updated successfully"}


@app.post("/cleanup")
async def cleanup_old_data(
    days_to_keep: int = Query(30, ge=1, le=365, description="Количество дней для сохранения данных")
):
    """Очистка старых данных"""
    deleted_count = await db_service.cleanup_old_data(days_to_keep)
    return {"message": f"Deleted {deleted_count} old price records"}


# ========== АНАЛИТИЧЕСКИЕ ЭНДПОИНТЫ ==========

@app.get("/analytics/top-gainers", response_model=List[TopGainerResponse])
async def get_top_gainers(
    days: int = Query(7, ge=1, le=30, description="Период для анализа"),
    limit: int = Query(10, ge=1, le=50, description="Количество результатов")
):
    """Получение кейсов с наибольшим ростом цены"""
    gainers = await analytics_service.get_top_gainers(days, limit)
    return [TopGainerResponse(**gainer) for gainer in gainers]


@app.get("/analytics/top-losers", response_model=List[TopLoserResponse])
async def get_top_losers(
    days: int = Query(7, ge=1, le=30, description="Период для анализа"),
    limit: int = Query(10, ge=1, le=50, description="Количество результатов")
):
    """Получение кейсов с наибольшим падением цены"""
    losers = await analytics_service.get_top_losers(days, limit)
    return [TopLoserResponse(**loser) for loser in losers]


@app.get("/analytics/volatile-cases", response_model=List[VolatileCaseResponse])
async def get_volatile_cases(
    days: int = Query(30, ge=7, le=90, description="Период для анализа"),
    limit: int = Query(10, ge=1, le=50, description="Количество результатов")
):
    """Получение наиболее волатильных кейсов"""
    volatile_cases = await analytics_service.get_most_volatile_cases(days, limit)
    return [VolatileCaseResponse(**case) for case in volatile_cases]


@app.get("/analytics/market-overview", response_model=MarketOverviewResponse)
async def get_market_overview():
    """Получение общего обзора рынка"""
    overview = await analytics_service.get_market_overview()
    return MarketOverviewResponse(**overview)


@app.get("/analytics/price-trends/{case_id}", response_model=PriceTrendResponse)
async def get_price_trends(
    case_id: str,
    days: int = Query(30, ge=7, le=90, description="Период для анализа тренда")
):
    """Анализ трендов цены для конкретного кейса"""
    trends = await analytics_service.get_price_trends(case_id, days)
    return PriceTrendResponse(**trends)


@app.get("/analytics/correlation", response_model=CorrelationResponse)
async def get_correlation_analysis(
    case_id_1: str = Query(..., description="ID первого кейса"),
    case_id_2: str = Query(..., description="ID второго кейса"),
    days: int = Query(30, ge=7, le=90, description="Период для анализа корреляции")
):
    """Анализ корреляции между двумя кейсами"""
    correlation = await analytics_service.get_correlation_analysis(case_id_1, case_id_2, days)
    return CorrelationResponse(**correlation)


# ========== ЭКСПОРТ ДАННЫХ ==========

@app.get("/export/cases/csv")
async def export_cases_csv():
    """Экспорт всех кейсов в CSV формате"""
    import csv
    import io
    
    cases = await db_service.get_all_cases()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(['ID', 'Name', 'Steam URL', 'Created At', 'Updated At'])
    
    # Данные
    for case in cases:
        writer.writerow([
            str(case.id),
            case.name,
            case.steam_url or '',
            case.created_at.isoformat(),
            case.updated_at.isoformat()
        ])
    
    from fastapi.responses import StreamingResponse
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cases.csv"}
    )


@app.get("/export/statistics/csv")
async def export_statistics_csv():
    """Экспорт статистики всех кейсов в CSV формате"""
    import csv
    import io
    
    statistics = await db_service.get_all_statistics()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        'Case ID', 'Current Price', 'Min Price 30d', 'Max Price 30d', 
        'Avg Price 30d', 'Price Change 24h', 'Price Change 7d', 
        'Price Change 30d', 'Last Updated'
    ])
    
    # Данные
    for stat in statistics:
        writer.writerow([
            str(stat.case_id),
            stat.current_price or '',
            stat.min_price_30d or '',
            stat.max_price_30d or '',
            stat.avg_price_30d or '',
            stat.price_change_24h or '',
            stat.price_change_7d or '',
            stat.price_change_30d or '',
            stat.last_updated.isoformat()
        ])
    
    from fastapi.responses import StreamingResponse
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=statistics.csv"}
    )


# ========== ЭНДПОИНТЫ ПОРТФЕЛЯ ==========

@app.post("/portfolio/add", response_model=PortfolioEntryResponse)
async def add_to_portfolio(entry: PortfolioEntryRequest, current_user: User = Depends(get_current_user)):
    """Добавление кейса в портфель"""
    try:
        portfolio_entry = await portfolio_service.add_to_portfolio(
            case_id=entry.case_id,
            quantity=entry.quantity,
            purchase_price=entry.purchase_price,
            user_id=str(current_user.id),
            notes=entry.notes
        )
        
        # Получаем обновленную информацию о портфеле
        portfolio_data = await portfolio_service.get_portfolio(str(current_user.id))
        entry_data = next((item for item in portfolio_data if item['id'] == str(portfolio_entry.id)), None)
        
        if entry_data:
            return PortfolioEntryResponse(**entry_data)
        else:
            raise HTTPException(status_code=500, detail="Ошибка получения данных портфеля")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка добавления в портфель: {e}")


@app.get("/portfolio", response_model=List[PortfolioEntryResponse])
async def get_portfolio(current_user: User = Depends(get_current_user)):
    """Получение портфеля пользователя"""
    try:
        portfolio_data = await portfolio_service.get_portfolio(str(current_user.id))
        return [PortfolioEntryResponse(**item) for item in portfolio_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения портфеля: {e}")


@app.get("/portfolio/statistics", response_model=PortfolioStatisticsResponse)
async def get_portfolio_statistics(current_user: User = Depends(get_current_user)):
    """Получение статистики портфеля"""
    try:
        stats = await portfolio_service.get_portfolio_statistics(str(current_user.id))
        return PortfolioStatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики портфеля: {e}")


@app.delete("/portfolio/{portfolio_id}")
async def remove_from_portfolio(
    portfolio_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление записи из портфеля"""
    try:
        success = await portfolio_service.remove_from_portfolio(portfolio_id, str(current_user.id))
        if success:
            return {"message": "Запись удалена из портфеля"}
        else:
            raise HTTPException(status_code=404, detail="Запись не найдена")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления из портфеля: {e}")


@app.put("/portfolio/{portfolio_id}")
async def update_portfolio_entry(
    portfolio_id: str,
    payload: PortfolioUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Обновление записи в портфеле"""
    try:
        success = await portfolio_service.update_portfolio_entry(
            portfolio_id=portfolio_id,
            quantity=payload.quantity,
            purchase_price=payload.purchase_price,
            notes=payload.notes,
            user_id=str(current_user.id)
        )
        
        if success:
            return {"message": "Запись обновлена"}
        else:
            raise HTTPException(status_code=404, detail="Запись не найдена")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления записи: {e}")


# ========== ЭНДПОИНТЫ СИНХРОНИЗАЦИИ ==========

@app.post("/sync/sheets", response_model=SheetSyncResponse)
async def sync_google_sheets():
    """Синхронизация с Google Sheets"""
    try:
        result = await sheet_sync_service.full_sync()
        return SheetSyncResponse(
            success=result['success'],
            message=result.get('message', 'Синхронизация завершена'),
            synced_count=result.get('total_synced', 0),
            errors=result.get('cases_sync', {}).get('errors', []) + 
                   result.get('prices_sync', {}).get('errors', [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {e}")


@app.get("/sync/sheets/status")
async def get_sheet_status():
    """Получение статуса подключения к Google Sheets"""
    try:
        status = await sheet_sync_service.get_sheet_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
