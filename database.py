import os
import psycopg2
from datetime import datetime
from psycopg2.extras import RealDictCursor

# الحصول على رابط قاعدة البيانات من المتغيرات البيئية
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """إنشاء جداول قاعدة البيانات في PostgreSQL"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # جدول المعامل
    cur.execute('''
        CREATE TABLE IF NOT EXISTS labs (
            lab_id SERIAL PRIMARY KEY,
            lab_name TEXT UNIQUE NOT NULL,
            lab_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول المستخدمين المسموح لهم
    cur.execute('''
        CREATE TABLE IF NOT EXISTS lab_users (
            user_id BIGINT PRIMARY KEY,
            lab_id INTEGER NOT NULL,
            lab_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lab_id) REFERENCES labs(lab_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول التقارير
    cur.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id SERIAL PRIMARY KEY,
            lab_id INTEGER NOT NULL,
            patient_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            doctor TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lab_id) REFERENCES labs(lab_id) ON DELETE CASCADE
        )
    ''')
    
    # جدول نتائج التحاليل
    cur.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            result_id SERIAL PRIMARY KEY,
            report_id INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            result_value TEXT NOT NULL,
            FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE
        )
    ''')
    
    # إنشاء فهارس للسرعة
    cur.execute('CREATE INDEX IF NOT EXISTS idx_lab_users_user_id ON lab_users(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_reports_lab_id ON reports(lab_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_test_results_report_id ON test_results(report_id)')
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ تم إنشاء جداول PostgreSQL بنجاح")
    
    # تأكد من وجود معمل المشرف
    ensure_admin_lab_exists()

def ensure_admin_lab_exists():
    """التأكد من وجود معمل المشرف"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # استخدم نفس البيانات من bot.py
    ADMIN_LAB_NAME = "Rajab"  # نفس الاسم
    ADMIN_PASSWORD = "2030"    # نفس كلمة السر
    
    # شوف إذا كان المعمل موجود
    cur.execute("SELECT lab_id FROM labs WHERE lab_name = %s", (ADMIN_LAB_NAME,))
    lab = cur.fetchone()
    
    if not lab:
        # أنشئ المعمل
        cur.execute("""
            INSERT INTO labs (lab_name, lab_password) 
            VALUES (%s, %s)
            RETURNING lab_id
        """, (ADMIN_LAB_NAME, ADMIN_PASSWORD))
        lab_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ تم إنشاء معمل {ADMIN_LAB_NAME}")
        print(f"🔑 كلمة السر: {ADMIN_PASSWORD}")
    else:
        lab_id = lab[0]
    
    cur.close()
    conn.close()
    return lab_id

# ================= دوال المعامل =================

def register_lab(lab_name, lab_password):
    """تسجيل معمل جديد (للمشرف فقط)"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO labs (lab_name, lab_password) 
            VALUES (%s, %s)
            RETURNING lab_id
        """, (lab_name, lab_password))
        lab_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return lab_id
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return None

def add_new_lab(lab_name, lab_password):
    """إضافة معمل جديد (للمشرف فقط)"""
    return register_lab(lab_name, lab_password)

def verify_lab(lab_name, lab_password):
    """التحقق من صحة بيانات المعمل"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT lab_id, lab_name FROM labs 
        WHERE lab_name = %s AND lab_password = %s
    """, (lab_name, lab_password))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result if result else None

def add_lab_user(user_id, lab_id, lab_name):
    """إضافة مستخدم لمعمل"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO lab_users (user_id, lab_id, lab_name) 
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET lab_id = EXCLUDED.lab_id, lab_name = EXCLUDED.lab_name
        """, (user_id, lab_id, lab_name))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return False

def get_lab_by_user(user_id):
    """الحصول على معمل المستخدم"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT lab_id, lab_name FROM lab_users 
        WHERE user_id = %s
    """, (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result if result else None

def get_lab_name(user_id):
    """الحصول على اسم المعمل (للتوافق مع الكود القديم)"""
    lab_info = get_lab_by_user(user_id)
    return lab_info[1] if lab_info else None

def get_all_labs():
    """الحصول على جميع المعامل (للمشرف فقط)"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT lab_id, lab_name, lab_password, created_at 
        FROM labs 
        ORDER BY lab_id
    """)
    labs = cur.fetchall()
    cur.close()
    conn.close()
    return labs

def delete_lab(lab_id):
    """حذف معمل (للمشرف فقط)"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM labs WHERE lab_id = %s", (lab_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return False

# ================= دوال التقارير =================

def create_report(user_id, patient_data):
    """إنشاء تقرير جديد"""
    lab_info = get_lab_by_user(user_id)
    if not lab_info:
        return None
    
    lab_id = lab_info[0]
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO reports (lab_id, patient_name, age, gender, doctor)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING report_id
    ''', (lab_id, patient_data['name'], patient_data['age'], 
          patient_data['gender'], patient_data['doctor']))
    report_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return report_id

def add_test_to_report(report_id, test_name, result_value):
    """إضافة تحليل للتقرير"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO test_results (report_id, test_name, result_value)
        VALUES (%s, %s, %s)
    ''', (report_id, test_name, result_value))
    conn.commit()
    cur.close()
    conn.close()

def get_report_details(report_id):
    """الحصول على تفاصيل التقرير"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # معلومات التقرير مع اسم المعمل
    cur.execute('''
        SELECT r.*, l.lab_name 
        FROM reports r
        JOIN labs l ON r.lab_id = l.lab_id
        WHERE r.report_id = %s
    ''', (report_id,))
    report = cur.fetchone()
    
    if not report:
        cur.close()
        conn.close()
        return None
    
    # التحاليل
    cur.execute('''
        SELECT test_name, result_value 
        FROM test_results 
        WHERE report_id = %s
    ''', (report_id,))
    tests = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # تحويل RealDictRow إلى dict عادي
    report_dict = dict(report)
    report_dict['tests'] = [dict(t) for t in tests]
    
    return report_dict

def get_report_with_normal_ranges(report_id):
    """الحصول على التقرير مع المدى الطبيعي"""
    try:
        from tests_data import get_normal_range, get_test_unit
    except ImportError:
        # لو ملف tests_data مش موجود
        def get_normal_range(*args): return "غير محدد"
        def get_test_unit(*args): return ""
    
    report = get_report_details(report_id)
    if not report:
        return None
    
    # إضافة المدى الطبيعي لكل تحليل
    for test in report['tests']:
        test['unit'] = get_test_unit(test['test_name'])
        test['normal_range'] = get_normal_range(test['test_name'], report.get('gender', 'ذكر'))
    
    return report
def save_lab_details(lab_id, details):
    """
    دالة لحفظ تفاصيل المختبر - مؤقتة لحل مشكلة الاستيراد
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # هنا ضع الكود المناسب لحفظ التفاصيل
        # هذا مجرد هيكل مؤقت
        cursor.execute("""
            UPDATE labs SET details = ? WHERE id = ?
        """, (details, lab_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving lab details: {e}")
        return False
    finally:
        conn.close()