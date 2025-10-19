"""
Сервис для синхронизации данных с Google Sheets
"""

from typing import Dict

from src.core.database import DatabaseService
from src.services.price_fetcher import PriceFetcher
from src.services.sheet_client import GoogleSheetClient


class SheetSyncService:
    """Сервис для синхронизации данных с Google Sheets"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.sheet_client = GoogleSheetClient()
        self.price_fetcher = PriceFetcher()
    
    async def sync_cases_from_sheet(self) -> Dict:
        """Синхронизация кейсов из Google Sheets в базу данных"""
        try:
            print("🔄 Синхронизация кейсов из Google Sheets...")
            
            # Получаем данные из Google Sheets
            rows = self.sheet_client.read_rows()
            
            if not rows:
                return {
                    'success': False,
                    'message': 'Нет данных в Google Sheets',
                    'synced_count': 0
                }
            
            synced_count = 0
            errors = []
            
            for row in rows:
                try:
                    case_name = row.get('Name', '').strip()
                    if not case_name:
                        continue
                    
                    # Создаем или обновляем кейс в базе данных
                    case = await self.db_service.save_case(
                        name=case_name,
                        steam_url=row.get('Steam URL', '')
                    )
                    
                    synced_count += 1
                    print(f"✅ Синхронизирован кейс: {case_name}")
                    
                except Exception as e:
                    error_msg = f"Ошибка синхронизации кейса {row.get('Name', 'Unknown')}: {e}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            return {
                'success': True,
                'message': f'Синхронизировано {synced_count} кейсов',
                'synced_count': synced_count,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка синхронизации: {e}',
                'synced_count': 0
            }
    
    async def sync_prices_from_sheet(self) -> Dict:
        """Синхронизация цен из Google Sheets"""
        try:
            print("🔄 Синхронизация цен из Google Sheets...")
            
            # Получаем данные из Google Sheets
            rows = self.sheet_client.read_rows()
            
            if not rows:
                return {
                    'success': False,
                    'message': 'Нет данных в Google Sheets',
                    'updated_count': 0
                }
            
            # Получаем цены для всех кейсов
            prices_by_row = await self.price_fetcher.fetch_prices_in_batches(rows)
            
            updated_count = 0
            errors = []
            
            for row_idx, price in prices_by_row.items():
                try:
                    if price == "N/A":
                        continue
                    
                    # Получаем информацию о кейсе
                    case_name = rows[row_idx - 2]["Name"]
                    
                    # Получаем или создаем кейс
                    case = await self.db_service.save_case(case_name)
                    
                    # Сохраняем цену в историю
                    await self.db_service.save_price(str(case.id), float(price))
                    
                    # Обновляем статистику
                    await self.db_service.update_case_statistics(str(case.id))
                    
                    # Обновляем Google Sheets
                    self.sheet_client.update_price(row_idx, price)
                    
                    updated_count += 1
                    print(f"✅ Обновлена цена для {case_name}: {price} руб.")
                    
                except Exception as e:
                    error_msg = f"Ошибка обновления цены для строки {row_idx}: {e}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            return {
                'success': True,
                'message': f'Обновлено {updated_count} цен',
                'updated_count': updated_count,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка синхронизации цен: {e}',
                'updated_count': 0
            }
    
    async def full_sync(self) -> Dict:
        """Полная синхронизация данных с Google Sheets"""
        print("🚀 Запуск полной синхронизации с Google Sheets...")
        
        # Синхронизируем кейсы
        cases_result = await self.sync_cases_from_sheet()
        
        # Синхронизируем цены
        prices_result = await self.sync_prices_from_sheet()
        
        return {
            'success': cases_result['success'] and prices_result['success'],
            'cases_sync': cases_result,
            'prices_sync': prices_result,
            'total_synced': cases_result.get('synced_count', 0) + prices_result.get('updated_count', 0)
        }
    
    async def get_sheet_status(self) -> Dict:
        """Получение статуса Google Sheets"""
        try:
            rows = self.sheet_client.read_rows()
            
            if not rows:
                return {
                    'connected': False,
                    'message': 'Нет данных в Google Sheets',
                    'rows_count': 0
                }
            
            return {
                'connected': True,
                'message': 'Подключение к Google Sheets успешно',
                'rows_count': len(rows),
                'sample_data': rows[:3] if rows else []
            }
            
        except Exception as e:
            return {
                'connected': False,
                'message': f'Ошибка подключения к Google Sheets: {e}',
                'rows_count': 0
            }
