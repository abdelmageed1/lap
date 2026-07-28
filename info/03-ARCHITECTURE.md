# بنية الكود — كيف مبني البرنامج من الداخل

## نظرة عامة على الطبقات

```
main.py / cli.py
    └── app/
        ├── ui/          ← طبقة الواجهة (PySide2/Qt)
        │   ├── main_window.py      ← النافذة الرئيسية + القائمة الجانبية
        │   ├── login_window.py     ← شاشة الدخول
        │   ├── *_view.py           ← شاشة لكل وحدة
        │   ├── styles.py           ← نظام الألوان والثيمات
        │   ├── qt_shim.py          ← حارس PySide2 (يمنع التحميل الصامت لـ PySide6)
        │   └── animated_button.py  ← زر بتأثير hover
        │
        ├── services/    ← طبقة البيزنس (لا تعرف عن Qt إطلاقًا)
        │   ├── auth_service.py     ← تسجيل الدخول + bcrypt
        │   ├── catalog_service.py  ← التحاليل والكتالوج والأسعار
        │   ├── visit_service.py    ← الزيارات والمرضى والمدفوعات
        │   ├── result_service.py   ← إدخال النتائج والاعتماد
        │   ├── auto_calc.py        ← الحسابات التلقائية (CBC / Creatinine)
        │   ├── audit_service.py    ← استعلامات سجل التدقيق
        │   ├── user_service.py     ← إدارة المستخدمين والأدوار
        │   ├── reports_service.py  ← إحصائيات وبيانات التقارير
        │   └── backup_service.py   ← نسخ واستعادة قاعدة البيانات
        │
        ├── reports/     ← توليد PDF
        │   ├── lab_report.py       ← تقرير النتيجة
        │   ├── invoice_report.py   ← الفاتورة
        │   ├── barcode_report.py   ← ملصقات الباركود
        │   └── pdf_base.py         ← قاعدة مشتركة (ReportLab)
        │
        ├── utils/
        │   └── audit.py            ← دالة log_action المشتركة
        │
        ├── db.py        ← اتصال SQLite + تعريف المخطط
        ├── config.py    ← المسارات (DATABASE_PATH، أدلة PDF، إلخ)
        └── seed.py      ← تعبئة البيانات الأولية + ترقية قواعد البيانات القديمة
```

---

## قاعدة الفصل الأساسية

**الـ `ui/` لا تكتب مباشرة في قاعدة البيانات.**  
كل كتابة تمر عبر `services/` — هذا يعني أن أي خطأ في البيزنس لا يصل إلى الواجهة، وأن الاختبارات التلقائية تعمل بدون Qt.

```python
# ✅ صح
from app.services import visit_service
visit_service.save_visit(data)

# ❌ خطأ (لا يحدث في الكود)
conn = get_connection()
conn.execute("INSERT INTO visits ...")  # في ملف UI
```

---

## تدفق التشغيل (startup flow)

```python
# main.py
app = QApplication(sys.argv)
app.setLayoutDirection(Qt.RightToLeft)   # RTL عربي لكل النافذة

db.init_schema()        # ينشئ الجداول لو مش موجودة
seed.seed_if_empty()    # يملأ البيانات الأولية لو قاعدة جديدة
                        # + ترقية قواعد قديمة (backfill)

login = LoginWindow()
login.show()
app.exec_()
```

---

## نظام الألوان والثيمات — `styles.py`

```python
# للقراءة من أي مكان
from app.ui.styles import get_color, get_saved_theme

color = get_color("primary")   # يُرجع hex حسب الثيم الحالي
theme = get_saved_theme()      # "dark" أو "light"
```

- الألوان تأتي من `lab_settings.brand_primary_color` / `brand_secondary_color`
- الثيم يُحفَظ في ملف `storage_config.json` (ليس في قاعدة البيانات)
- كل الأنماط QSS تُولَّد ديناميكيًا من الألوان المُختارة بدل hardcoded CSS

---

## توليد PDF — طبقة `reports/`

**المكتبة:** ReportLab (تعمل على Python 3.9 + Windows 7)  
**الخط:** DejaVu Sans مُضمَّن في `app/reports/fonts/` — يدعم Unicode كامل (بما فيه العربية)

