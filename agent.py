import sqlite3
import pandas as pd

def analyze_data():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT name, date, reason FROM visits", conn)
    conn.close()

    if df.empty:
        return "لا توجد بيانات للعرض."

    messages = []

    # أكثر المرضى زيارة
    top_patient = df['name'].value_counts().idxmax()
    count = df['name'].value_counts().max()
    messages.append(f"👤 أكثر مريض زيارة هو: {top_patient} ({count} زيارة).")

    # أكثر الأعراض تكرارًا
    common_reasons = df['reason'].dropna().str.lower().value_counts()
    if not common_reasons.empty:
        top_reason = common_reasons.idxmax()
        reason_count = common_reasons.max()
        messages.append(f"📝 أكثر سبب تكرر في الزيارات هو: '{top_reason}' ({reason_count} مرة).")

    # تنبيه لو تم إدخال عرض غريب أو جديد
    rare_reasons = common_reasons[common_reasons == 1]
    if len(rare_reasons) > 0:
        messages.append(f"⚠️ تم تسجيل {len(rare_reasons)} عرض غير معتاد (ظهر مرة واحدة فقط).")

    return " | ".join(messages)
