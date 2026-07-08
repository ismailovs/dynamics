from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class AppConfig:
    app_title: str = "Manufacturing Discrepancy Analyzer"
    default_page_layout: str = "wide"
    max_rows_preview: int = 5000
    top_n_rankings: int = 20
    anomaly_contamination: float = 0.05


APP_CONFIG = AppConfig()


CANONICAL_FIELDS: Dict[str, List[str]] = {
    "assembler": ["assembler", "assembler name", "built by", "employee", "builder"],
    "checker": ["checker", "checked by", "inspector", "inspected by", "qa"],
    "rework": ["rework by", "rework person", "repair by", "technician", "repaired by"],
    "job_number": ["job", "job number", "work order", "wo", "job no"],
    "project": ["project", "project name", "contract"],
    "customer": ["customer", "client", "account"],
    "department": ["department", "dept", "area", "section"],
    "category": ["category", "defect type", "issue type", "classification"],
    "root_cause": ["root cause", "cause", "failure cause", "reason"],
    "severity": ["severity", "priority", "criticality"],
    "description": ["description", "issue", "defect", "problem", "discrepancy"],
    "cost": ["cost", "repair cost", "expense", "amount", "value"],
    "repair_time": ["repair time", "duration", "hours", "time to repair", "cycle time"],
    "date": ["date", "created date", "reported date", "inspection date", "timestamp"],
    "shift": ["shift", "work shift", "line shift"],
    "status": ["status", "state", "closed", "open"],
    "comments": ["comments", "notes", "remarks"],
}


DISPLAY_NAMES: Dict[str, str] = {
    "assembler": "Assembler",
    "checker": "Checker",
    "rework": "Rework By",
    "job_number": "Job Number",
    "project": "Project",
    "customer": "Customer",
    "department": "Department",
    "category": "Category",
    "root_cause": "Root Cause",
    "severity": "Severity",
    "description": "Description",
    "cost": "Cost",
    "repair_time": "Repair Time",
    "date": "Date",
    "shift": "Shift",
    "status": "Status",
    "comments": "Comments",
}
