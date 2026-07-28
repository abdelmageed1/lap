

```
أوامر عمل بيئة جديدة (لو احتجت مستقبلاً)
powershell
# 1. إنشاء البيئة
conda create -n laplis python=3.9 -y
# 2. تفعيل البيئة
conda activate laplis
# 3. تثبيت المكتبات
pip install -r requirements.txt
# 4. تثبيت PySide2 (مهم جداً!)
pip install PySide2==5.15.15
# 5. تثبيت PyInstaller
pip install pyinstaller
# 6. بناء الـ exe
cd E:\source\lap\LapLISpythonvbacalcupdate\python-app
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1

```