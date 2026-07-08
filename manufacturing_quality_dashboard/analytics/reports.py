from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd


@dataclass
class ReportBundle:
    kpis: Dict[str, float]
    summary_tables: Dict[str, pd.DataFrame]


def build_report_bundle(kpis: Dict[str, float], tables: Dict[str, pd.DataFrame]) -> ReportBundle:
    return ReportBundle(kpis=kpis, summary_tables=tables)
