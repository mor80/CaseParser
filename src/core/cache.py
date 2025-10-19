"""
Система кэширования для CaseParser
"""

import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

from redis.asyncio import Redis


class CacheService:
    """Сервис кэширования с поддержкой Redis и in-memory кэша"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", use_redis: bool = True):
        self.use_redis = use_redis
        self.redis_client: Optional[Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        if use_redis:
            try:
                self.redis_client = Redis.from_url(redis_url, decode_responses=True)
                print("✅ Redis кэш подключен")
            except Exception as e:
                print(f"⚠️ Redis недоступен, используется in-memory кэш: {e}")
                self.use_redis = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        if self.use_redis and self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                print(f"Ошибка получения из Redis: {e}")
                return None
        
        # Fallback to memory cache
        if key in self.memory_cache:
            cache_data = self.memory_cache[key]
            if cache_data['expires_at'] > datetime.utcnow():
                return cache_data['value']
            else:
                del self.memory_cache[key]
        
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Сохранение значения в кэш"""
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.setex(
                    key, 
                    ttl_seconds, 
                    json.dumps(value, default=str)
                )
                return True
            except Exception as e:
                print(f"Ошибка сохранения в Redis: {e}")
                return False
        
        # Fallback to memory cache
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self.memory_cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
        return True
    
    async def delete(self, key: str) -> bool:
        """Удаление значения из кэша"""
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.delete(key)
                return True
            except Exception as e:
                print(f"Ошибка удаления из Redis: {e}")
                return False
        
        # Fallback to memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
            return True
        
        return False
    
    async def clear(self) -> bool:
        """Очистка всего кэша"""
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.flushdb()
                return True
            except Exception as e:
                print(f"Ошибка очистки Redis: {e}")
                return False
        
        # Fallback to memory cache
        self.memory_cache.clear()
        return True
    
    async def exists(self, key: str) -> bool:
        """Проверка существования ключа в кэше"""
        if self.use_redis and self.redis_client:
            try:
                return await self.redis_client.exists(key) > 0
            except Exception as e:
                print(f"Ошибка проверки в Redis: {e}")
                return False
        
        # Fallback to memory cache
        if key in self.memory_cache:
            cache_data = self.memory_cache[key]
            if cache_data['expires_at'] > datetime.utcnow():
                return True
            else:
                del self.memory_cache[key]
        
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        if self.use_redis and self.redis_client:
            try:
                info = await self.redis_client.info()
                return {
                    'type': 'redis',
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', '0B'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'total_keys': await self.redis_client.dbsize()
                }
            except Exception as e:
                return {'type': 'redis', 'error': str(e)}
        
        # Memory cache stats
        return {
            'type': 'memory',
            'total_keys': len(self.memory_cache),
            'expired_keys': len([
                k for k, v in self.memory_cache.items() 
                if v['expires_at'] <= datetime.utcnow()
            ])
        }


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Декоратор для кэширования результатов функций"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Создаем ключ кэша на основе аргументов функции
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Пытаемся получить из кэша
            cache_service = getattr(wrapper, '_cache_service', None)
            if cache_service:
                cached_result = await cache_service.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем в кэш
            if cache_service:
                await cache_service.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


class CacheManager:
    """Менеджер кэша для различных типов данных"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    async def cache_market_overview(self, data: Dict[str, Any], ttl: int = 300):
        """Кэширование обзора рынка"""
        await self.cache_service.set("market_overview", data, ttl)
    
    async def get_cached_market_overview(self) -> Optional[Dict[str, Any]]:
        """Получение кэшированного обзора рынка"""
        return await self.cache_service.get("market_overview")
    
    async def cache_top_gainers(self, data: list, days: int, ttl: int = 600):
        """Кэширование топ гейнеров"""
        key = f"top_gainers_{days}d"
        await self.cache_service.set(key, data, ttl)
    
    async def get_cached_top_gainers(self, days: int) -> Optional[list]:
        """Получение кэшированных топ гейнеров"""
        key = f"top_gainers_{days}d"
        return await self.cache_service.get(key)
    
    async def cache_top_losers(self, data: list, days: int, ttl: int = 600):
        """Кэширование топ лузеров"""
        key = f"top_losers_{days}d"
        await self.cache_service.set(key, data, ttl)
    
    async def get_cached_top_losers(self, days: int) -> Optional[list]:
        """Получение кэшированных топ лузеров"""
        key = f"top_losers_{days}d"
        return await self.cache_service.get(key)
    
    async def cache_volatile_cases(self, data: list, days: int, ttl: int = 900):
        """Кэширование волатильных кейсов"""
        key = f"volatile_cases_{days}d"
        await self.cache_service.set(key, data, ttl)
    
    async def get_cached_volatile_cases(self, days: int) -> Optional[list]:
        """Получение кэшированных волатильных кейсов"""
        key = f"volatile_cases_{days}d"
        return await self.cache_service.get(key)
    
    async def cache_price_history(self, case_id: str, data: list, days: int, ttl: int = 1800):
        """Кэширование истории цен"""
        key = f"price_history_{case_id}_{days}d"
        await self.cache_service.set(key, data, ttl)
    
    async def get_cached_price_history(self, case_id: str, days: int) -> Optional[list]:
        """Получение кэшированной истории цен"""
        key = f"price_history_{case_id}_{days}d"
        return await self.cache_service.get(key)
    
    async def invalidate_case_cache(self, case_id: str):
        """Инвалидация кэша для конкретного кейса"""
        # Удаляем все кэшированные данные для кейса
        keys_to_delete = [
            f"price_history_{case_id}_30d",
            f"price_history_{case_id}_7d",
            f"price_history_{case_id}_1d"
        ]
        
        for key in keys_to_delete:
            await self.cache_service.delete(key)
    
    async def invalidate_market_cache(self):
        """Инвалидация кэша рынка"""
        keys_to_delete = [
            "market_overview",
            "top_gainers_7d",
            "top_gainers_30d",
            "top_losers_7d", 
            "top_losers_30d",
            "volatile_cases_30d"
        ]
        
        for key in keys_to_delete:
            await self.cache_service.delete(key)


# Глобальный экземпляр кэша
cache_service = CacheService()
cache_manager = CacheManager(cache_service)
