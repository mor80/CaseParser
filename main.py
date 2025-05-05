import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from Code.sheet_client import GoogleSheetClient
from Code.price_fetcher import PriceFetcher
from config import UPDATE_PERIOD_MIN

sheet_client = GoogleSheetClient()
price_fetcher = PriceFetcher()


async def update_prices_job():
    print("Обновление цен…")
    rows = sheet_client.read_rows()
    prices_by_row = await price_fetcher.fetch_prices_in_batches(rows)

    for row_idx, price in prices_by_row.items():
        sheet_client.update_price(row_idx, price)
        print(f"row {row_idx}: {price}")

    print("Готово!")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(
        update_prices_job,
        trigger="interval",
        minutes=UPDATE_PERIOD_MIN,
    )
    scheduler.start()

    # запуск первой итерации без ожидания
    loop.create_task(update_prices_job())

    print(f"Скрипт запущен, обновление каждые {UPDATE_PERIOD_MIN} мин.")
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Остановлено пользователем.")


if __name__ == "__main__":
    main()
