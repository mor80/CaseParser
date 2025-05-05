import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Dict

from config import GOOGLE_SHEET_NAME, GOOGLE_CREDS_FILE


class GoogleSheetClient:
    def __init__(self) -> None:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            GOOGLE_CREDS_FILE, scope
        )
        self.gc = gspread.authorize(creds)
        self.sheet = self.gc.open(GOOGLE_SHEET_NAME).sheet1

    def read_rows(self) -> List[Dict]:
        return self.sheet.get_all_records()

    def update_price(self, row_idx: int, price: str) -> None:
        """Обновляем E‑колонку (5) ТОЛЬКО если цена валидная."""
        if price == "N/A":
            current_val = self.sheet.cell(row_idx, 5).value
            if current_val:
                return
        self.sheet.update_cell(row_idx, 5, price)
