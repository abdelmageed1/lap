# دليل بناء EXE — خطوة بخطوة (Windows 7 Compatible)

---

## ⚠️ قبل أي شيء — شروط أساسية

| الشرط | التحقق |
|---|---|
| Miniconda مثبَّت | `conda --version` |
| بيئة `laplis` موجودة بـ Python 3.9 | `conda activate laplis` ← لا تعطي خطأ |
| PySide2 مثبَّت في البيئة | `python -c "import PySide2; print(PySide2.__version__)"` |
| PyInstaller مثبَّت في البيئة | `pyinstaller --version` |

---

## الخطوة 1 — إعداد البيئة (مرة واحدة فقط)

لو البيئة موجودة بالفعل، اقفز للخطوة 2 مباشرة.  
لو البيئة اتحذفت أو فيها مشكلة، أعدها من الصفر:

```powershell
# 1. إنشاء بيئة نظيفة بـ Python 3.9
conda create -n laplis python=3.9 -y

# 2. تفعيل البيئة
conda activate laplis

# 3. تثبيت كل المكتبات
pip install -r requirements.txt

# 4. تثبيت PySide2 بإصدار محدد (مهم!)
pip install PySide2==5.15.2.1

# 5. تثبيت PyInstaller
pip install pyinstaller
```

> **لماذا PySide2==5.15.2.1 تحديدًا؟**  
> هو أحدث إصدار رسمي مستقر لمكتبة PySide2 على PyPI مع دعم كامل لـ Python 3.9 و Windows 7+.

---

## الخطوة 2 — تفعيل البيئة

**قبل أي بناء** تأكد أن البيئة الصحيحة مفعَّلة:

```powershell
conda activate laplis
```

تظهر `(laplis)` في بداية السطر — لو مش ظاهرة ما تكمّلش.

---

## الخطوة 3 — الانتقال للمجلد الصحيح

```powershell
cd E:\source\lap\LapLISpythonvbacalcupdate\python-app
```

---

## الخطوة 4 — تشغيل الاختبارات (اختياري لكن مُوصى به)

```powershell
python -m pytest tests/ -v
```

النتيجة المتوقعة: `43 passed` — لو في فشل لا تبني الـ exe.

---

## الخطوة 5 — البناء

### الطريقة الموصى بها (PowerShell script جاهز)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

### أو مباشرة بدون سكربت

```powershell
C:\Users\abdelmageed.fathy\AppData\Local\miniconda3\envs\laplis\Scripts\pyinstaller.exe `
    --noconfirm --clean "mostafa elznaty.spec"
```

---

## الخطوة 6 — التحقق من الناتج

بعد انتهاء البناء (5–10 دقائق):

```powershell
# تأكد الملف موجود
Test-Path "dist\mostafa elznaty.exe"
# يجب أن يعطي: True

# حجم الملف (عادة 60–120 MB)
(Get-Item "dist\mostafa elznaty.exe").Length / 1MB
```

---

## الخطوة 7 — اختبار قبل التوزيع

```powershell
# شغّل الـ exe مباشرة
& "dist\mostafa elznaty.exe"
```

**تحقق من:**
- [ ] شاشة تسجيل الدخول تفتح بشكل صحيح
- [ ] اللغة العربية تظهر سليمة
- [ ] الواجهة من اليمين لليسار (RTL)
- [ ] شاشة الاستقبال تعمل
- [ ] طباعة فاتورة PDF تعمل
- [ ] طباعة تقرير نتيجة PDF يظهر عربي سليم

---

## ملاحظات مهمة على الـ .spec

ملف `mostafa elznaty.spec` يتضمن:

```python
# مسارات مثبَّتة لبيئة Conda على جهازك
_conda_bin   = r'C:\Users\abdelmageed.fathy\...\laplis\library\bin'
_pyside2_dir = r'C:\Users\abdelmageed.fathy\...\laplis\...\PySide2'
```

**هذه المسارات مُثبَّتة لجهازك** — لو بنيت على جهاز آخر، يجب تعديلها.

### الـ DLLs المضافة يدويًا (سبب الإضافة)

Conda تثبّت PySide2 بنسخة DLL اسمها `Qt5Core_conda.dll` (بدل `Qt5Core.dll`).  
PyInstaller لا يكتشفها تلقائيًا — لذلك الـ spec يضيفها يدويًا:

```python
_conda_dlls = [
    'Qt5Core_conda.dll',
    'Qt5Gui_conda.dll',
    'Qt5Widgets_conda.dll',
    'Qt5Charts_conda.dll',
    'Qt5Svg_conda.dll',
    'Qt5Network_conda.dll',
    ...
]
```

لو حذفتها من الـ spec، الـ exe يفشل بـ `No compatible Qt binding found`.

---

## أخطاء شائعة وحلولها

| الخطأ | السبب | الحل |
|---|---|---|
| `laplis conda environment not found` | البيئة مش موجودة | نفّذ الخطوة 1 |
| `No compatible Qt binding found` | PySide2 مش مُضمَّنة بشكل صحيح | تأكد أن `_conda_dlls` كامل في الـ spec |
| `FileNotFoundError: seed_data` | بيانات JSON مش مُرفَقة | تأكد من `datas=[('app/seed_data', ...)]` في الـ spec |
| `FileNotFoundError: fonts` | خط DejaVu مش مُرفَق | تأكد من `('app/reports/fonts', ...)` في الـ spec |
| الـ exe يفتح وينغلق فورًا | خطأ في runtime | شغّل من CMD بدون `--windowed` للاطلاع على الخطأ |
| `OverflowError` عند فتح جدول | نسخة قديمة من الكود | تأكد من تحديث الكود قبل البناء |
| حجم الـ exe صغير جدًا (< 10 MB) | PyInstaller من بيئة غلط | تأكد أن `conda activate laplis` مفعَّل |

---

## تشخيص الـ exe المكسور (debug mode)

لو الـ exe يفشل بدون رسالة خطأ واضحة:

```powershell
# 1. أنشئ نسخة debug مؤقتة
C:\Users\abdelmageed.fathy\AppData\Local\miniconda3\envs\laplis\Scripts\pyinstaller.exe `
    --noconfirm --clean --console "mostafa elznaty.spec"

# 2. شغّل الناتج من CMD وشوف الأخطاء
"dist\mostafa elznaty.exe"
```

الـ `--console` يخلّي نافذة سوداء تظهر مع رسائل الخطأ الحقيقية.

---

## بعد التوزيع — ترقية العميل

عند توزيع نسخة جديدة على جهاز عميل:

1. **خذ نسخة احتياطية من قاعدة البيانات أولاً** (من داخل البرنامج)
2. استبدل ملف `mostafa elznaty.exe` القديم بالجديد فقط
3. **لا تحذف** أي ملف آخر على جهاز العميل
4. شغّل البرنامج — الترقية التلقائية تعمل وحدها:
   - تُضاف صلاحيات أي شاشات جديدة
   - تُضاف معايير تحاليل جديدة
   - **لا فقدان للبيانات**