```
pdf_base.py
├── RTL layout helper (Arabic text reversal)
├── Header: شعار المعمل + اسمه + تاريخ الطباعة
└── Footer: التوقيعات + الختم الرقمي

lab_report.py       ← يستخدم pdf_base + يضيف جدول النتائج
invoice_report.py   ← يستخدم pdf_base + جدول التحاليل والأسعار
barcode_report.py   ← يُنشئ Code128 بملصق لكل عينة
```

> **ملاحظة RTL:** ReportLab لا يدعم العربية مباشرة — `arabic_text.py` تعكس اتجاه النص ميكانيكيًا باستخدام `bidi` algorithm (مكتبة `python-bidi`) قبل تمريره لـ ReportLab.

---

## إدارة المسارات — `config.py`

لا يوجد أي مسار مكتوب يدويًا في الكود. كل مسار يُحسَب من:

```
DATA_DIR (AppData/Roaming/LapLIS-Python/)
├── laplis.db              ← قاعدة البيانات
├── logo_cached.png        ← نسخة PNG من الشعار
└── storage_config.json    ← مسار التخزين القابل للتعديل

STORAGE_ROOT (~/Documents/LapLIS/ — قابل للتعديل من الإعدادات)
├── PDFs/Reports/          ← تقارير النتائج
├── PDFs/Invoices/         ← الفواتير
├── Exports/Patients/      ← ملفات CSV تصدير المرضى
├── Exports/Catalog/       ← ملفات CSV تصدير الكتالوج
└── Backups/               ← النسخ الاحتياطية
```

---

## ترقية قواعد البيانات — `seed.py`

`seed_if_empty()` تُشغَّل **عند كل إقلاع** — وليس مرة واحدة فقط:

```python
def seed_if_empty():
    # 1. البيانات الأولية (تُضاف مرة واحدة لو الجداول فارغة)
    if not has_roles:        _seed_roles_and_admin(conn)
    if not has_departments:  _seed_catalog(conn); _seed_profiles(conn, ...)
    if not has_settings:     # إعدادات افتراضية

    # 2. ترقيات تشتغل في كل مرة (آمنة للتكرار)
    _ensure_reference_defaults(conn)        # أطباء وجهات إحالة افتراضية
    _backfill_missing_module_permissions(conn)  # صلاحيات شاشات جديدة
    _backfill_new_profile_breakdowns(conn)  # معايير تحاليل جديدة
```

**قاعدة الأمان في backfill:** لا يُحذَف أي معيار لو فيه نتيجة مُدخَلة بالفعل.

---

## الاختبارات التلقائية — `tests/`

```
tests/
├── test_auto_calc.py      ← 38 اختبار: صيغ CBC + Creatinine + normalize_param_key
└── test_seed_migration.py ← 5 اختبارات: ترقية قواعد البيانات + سلامة البيانات
```

**التشغيل:**
```bash
python -m pytest tests/ -v
# النتيجة المتوقعة: 43 passed
```

الاختبارات لا تحتاج Qt ولا واجهة رسومية — تعمل على أي بيئة بـ Python فقط.

---

## ملاحظات PySide2 المهمة

### int() في setTextAlignment
```python
# OverflowError على PySide2 بدون int()
item.setTextAlignment(int(Qt.AlignCenter))

# للمحاذاة المركّبة
item.setTextAlignment(int(Qt.AlignRight) | int(Qt.AlignVCenter))
```

### QMessageBox بدون Yes|No flags
```python
# TypeError على PySide2
reply = QMessageBox.question(self, ..., QMessageBox.Yes | QMessageBox.No)

# الطريقة الآمنة
msg = QMessageBox(self)
yes_btn = msg.addButton("نعم", QMessageBox.YesRole)
no_btn  = msg.addButton("لا",  QMessageBox.NoRole)
msg.exec_()
if msg.clickedButton() is yes_btn:
    ...
```

### لا PySide6 أبدًا
```python
# qt_shim.py يرفض التشغيل بوضوح لو PySide2 مش موجود
# بدل ما يستبدله بـ PySide6 بصمت (PySide6 لا يدعم Windows 7)
```
