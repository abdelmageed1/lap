# تحويل التطبيق إلى ملف EXE قابل للتوزيع على Windows 7

## الأداة: PyInstaller

**يجب تنفيذ خطوات هذا الدليل على جهاز Windows فعلي** (أو جهاز افتراضي بـ Windows) — على عكس بعض أدوات .NET، لا يمكن بناء ملف `.exe` لبرامج بايثون من على Linux/Mac بشكل موثوق لأن PyInstaller يحزم مكتبات النظام الأصلية (native) الخاصة بنظام التشغيل الذي يُنفَّذ عليه الأمر.

**مهم جدًا**: لضمان توافق الملف الناتج مع Windows 7 فعليًا، **يجب** تنفيذ هذه الخطوات من داخل بيئة Python 3.9 (وليس أي إصدار أحدث) مُثبَّتة على نفس جهاز البناء.

### الخطوات

1. على جهاز Windows به Python 3.9، ثبّت الحزم:
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. من داخل مجلد `python-app`، نفّذ:
   ```cmd
   pyinstaller --name LapLIS --onefile --windowed --add-data "app/seed_data;app/seed_data" --add-data "app/reports/fonts;app/reports/fonts" main.py
   ```

   شرح كل جزء:
   | الجزء | المعنى |
   |---|---|
   | `--name LapLIS` | اسم ملف الـ exe الناتج |
   | `--onefile` | دمج كل شيء في ملف تنفيذي واحد |
   | `--windowed` | عدم فتح نافذة Console سوداء خلف التطبيق |
   | `--add-data "app/seed_data;..."` | تضمين ملفات JSON المرجعية (كتالوج التحاليل والأسعار) داخل الملف التنفيذي |
   | `--add-data "app/reports/fonts;..."` | تضمين خط DejaVu Sans المطلوب لطباعة PDF بالعربية |

   أو، بدل تنفيذ الأمر يدويًا، شغّل سكربت PowerShell الجاهز (يحتوي على نفس الأمر بالضبط):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
   ```

3. بعد الانتهاء، ستجد الملف الناتج في: `dist/LapLIS.exe`

4. وزّع هذا الملف فقط على أجهزة العملاء — لا حاجة لتثبيت Python أو أي حزمة على جهاز العميل، كل شيء مُضمَّن داخل الملف.

## ملاحظة عن قراءة الملفات المُضمَّنة داخل EXE

عند التشغيل من داخل ملف `.exe` مبني بـ PyInstaller، تتغيّر طريقة الوصول للملفات المُرفَقة (`--add-data`). إن واجهت خطأ `FileNotFoundError` عند قراءة ملفات `seed_data` أو الخطوط بعد التحويل لـ exe، يجب تعديل الدوال التي تقرأ هذه الملفات (`app/config.py`، `app/seed.py`، `app/reports/pdf_base.py`) لتتحقق من المتغير الخاص `sys._MEIPASS` (المسار المؤقت الذي يفكّ فيه PyInstaller الملفات المُرفَقة أثناء التشغيل) واستخدامه كجذر عند وجوده، مثال:

```python
import sys, os

def resource_path(relative_path):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)
```

## اختبار قبل التوزيع

قبل نسخ الملف لأي جهاز عميل:
1. جرّب تشغيل `dist/LapLIS.exe` على نفس جهاز البناء أولًا.
2. الأفضل: جرّبه على جهاز Windows 7 فعلي أو آلة افتراضية Windows 7 نظيفة (بدون Python مثبَّت عليها) للتأكد من التوافق الكامل قبل التوزيع الفعلي على المعمل.

## تحديثات مستقبلية

عند تحديث الكود، أعد تنفيذ أمر `pyinstaller` نفسه لإنشاء نسخة جديدة من `LapLIS.exe`. قاعدة البيانات محفوظة في `%APPDATA%\LapLIS-Python` بشكل منفصل تمامًا عن ملف البرنامج، فلن تتأثر بتحديث الملف التنفيذي.

## البديل: بناء الـ EXE من Linux/Mac عبر Docker (بدون جهاز Windows فعلي)

إن لم يتوفر لديك جهاز Windows فعلي للبناء، يوفّر المشروع `Dockerfile` جاهزًا في `python-app/Dockerfile` يبني الملف التنفيذي آليًا باستخدام **Wine** + تثبيت حقيقي لـ **Python 3.9 لنظام Windows** (نفس المثبِّت الرسمي من python.org) يعمل داخل Wine، ثم ينفّذ نفس أمر PyInstaller بالضبط. الناتج ملف `.exe` حقيقي يعمل على Windows 7 فعليًا (وليس ملفًا لينكسيًا).

### لماذا هذا يعمل (ولماذا لا يمكن تشغيل PyInstaller مباشرة على Linux)؟

PyInstaller **لا يحوّل الكود بين الأنظمة (لا يعمل cross-compile)** — هو فقط يحزم مفسّر بايثون (Python interpreter) الذي يعمل تحته وقت التنفيذ. فإذا شغّلته على Linux ستحصل على ملف تنفيذي لينكسي (ELF)، وليس Windows PE. لذلك يقوم الـ Dockerfile بتشغيل **مثبِّت Python الرسمي لنظام Windows نفسه** (لا مفسّر Linux) داخل Wine، وتنفيذ PyInstaller من خلاله — فيكون الناتج ملف Windows PE حقيقي.

### أوامر البناء

```bash
cd python-app
docker build -t laplis-win7-builder .
docker run --rm -v "$(pwd)/dist:/output" laplis-win7-builder
```

بعد انتهاء الأمرين، ستجد `LapLIS.exe` (وملفاته المرافقة إن وُجدت) داخل مجلد `dist/` على جهازك مباشرة — بدون الحاجة لأي جهاز Windows فعليًا طوال العملية.

> ملاحظة: عملية البناء بالكامل (تثبيت Wine + تحميل مثبِّت Python + تثبيت الحزم + PyInstaller) تتم داخل صورة Docker مؤقتة، وقد تستغرق عدة دقائق في أول تنفيذ (تحميل حزم Wine ومثبِّت Python من الإنترنت). لم يتم اختبار هذا الـ Dockerfile فعليًا على جهاز به Docker (لم يتوفر Docker daemon أثناء التطوير)، لذا **يُنصح باختبار الملف الناتج جيدًا** (نفس خطوات "اختبار قبل التوزيع" أعلاه) قبل التوزيع الفعلي على أجهزة العملاء. إن واجهت أي خطأ أثناء `docker build`، فالبديل الموثوق 100% يبقى دائمًا البناء المباشر على جهاز Windows بـ Python 3.9 كما هو موضح في القسم الأول من هذا الملف.
