"""Endpoints de exportación (Excel y PDF)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.export_service import ExportService

router = APIRouter()

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx_response(content: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type=_XLSX,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/ranking.xlsx")
def export_ranking(db: Session = Depends(get_db)) -> StreamingResponse:
    return _xlsx_response(ExportService(db).ranking_excel(), "ranking.xlsx")


@router.get("/results.xlsx")
def export_results(db: Session = Depends(get_db)) -> StreamingResponse:
    return _xlsx_response(ExportService(db).results_excel(), "resultados.xlsx")


@router.get("/predictions.xlsx")
def export_predictions(db: Session = Depends(get_db)) -> StreamingResponse:
    return _xlsx_response(ExportService(db).predictions_excel(), "predicciones.xlsx")


@router.get("/summary.pdf")
def export_summary_pdf(db: Session = Depends(get_db)) -> StreamingResponse:
    content = ExportService(db).summary_pdf()
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resumen.pdf"},
    )
