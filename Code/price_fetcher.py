import asyncio
import random
from typing import Dict, List
from urllib.parse import quote

import aiohttp

from config import (
    CONCURRENCY, STEAM_CURRENCY, STEAM_COUNTRY,
    RETRY_COUNT, RETRY_DELAY,
    BATCH_SIZE, BATCH_SLEEP
)

STEAM_API = (
    "https://steamcommunity.com/market/priceoverview/"
    "?country={country}&currency={currency}&appid=730&market_hash_name={name}"
)


class PriceFetcher:
    """Асинхронно получает цены для списка кейсов с повторами."""

    def __init__(self) -> None:
        self.sem = asyncio.Semaphore(CONCURRENCY)

    async def _one_request(self, session: aiohttp.ClientSession, url: str) -> str:
        async with self.sem, session.get(url, timeout=30) as resp:
            if resp.status != 200:
                return "N/A"
            data = await resp.json()

            price_raw = data.get("lowest_price", "N/A")
            price = price_raw.replace(" руб.", "").replace("\u200e", "")

            return price

    async def _fetch(self, session: aiohttp.ClientSession, name: str) -> str:
        url_name = quote(name)
        url = STEAM_API.format(
            country=STEAM_COUNTRY, currency=STEAM_CURRENCY, name=url_name
        )

        delay = RETRY_DELAY
        for attempt in range(1, RETRY_COUNT + 1):
            price = await self._one_request(session, url)
            if price != "N/A":
                return price

            await asyncio.sleep(delay + random.uniform(0, 0.4))
            delay *= 2

        return "N/A"

    async def fetch_prices(self, rows: List[Dict]) -> Dict[int, str]:
        prices = {}
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit_per_host=CONCURRENCY)) as session:
            tasks, indices = [], []
            for idx, row in enumerate(rows, start=2):
                name = row["Name"]
                tasks.append(asyncio.create_task(self._fetch(session, name)))
                indices.append(idx)

            for idx, coro in zip(indices, tasks):
                prices[idx] = await coro

        return prices

    async def fetch_prices_in_batches(self, rows: List[Dict]) -> Dict[int, str]:
        """
        Возвращает словарь {row_index_in_sheet : price},
        причём row_index_in_sheet — глобальный (A1‑нотация: 2, 3, 4…).
        """
        result: Dict[int, str] = {}
        total = len(rows)

        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit_per_host=CONCURRENCY)
        ) as session:
            for start in range(0, total, BATCH_SIZE):
                end = min(start + BATCH_SIZE, total)
                batch_rows = rows[start:end]
                row_indices = range(start + 2, end + 2)

                print(f"Запрос пачки {start + 2}–{end + 1}")

                tasks = [
                    asyncio.create_task(self._fetch(session, r["Name"]))
                    for r in batch_rows
                ]
                prices = await asyncio.gather(*tasks)

                for idx, price in zip(row_indices, prices):
                    result[idx] = price

                if end < total:
                    await asyncio.sleep(BATCH_SLEEP)

        return result
