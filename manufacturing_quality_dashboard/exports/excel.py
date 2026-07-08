from __future__ import annotations

from io import BytesIO
from typing import Dict

import pandas as pd


def export_excel(dataframes: Dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, frame in dataframes.items():
            if frame is None or frame.empty:
                continue
            safe_name = name[:31]
            frame.to_excel(writer, sheet_name=safe_name, index=False)
    output.seek(0)
    return output.read()
