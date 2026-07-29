"""Internal quality control (QC) tracking: target mean/SD per (parameter, control level), and a
running log of measured control values - the data behind a Levey-Jennings chart."""
from __future__ import annotations

from datetime import datetime

from app.db import get_connection

CONTROL_LEVELS = ["Level 1", "Level 2", "Level 3"]


def save_qc_target(parameter_id: int, control_level: str, target_mean: float, target_sd: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO qc_targets (parameter_id, control_level, target_mean, target_sd) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(parameter_id, control_level) DO UPDATE SET target_mean=excluded.target_mean, "
            "target_sd=excluded.target_sd",
            (parameter_id, control_level, target_mean, target_sd),
        )
        conn.commit()
    finally:
        conn.close()


def get_qc_target(parameter_id: int, control_level: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM qc_targets WHERE parameter_id = ? AND control_level = ?",
            (parameter_id, control_level),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _classify(value: float, mean: float, sd: float) -> str:
    if sd <= 0:
        return "InControl"
    distance = abs(value - mean) / sd
    if distance > 3:
        return "OutOfControl"
    if distance > 2:
        return "Warning"
    return "InControl"


def record_qc_value(parameter_id: int, control_level: str, value: float, user_id: int = None) -> tuple[bool, str]:
    target = get_qc_target(parameter_id, control_level)
    if not target:
        return False, "لم يتم تحديد المتوسط والانحراف المعياري المستهدف لهذا المعيار/المستوى بعد"

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO qc_records (parameter_id, control_level, measured_value, recorded_at, user_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (parameter_id, control_level, value, datetime.now().isoformat(timespec="seconds"), user_id),
        )
        conn.commit()
    finally:
        conn.close()

    status = _classify(value, target["target_mean"], target["target_sd"])
    labels = {"InControl": "ضمن النطاق الطبيعي", "Warning": "تحذير: خارج ±2 انحراف معياري",
              "OutOfControl": "خارج السيطرة: تجاوز ±3 انحراف معياري"}
    return True, labels[status]


def get_qc_history(parameter_id: int, control_level: str, limit: int = 30) -> list:
    target = get_qc_target(parameter_id, control_level)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM qc_records WHERE parameter_id = ? AND control_level = ? "
            "ORDER BY recorded_at DESC LIMIT ?",
            (parameter_id, control_level, limit),
        ).fetchall()
        records = [dict(r) for r in reversed(rows)]
        for r in records:
            if target:
                r["status"] = _classify(r["measured_value"], target["target_mean"], target["target_sd"])
            else:
                r["status"] = "InControl"
        return records
    finally:
        conn.close()
