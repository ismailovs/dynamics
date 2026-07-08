from __future__ import annotations

from io import BytesIO
from typing import Dict

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def export_pdf(title: str, kpis: Dict[str, float]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, height - 40, title)
    pdf.setFont("Helvetica", 11)
    y = height - 80
    for key, value in kpis.items():
        pdf.drawString(40, y, f"{key}: {value}")
        y -= 18
        if y < 60:
            pdf.showPage()
            y = height - 40
    pdf.save()
    buffer.seek(0)
    return buffer.read()
