# دليل بناء EXE — خطوة بخطوة (Windows 7 Compatible)

---

## 🔴 مهم جدًا: هل عايز تدعم Windows 7 32-bit؟ اقرأ القسم ده الأول

**كل خطوات هذا الملف (عبر Conda) بتنتج exe لـ 64-bit فقط** - حتى لو الكود نفسه متوافق مع Windows 7،
الملف التنفيذي الناتج **لن يفتح إطلاقًا** على أي جهاز Windows 7 نسخة 32-bit (exe الـ 64-bit مرفوض
تمامًا من نظام تشغيل 32-bit، مش مجرد تحذير أو بطء - رفض كامل بدون رسالة خطأ مفيدة غالبًا).

**السبب**: قناة Conda-forge (اللي بتوفر PySide2 المُستخدَمة في بيئة `laplis`) **توقفت عن نشر أي
نسخة حديثة لـ Windows 32-bit** من PySide2 - آخر نسخة متاحة لـ 32-bit عندهم قديمة جدًا (لبايثون 2.7
و3.5 فقط) ومش هتشتغل مع كود المشروع (Python 3.9). تم التأكد من ده فعليًا بفحص قائمة حزم
conda-forge لـ win-32 مباشرة.

**الحل**: لازم تبني نسخة 32-bit **بدون Conda إطلاقًا** - باستخدام بايثون 32-bit أصلي + pip
(المكتبات دي بتوفر wheels رسمية لـ 32-bit فعليًا، تم التأكد منها على PyPI):

```powershell
# 1. نزّل مثبِّت بايثون 3.9 نسخة 32-bit (وليس 64-bit) من الموقع الرسمي:
#    https://www.python.org/downloads/release/python-3913/
#    اختر "Windows installer (x86)" - وليس "x86-64"

# 2. أنشئ بيئة افتراضية منفصلة بهذا البايثون 32-bit تحديدًا
#    (استبدل المسار بمكان تثبيت بايثون 32-bit الفعلي عندك)
C:\Users\<اسمك>\AppData\Local\Programs\Python\Python39-32\python.exe -m venv laplis32
laplis32\Scripts\activate

# 3. تأكد إنك فعلًا جوه بيئة 32-bit (مهم - تحقق قبل الاستكمال)
python -c "import struct; print(struct.calcsize('P') * 8)"
# لازم يطبع 32 - لو طبع 64 يبقى لسه شغّال بايثون غلط، ارجع للخطوة 2

# 4. ثبّت المكتبات (كلها عندها wheels رسمية لـ 32-bit)
pip install -r requirements.txt
pip install pyinstaller

# 5. ابني الـ exe بنفس أمر PyInstaller المعتاد (الخطوة 5 تحت)، لكن من داخل بيئة الـ32-bit دي.
#    لا تضبط متغيّر البيئة LAPLIS_ARCH إطلاقًا هنا (اتركه فاضي) - ملف الـ.spec افتراضيًا
#    (لو المتغيّر ده مش موجود) بيستهدف 32-bit (target_arch='x86'). لو ضبطته بالخطأ لـ
#    amd64/x64/64 هيبني نسخة 64-bit بدل 32-bit.
```

> **ملف الـ.spec (`mostafa elznaty.spec`) نفسه يعمل بدون أي تعديل مع هذا المسار**: المسارات
> الثابتة (`_conda_bin` وغيرها) بداخله مكتوبة لجهاز المطوّر الأصلي على بيئة Conda، لكنها محميّة
> بشرط `if os.path.exists(...)` - فلو بنيت من بيئة pip/venv عادية (زي هنا)، هذه المسارات ببساطة
> مش موجودة فيتجاهلها PyInstaller تلقائيًا، ويعتمد بدلًا منها على اكتشافه التلقائي المعتاد
> لملفات PySide2 المُثبَّتة عبر pip (وهو الأسلوب القياسي المدعوم فعليًا، بعكس تسمية DLLs الخاصة
> بـ Conda اللي كانت محتاجة استثناء يدوي).

> **مكتبات المشروع كلها متأكَّد إنها بتدعم 32-bit فعليًا** (فُحصت على PyPI مباشرة):
> PySide2==5.15.2.1، shiboken2 (تابعة تلقائيًا)، bcrypt، python-bidi، pyinstaller - كلها عندها
> wheels رسمية لـ `win32`. أما reportlab وarabic-reshaper فهي مكتبات بايثون خالصة (pure Python)
> فمش مرتبطة بمعمارية المعالج إطلاقًا.

> **⚠️ لازم أيضًا على جهاز العميل (Windows 7 32-bit)**: تثبيت
> **Microsoft Visual C++ Redistributable (x86)** - PySide2/Qt5 محتاجة مكتبات C++ الأساسية دي
> عشان تشتغل، وأغلب أجهزة Windows 7 القديمة معندهاش نسخة حديثة منها مثبَّتة افتراضيًا. نزّلها من
> موقع مايكروسوفت الرسمي وثبّتها على جهاز العميل **قبل** تشغيل البرنامج أول مرة.

> **ملحوظة**: لو مش محتاج فعليًا تدعم أجهزة 32-bit (يعني كل أجهزة العملاء المستهدَفة Windows 7
> **64-bit**)، تجاهل القسم ده بالكامل واستكمل بالخطوات العادية (Conda) تحت.

---

## ⚠️ قبل أي شيء — شروط أساسية (مسار Conda العادي - 64-bit)

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
| `FileNotFoundError: fonts` | خط Amiri مش مُرفَق | تأكد من `('app/reports/fonts', ...)` في الـ spec |
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