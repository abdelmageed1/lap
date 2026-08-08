2️⃣ أمر بناء الـ .exe للنسخة الجديدة (Build Phase)
بعد الانتهاء من التعديلات واختبارها، نفّذ هذا السطر للبناء:

powershell
```
taskkill /F /IM "mostafa elznaty.exe" /T 2>$null; $env:LAPLIS_ARCH=""; pyinstaller --noconfirm --clean "mostafa elznaty.spec"
```

