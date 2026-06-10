"""Servicio de exportación a Excel y PDF."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.ranking_service import RankingService


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.matches = MatchRepository(db)
        self.predictions = PredictionRepository(db)
        self.participants = ParticipantRepository(db)
        self.ranking_service = RankingService(db)
        self._exports_dir = settings.exports_path
        self._exports_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------- Excel -----------------------------
    def ranking_excel(self) -> bytes:
        rows = self.ranking_service.get_ranking()
        df = pd.DataFrame(
            [
                {
                    "Posición": r.posicion,
                    "Participante": r.nombre,
                    "Puntos": r.puntos_totales,
                    "Exactos": r.aciertos_exactos,
                    "Aciertos": r.partidos_acertados,
                }
                for r in rows
            ]
        )
        return self._to_excel_bytes(df, "Ranking")

    def results_excel(self) -> bytes:
        df = pd.DataFrame(
            [
                {
                    "Fase": m.fase,
                    "Grupo": m.grupo,
                    "Local": m.local,
                    "Visitante": m.visitante,
                    "Goles Local": m.goles_local,
                    "Goles Visitante": m.goles_visitante,
                    "Estado": m.estado.value,
                    "Fecha": m.fecha.isoformat() if m.fecha else None,
                }
                for m in self.matches.list()
            ]
        )
        return self._to_excel_bytes(df, "Resultados")

    def predictions_excel(self) -> bytes:
        rows = []
        for pred in self.predictions.list():
            participant = pred.participant
            match = pred.match
            rows.append(
                {
                    "Participante": participant.nombre if participant else "?",
                    "Email": participant.email if participant else "?",
                    "Local": match.local if match else "?",
                    "Visitante": match.visitante if match else "?",
                    "Pred Local": pred.pred_local,
                    "Pred Visitante": pred.pred_visitante,
                }
            )
        df = pd.DataFrame(rows)
        return self._to_excel_bytes(df, "Predicciones")

    @staticmethod
    def _to_excel_bytes(df: pd.DataFrame, sheet: str) -> bytes:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet)
        return buffer.getvalue()

    # ------------------------------ PDF ------------------------------
    def summary_pdf(self) -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title="Resumen Mundial 2026")
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Mundial 2026 - Resumen de Ranking", styles["Title"]))
        story.append(
            Paragraph(
                f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 16))

        rows = self.ranking_service.get_ranking()
        data = [["Pos", "Participante", "Puntos", "Exactos", "Aciertos"]]
        for r in rows:
            data.append(
                [r.posicion, r.nombre, r.puntos_totales, r.aciertos_exactos, r.partidos_acertados]
            )

        table = Table(data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#eff6ff")],
                    ),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ]
            )
        )
        story.append(table)
        doc.build(story)
        return buffer.getvalue()

    # ---------------------------- A disco ----------------------------
    def save_to_disk(self, kind: str) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        mapping = {
            "ranking": (self.ranking_excel, f"ranking_{ts}.xlsx"),
            "results": (self.results_excel, f"resultados_{ts}.xlsx"),
            "predictions": (self.predictions_excel, f"predicciones_{ts}.xlsx"),
            "pdf": (self.summary_pdf, f"resumen_{ts}.pdf"),
        }
        if kind not in mapping:
            raise ValueError(f"Tipo de exportación inválido: {kind}")
        func, filename = mapping[kind]
        path = self._exports_dir / filename
        path.write_bytes(func())
        return path
