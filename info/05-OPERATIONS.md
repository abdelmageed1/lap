# التشغيل والبناء والعمليات

## تشغيل من الكود المصدري

### المتطلبات

| المكوّن | الإصدار | ملاحظة |
|---|---|---|
| Python | 3.9 | آخر إصدار رسمي يدعم Windows 7 — أو 3.9–3.12 على Windows 10/11 |
| PySide2 | 5.15.x | Qt5 — لا تستبدل بـ PySide6 (لا يدعم Windows 7) |
| ReportLab | أي حديث | توليد PDF |
| bcrypt | أي حديث | تشفير كلمات المرور |
| python-bidi + arabic-reshaper | أي حديث | نص عربي صحيح في PDF |

```bash
pip install -r requirements.txt
```

### التشغيل
```bash
python main.py
```

**عند أول تشغيل تلقائيًا:**
1. تُنشأ قاعدة البيانات في `%APPDATA%\LapLIS-Python\laplis.db`
2. يُعبَّأ كتالوج 954 تحليل + 2289 سعر + المدى الطبيعي
3. يُنشأ مستخدم admin افتراضي (`admin / Admin@123`)

---

## بيانات الدخول الافتراضية

```
اسم المستخدم: admin
كلمة المرور:   Admin@123
```

> **غيّر كلمة المرور فورًا** من شاشة المستخدمين بعد أول دخول.

---

## ملفات ومجلدات البرنامج

### البيانات (لا تُمَس يدويًا)
```
%APPDATA%\LapLIS-Python\
├── laplis.db              ← قاعدة البيانات (النسخة الاحتياطية تحفظ هذا الملف)
├── logo_cached.png        ← cache للشعار
└── storage_config.json    ← مسار التخزين المُختار من الإعدادات
```

### الملفات المُولَّدة (يمكن تغيير مكانها من الإعدادات)
```
~/Documents/LapLIS/          ← المجلد الافتراضي
├── PDFs/Reports/            ← تقارير النتائج المعتمدة
├── PDFs/Invoices/           ← فواتير الزيارات
├── Exports/Patients/        ← CSV تصدير بيانات مرضى
├── Exports/Catalog/         ← CSV تصدير كتالوج
└── Backups/                 ← النسخ الاحتياطية
```

---

## الاختبارات التلقائية

```bash
python -m pytest tests/ -v
# النتيجة: 43 passed
```

**ما تغطيه:**
- `tests/test_auto_calc.py` — صيغ CBC الـ 10، تصفية الكرياتينين، مطابقة أسماء المعايير
- `tests/test_seed_migration.py` — ترقية قواعد البيانات القديمة بأمان

الاختبارات معزولة تمامًا (in-memory SQLite) — تشغيلها آمن دون تأثير على قاعدة البيانات الحقيقية.

---

## بناء ملف EXE للتوزيع على Windows 7

### الطريقة المباشرة (على جهاز Windows بـ Python 3.9)

```cmd
pip install pyinstaller
pyinstaller "mostafa elznaty.spec"
```

أو بالأمر الكامل:
```cmd
pyinstaller --name LapLIS --onefile --windowed ^
  --add-data "app/seed_data;app/seed_data" ^
  --add-data "app/reports/fonts;app/reports/fonts" ^
  --add-data "logo;logo" ^
  main.py
```

الناتج: `dist/LapLIS.exe` — ملف واحد، لا يحتاج Python مثبَّتة على جهاز العميل.

### البناء من Linux/Mac عبر Docker (بدون جهاز Windows)

```bash
cd python-app
docker build -t laplis-win7-builder .
docker run --rm -v "$(pwd)/dist:/output" laplis-win7-builder
```

الـ Dockerfile يستخدم Wine + مثبِّت Python 3.9 الرسمي لـ Windows داخل Linux لإنتاج ملف exe حقيقي.

> ⚠️ اختبر الملف الناتج على Windows 7 فعلي (أو VM) قبل التوزيع.

---

## النسخ الاحتياطي والاستعادة

### النسخ الاحتياطي اليدوي (من واجهة البرنامج)
1. شاشة **النسخ الاحتياطي** → **إنشاء نسخة احتياطية الآن**
2. تُحفَظ نسخة في `~/Documents/LapLIS/Backups/laplis_backup_YYYY-MM-DD_HH-MM.db`

### الاستعادة
1. اختر النسخة المطلوبة من القائمة → **استعادة**
2. يُؤخَذ backup تلقائي من الوضع الحالي قبل الاستبدال
3. **أعد تشغيل البرنامج بعد الاستعادة**

### النسخ الاحتياطي اليدوي (خارج البرنامج)
```
انسخ الملف: %APPDATA%\LapLIS-Python\laplis.db
إلى أي مكان آمن (USB، Google Drive، إلخ)
```

---

## ترقية البرنامج (تحديث الكود)

1. استبدل ملفات الكود الجديدة (أو العقلة النسخة الجديدة من `LapLIS.exe`)
2. **لا تحذف** مجلد `%APPDATA%\LapLIS-Python\` — فيه قاعدة بياناتك
3. شغّل البرنامج — `seed_if_empty()` ستُشغِّل تلقائيًا:
   - `_backfill_missing_module_permissions()` — صلاحيات شاشات جديدة
   - `_backfill_new_profile_breakdowns()` — معايير تحاليل جديدة

**لا حاجة لأي migration يدوي.**

---

## أداة سطر الأوامر (cli.py)

```bash
# تصدير الكتالوج كـ JSON
python cli.py export backup.json

# استيراد كتالوج (يستبدل الجداول الحالية بالكامل!)
python cli.py import backup.json
```

> ⚠️ `import` تحذف وتستبدل — خذ نسخة احتياطية قبلها.

---

## إعادة التشغيل من الصفر (للتطوير)

لمسح كل البيانات وبدء قاعدة بيانات نظيفة:
```bash
# على Windows
rmdir /s "%APPDATA%\LapLIS-Python"
python main.py
```

---

## استكشاف الأخطاء الشائعة

| المشكلة | السبب المحتمل | الحل |
|---|---|---|
| `ImportError: PySide2 is not installed` | PySide2 غير مثبَّت أو مثبَّت PySide6 بدلاً منه | `pip install PySide2` |
| `OverflowError` عند فتح أي جدول | إصدار قديم من الكود بدون `int()` | تأكد أن الكود محدَّث |
| `database is locked` | اتصالان مفتوحان في نفس الوقت | تمرير `conn` لـ `log_action` بدل فتح اتصال جديد |
| الشاشة فارغة بعد تحديث الكود | مودل جديد ومش موجود صلاحيات له | `_backfill_missing_module_permissions` تُصلح عند التشغيل |
| PDF لا يُفتح تلقائيًا | المتصفح الافتراضي لـ PDF مش مُعيَّن | افتح المجلد وافتح الملف يدويًا |
| النص العربي في PDF مقلوب | `arabic-reshaper` / `python-bidi` مش مثبَّتة | `pip install arabic-reshaper python-bidi` |
| `ModuleNotFoundError` | بيئة افتراضية مش مُفعَّلة | `venv\Scripts\activate` ثم `pip install -r requirements.txt` |

---

## ملف requirements.txt الحالي

```
PySide2
reportlab
bcrypt
arabic-reshaper
python-bidi
pytest
```
