"""Generates the automated weekly/monthly summary report and, if the lab has configured SMTP
settings, emails it to the lab owner. If SMTP isn't configured, the report is still generated and
saved locally so the feature is useful even without any mail server on hand."""
from __future__ import annotations

import os
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage

from app.config import get_periodic_reports_dir
from app.reports.excel_export import generate_periodic_report_excel
from app.services import catalog_service, reports_service


FREQUENCY_DAYS = {"weekly": 7, "monthly": 30}


def is_report_due(settings: dict, today: date = None) -> bool:
    if not settings.get("periodic_report_enabled"):
        return False
    today = today or date.today()
    last_sent = settings.get("periodic_report_last_sent")
    if not last_sent:
        return True
    try:
        last_sent_date = date.fromisoformat(last_sent[:10])
    except ValueError:
        return True
    frequency = settings.get("periodic_report_frequency") or "monthly"
    interval_days = FREQUENCY_DAYS.get(frequency, 30)
    return (today - last_sent_date).days >= interval_days


def _build_report_data(start_date: str, end_date: str, period_label: str):
    comparison_totals = reports_service.get_visits_in_range(start_date=start_date, end_date=end_date)
    revenue = sum(v["total_amount"] for v in comparison_totals)
    paid = sum(v["paid_amount"] for v in comparison_totals)
    balance = sum(v["balance"] for v in comparison_totals)

    summary_rows = [
        ["الفترة", period_label],
        ["عدد الزيارات", len(comparison_totals)],
        ["إجمالي الإيرادات", round(revenue, 2)],
        ["إجمالي التحصيلات", round(paid, 2)],
        ["إجمالي المتبقي", round(balance, 2)],
    ]

    doctors = reports_service.get_top_referring_doctors(start_date=start_date, end_date=end_date)
    doctors_rows = [[d["doctor_name"] or "غير محدد", d["visit_count"], round(d["total_amount"], 2)] for d in doctors]

    staff = reports_service.get_staff_productivity_analytics(start_date=start_date, end_date=end_date)
    staff_rows = [[s["full_name"], s["visits_created"], round(s["collected_payments"], 2), s["results_processed"]]
                  for s in staff]

    return summary_rows, doctors_rows, staff_rows


def generate_report_file(settings: dict, today: date = None) -> str:
    """Builds the Excel file for the period since the last report (or the last 30 days if this is
    the first one ever) and returns the saved file path."""
    today = today or date.today()
    last_sent = settings.get("periodic_report_last_sent")
    if last_sent:
        start_date = last_sent[:10]
    else:
        frequency = settings.get("periodic_report_frequency") or "monthly"
        start_date = (today - timedelta(days=FREQUENCY_DAYS.get(frequency, 30))).isoformat()
    end_date = today.isoformat()
    period_label = f"{start_date} إلى {end_date}"

    summary_rows, doctors_rows, staff_rows = _build_report_data(start_date, end_date, period_label)

    out_dir = get_periodic_reports_dir()
    os.makedirs(out_dir, exist_ok=True)
    file_path = os.path.join(out_dir, f"periodic_report_{end_date}.xlsx")
    generate_periodic_report_excel(file_path, period_label, summary_rows, doctors_rows, staff_rows)
    return file_path


def send_report_email(settings: dict, file_path: str) -> bool:
    """Returns True if the email was sent, False if SMTP isn't configured or sending failed
    (failure is swallowed - the report file itself is already saved regardless)."""
    host = settings.get("smtp_host")
    to_email = settings.get("smtp_to_email")
    if not host or not to_email:
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = f"التقرير الدوري - {settings.get('lab_name') or 'LapLIS'}"
        msg["From"] = settings.get("smtp_from_email") or settings.get("smtp_username") or "laplis@localhost"
        msg["To"] = to_email
        msg.set_content("مرفق التقرير الدوري لأداء المعمل. تم إرساله تلقائيًا بواسطة LapLIS.")
        with open(file_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application",
                               subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               filename=os.path.basename(file_path))

        port = settings.get("smtp_port") or 587
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            username = settings.get("smtp_username")
            password = settings.get("smtp_password")
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        return True
    except Exception:
        return False


def check_and_run(today: date = None) -> dict:
    """Called once at app startup. Returns a dict describing what happened, always safe to call -
    any failure here must never prevent the app from starting."""
    result = {"ran": False, "file_path": None, "emailed": False}
    try:
        settings = catalog_service.get_lab_settings()
        if not is_report_due(settings, today=today):
            return result

        file_path = generate_report_file(settings, today=today)
        emailed = send_report_email(settings, file_path)

        catalog_service.save_lab_settings({
            **settings,
            "periodic_report_last_sent": (today or date.today()).isoformat(),
        })

        result.update({"ran": True, "file_path": file_path, "emailed": emailed})
    except Exception:
        pass
    return result
