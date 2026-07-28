# قاعدة البيانات — كل جدول وعلاقاته

## المخطط الكامل (Entity Relationship)

```
departments ──< tests >── test_parameters ──< parameter_reference_ranges
                   │              │
                   │         result_values <── visit_test_orders
                   │                                  │
              price_list_items             visits ────┘
                                              │
                              patients ───────┤
                              doctors ────────┤
                              referral_sources┘
                                   │
                              payments

roles ──< role_permissions
roles ──< users ──< audit_logs
```

---

## جداول الكتالوج

### `departments`
```sql
id | name
```
أقسام المعمل (هيماتولوجي، كيمياء، هرمونات، إلخ). مرجع للتحاليل.

---

### `tests`
```sql
id | name | abbreviation | department_id | default_unit
   | turnaround_time | collection_instructions
   | is_active | display_order
```
954 تحليل مستخرج من `ahmed_lab.mdb`. كل تحليل له:
- `abbreviation` — اختصار يظهر في قائمة البحث
- `is_active` — التحاليل المعطَّلة تختفي من الاستقبال لكن تبقى في سجلات المرضى
- `display_order` — ترتيب الظهور في الكتالوج

---

### `test_parameters`
```sql
id | test_id | name | unit | data_type | display_order
```
كل تحليل له معيار واحد أو أكثر:
- تحليل بسيط: معيار واحد اسمه `"النتيجة"`
- CBC: 22 معيارًا (WBC, RBC, HB, HCT, MCV, MCH, MCHC, PLT, Color Index, ...)
- Creatinine Clearance: 4 معايير (Serum/Urine Creatinine، Urine Volume، Clearance)

`data_type` = `"Numeric"` أو `"Text"` — يحدد نوع الحقل في شاشة الإدخال.

---

### `parameter_reference_ranges`
```sql
id | parameter_id | sex | age_from_years | age_to_years
   | low_value | high_value | normal_text
```
المدى الطبيعي لكل معيار حسب النوع والعمر:
- `sex`: `"Male"` / `"Female"` / `"Both"`
- `low_value`/`high_value`: للقيم الرقمية (يُحسَب منهما الـ flag تلقائيًا)
- `normal_text`: للقيم الوصفية (مثل "سالب" / "Negative")
- سطر واحد يمكن تغطية كل الفئات (`age_from=0, age_to=120`)

---

### `price_list_items`
```sql
id | test_id | source_type | price
```
- `source_type`: `"Individual"` / `"Insurance"` / اسم جهة الإحالة
- كل تحليل يمكن أن يكون له عدة أسعار (سعر لكل جهة)
- لو ما في سعر للجهة المحددة، يُستخدم سعر `"Individual"` احتياطًا

---

## جداول المرضى والزيارات

### `patients`
```sql
id | full_name | title | gender | age_years | phone
   | created_by_user_id
```
- `phone` — غير فريد (مريض يمكن أن يكون له أكثر من رقم مسجَّل تاريخيًا)
- `created_by_user_id` — للتدقيق على من أنشأ السجل

---

### `visits`
```sql
id | patient_id | invoice_number | visit_date | doctor_id
   | referral_source_id | total_amount | discount_amount | paid_amount
```
- `invoice_number` — تسلسلي، يُولَّد تلقائيًا (`MAX(invoice_number) + 1`)
- `paid_amount` — يُحدَّث عند كل دفعة جديدة
- المتبقي = `total_amount - discount_amount - paid_amount` (يُحسَب عند القراءة)

---

### `visit_test_orders`
```sql
id | visit_id | test_id | price | status
```
- سطر واحد لكل تحليل مطلوب ضمن الزيارة
- `price` يُحجَز وقت الطلب (لا يتأثر بتغيير أسعار الكتالوج لاحقًا)
- `status`: `Ordered → InProgress → Completed → Reviewed` (تسلسل أحادي الاتجاه)

---

### `result_values`
```sql
id | visit_test_order_id | parameter_id | numeric_value | text_value | flag
```
- سطر لكل معيار لكل تحليل مطلوب
- `flag`: `Normal / High / Low / Abnormal / Manual`
- `numeric_value` و`text_value` — واحد منهم فقط مملوء حسب نوع المعيار

---

### `payments`
```sql
id | visit_id | amount | paid_at
```
الدفعات التفصيلية — مجموعها + الحقل `visits.paid_amount` يعطي إجمالي المدفوع.

---

## جداول الإعدادات والصلاحيات

### `lab_settings`
```sql
id | lab_name | tagline | address | phone_numbers
   | footer_signature1 | footer_signature2
   | digital_seal_text | app_title
   | brand_primary_color | brand_secondary_color
```
- `id = 1` دائمًا (جدول إعداد واحد فقط)
- `brand_*_color` — hex codes تُستخدَم لتوليد كامل الـ QSS (الثيم)
- `digital_seal_text` — يظهر في footer تقرير النتيجة كختم رقمي

---

### `roles` + `role_permissions`
```sql
-- roles
id | name

-- role_permissions
id | role_id | module_key | can_view | can_add | can_edit | can_delete
```
- `module_key`: `Dashboard / Reception / Visits / Results / PatientHistory / Catalog / Pricing / Settings / Users / Audit / Backup / Reports`
- الصلاحيات قيم `0/1` (boolean SQLite)
- عند إضافة `module_key` جديد للكود، دالة `_backfill_missing_module_permissions()` تضيفه تلقائيًا لكل الأدوار الموجودة

---

### `users`
```sql
id | username | full_name | password_hash | role_id | is_active
```
- `password_hash` — bcrypt hash، لا تُخزَّن كلمة المرور الصريحة أبدًا
- `is_active = 0` — يمنع الدخول بدون حذف السجل

---

### `audit_logs`
```sql
id | table_name | row_id | action | user_id | timestamp | details
```
- `timestamp` — UTC ISO format
- `user_id` قد تكون NULL لعمليات النظام التلقائية
- `details` — نص حر للسياق (مثل: `lab_name=معمل نخبة`)

---

## الـ Indexes (للأداء)

| Index | الجدول | الأعمدة | السبب |
|---|---|---|---|
| idx_visits_patient | visits | patient_id | البحث بسجل المريض |
| idx_result_values_visit_test | result_values | visit_test_order_id | تحميل نتائج تحليل |
| idx_visits_visit_date | visits | visit_date | تقارير اليوم/الأسبوع |
| idx_users_username | users | username | تسجيل الدخول |
| idx_tests_name | tests | name | البحث في الكتالوج |
| idx_price_list_test | price_list_items | test_id | جلب سعر التحليل |

---

## ملاحظات مهمة على SQLite

### مكان الملف
```
Windows: C:\Users\<username>\AppData\Roaming\LapLIS-Python\laplis.db
```

### الـ Foreign Keys
```sql
PRAGMA foreign_keys = ON;  -- يُشغَّل عند كل اتصال في get_connection()
```
بدونه، SQLite لا يطبّق قيود العلاقات!

### ON DELETE CASCADE
كل جداول التفاصيل فيها `ON DELETE CASCADE`:
- حذف تحليل → تُحذَف معاييره ومداه ونتائجه
- حذف زيارة → تُحذَف طلباتها ودفعاتها

### مشكلة database is locked
SQLite لا يقبل اتصالين يكتبان في نفس الوقت. الحل المُطبَّق:
```python
# تمرير conn الحالي لـ log_action بدل فتح اتصال جديد
log_action(table_name, row_id, action, user_id=uid, conn=conn)
```
