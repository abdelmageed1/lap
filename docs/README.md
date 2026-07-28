# LapLIS (نسخة Python) — نظام معمل نخبة للدكتور مصطفى الزناتي المتوافقة مع Windows 7





اخر تعديل 
```
pyinstaller --noconfirm --onefile --windowed --name "LapLIS" --icon "logo/app_icon.ico" --add-data "app/seed_data;app/seed_data" --add-data "app/reports/fonts;app/reports/fonts" --add-data "logo;logo" main.py
```

 المتطلبات الوحيدة اللازمة على جهاز العميل (Windows 7):
لكي يعمل البرنامج على جهاز العميل المزود بـ Windows 7 بدون أي مشاكل، يفضل دائماً التأكد من:

وجود حزمة Service Pack 1 (SP1) على ويندوز 7.
تثبيت حزمة Visual C++ Redistributable (2015-2022) (وهي مجانية وتثبّت في دقيقة واحدة).

```
conda activate laplis
python main.py


```

# 1️⃣ إنشاء بيئة جديدة باسم “laplis”
conda create -y -n laplis python=3.13
# 2️⃣ تفعيل البيئة
conda activate laplis
# 3️⃣ تثبيت PySide2 من قناة conda‑forge
conda install -y -c conda-forge pyside2
```
هذه نسخة بديلة من نظام LapLIS، مبنية بلغة **Python** بدلاً من C#/.NET، خصيصًا لدعم الأجهزة القديمة التي لا تزال تعمل بنظام **Windows 7** (والذي توقفت .NET 8 — المستخدمة في النسخة الأساسية — عن دعمه تمامًا).

تحتوي هذه النسخة على **نفس منطق العمل الأساسي** الموجود في نظام الأكسس الأصلي (`ahmed_lab.mdb`): استقبال المرضى، كتالوج التحاليل والأسعار، إدخال النتائج مع المدى الطبيعي حسب السن/النوع، طباعة الفواتير وتقارير النتائج، لوحة متابعة إحصائية، صفحة إعدادات للإدارة، والمستخدمين والأدوار الأساسية. **لا تحتوي** على الإضافات المتقدمة الموجودة في النسخة الرئيسية (.NET) مثل شاشة التقارير والإحصائيات المنفصلة المعقدة أو القوالب الجاهزة — لأن الهدف من هذه النسخة هو التوافق الأقصى مع الأجهزة القديمة بأبسط وأخف استاك ممكن.

## بداية سريعة

| أريد أن... | اذهب إلى |
|---|---|
| أفهم لماذا Python ولماذا يدعم Windows 7 | [01-OVERVIEW.md](01-OVERVIEW.md) |
| أشغّل الكود المصدري على جهازي | [02-SETUP-AND-RUN.md](02-SETUP-AND-RUN.md) |
| أحوّل المشروع لملف `.exe` قابل للتوزيع على Windows 7 | [03-BUILD-EXE.md](03-BUILD-EXE.md) |
| أتعلم استخدام كل شاشة | [04-USER-GUIDE.md](04-USER-GUIDE.md) |
| أفهم قاعدة البيانات | [05-DATABASE-SCHEMA.md](05-DATABASE-SCHEMA.md) |

## الاستاك التقني

Python 3.9 · PySide2 (Qt5) · SQLite (مدمجة في Python) · ReportLab (PDF) · bcrypt

## بيانات الدخول الافتراضية

```
اسم المستخدم: admin
كلمة المرور:   Admin@123
```

**غيّر كلمة المرور فورًا بعد أول تشغيل.**
