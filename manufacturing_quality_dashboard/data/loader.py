from __future__ import annotations

from io import BytesIO
from typing import Dict, Tuple

import pandas as pd


def load_excel_workbook(uploaded_file: bytes) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    workbook = pd.read_excel(BytesIO(uploaded_file), sheet_name=None, engine="openpyxl")
    normalized_sheets: Dict[str, pd.DataFrame] = {}
    for name, frame in workbook.items():
        if frame is None or frame.empty:
            continue
        sheet = frame.copy()
        sheet["__sheet_name"] = name
        normalized_sheets[name] = sheet
    if not normalized_sheets:
        return pd.DataFrame(), {}
    combined = pd.concat(normalized_sheets.values(), ignore_index=True)
    combined.columns = [str(col).strip() for col in combined.columns]
    return combined, normalized_sheets
