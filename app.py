from flask import session, flash

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response
from functools import wraps
import psycopg2
#import sqlite3
import os
from io import BytesIO
from werkzeug.utils import secure_filename

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader

from bidi.algorithm import get_display
import arabic_reshaper

import urllib.parse


import sqlite3
import agent
import os
from datetime import datetime



app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = 'your_secret_key_here'  # استخدم قيمة عشوائية حقيقية لاحقًا

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="clinic_db",
        user="clinic_user",
        password="clinic_pass"
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    #c.execute('''CREATE TABLE IF NOT EXISTS visits
    #             (id INTEGER PRIMARY KEY, name TEXT, date TEXT, reason TEXT)''')
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return render_template('unauthorized.html', page_title="غير مصرح بالدخول")

        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        date = request.form['date']
        reason = request.form['reason']
        image_file = request.files.get('image')
        image_filename = ''

        if image_file and image_file.filename != '' and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        c.execute("INSERT INTO visits (patient_id, date, reason, image) VALUES (%s, %s, %s, %s)",
                  (patient_id, date, reason, image_filename))
        conn.commit()

    # استعلام الزيارات مع أسماء المرضى
    c.execute("""
        SELECT visits.patient_id, patients.name, visits.date, visits.reason, visits.image
        FROM visits
        JOIN patients ON visits.patient_id = patients.id
        ORDER BY visits.date DESC
    """)
    visits = c.fetchall()

    # استعلام أسماء المرضى للقائمة
    c.execute("SELECT id, name FROM patients")
    patients = c.fetchall()

    conn.close()

    analysis = agent.analyze_data()
    return render_template('index.html', visits=visits, patients=patients, analysis=analysis,page_title="نظام العيادة - القائمة الرئيسية")


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

from bidi.algorithm import get_display
import arabic_reshaper
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFont

@app.route('/download-pdf')
@login_required
def download_pdf():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, date, reason FROM visits")
    visits = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # تحميل الخط العربي
    font_path = "fonts/Amiri-Regular.ttf"  # أو المسار الصحيح للخط
    pdfmetrics.registerFont(TTFont("Arabic", font_path))
    p.setFont("Arabic", 14)

    y = height - 50
    title = arabic_reshaper.reshape("تقرير الزيارات")
    title = get_display(title)
    p.drawString(100, y, title)
    y -= 40

    for visit in visits:
        name, date, reason = visit
        line = f"{name} - {date} - {reason}"
        reshaped_line = arabic_reshaper.reshape(line)
        bidi_line = get_display(reshaped_line)
        p.drawString(50, y, bidi_line)
        y -= 25
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Arabic", 14)

    p.save()
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=report_ar.pdf'
    return response


@app.route('/patient-report/<int:patient_id>')
def patient_report(patient_id):
    conn = get_db_connection()
    c = conn.cursor()

    # احصل على اسم المريض
    c.execute("SELECT name FROM patients WHERE id = %s", (patient_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return "المريض غير موجود", 404

    name = result[0]

    # احصل على زيارات هذا المريض
    c.execute("SELECT date, reason, image  FROM visits WHERE patient_id = %s", (patient_id,))
    visits = c.fetchall()
    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # تحميل الخط العربي
    font_path = "fonts/Amiri-Regular.ttf"
    pdfmetrics.registerFont(TTFont("Arabic", font_path))
    p.setFont("Arabic", 14)

    y = height - 50
    title = arabic_reshaper.reshape(f"تقرير زيارات المريض: {name}")
    title = get_display(title)
    p.drawString(50, y, title)
    y -= 40

    for date, reason, image in visits:
        line = f"{date} - {reason}"
        reshaped = arabic_reshaper.reshape(line)
        bidi_line = get_display(reshaped)
        p.drawString(50, y, bidi_line)
        y -= 25

        # إذا كانت هناك صورة
        if image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image)
            if os.path.exists(image_path):
                try:
                    p.drawImage(image_path, 50, y - 100, width=200, preserveAspectRatio=True, mask='auto')
                    y -= 120  # المسافة بعد الصورة
                except Exception as e:
                    p.drawString(50, y, "(لم يتم تحميل الصورة)")
                    y -= 20

        if y < 150:
            p.showPage()
            p.setFont("Arabic", 14)
            y = height - 50

        line = f"{date} - {reason}"
        reshaped = arabic_reshaper.reshape(line)
        bidi_line = get_display(reshaped)
        p.drawString(50, y, bidi_line)
        y -= 25
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Arabic", 14)

    p.save()
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=report_{patient_id}.pdf'
    return response

@app.route('/patient/<int:patient_id>')
@login_required
def patient_details(patient_id):
    conn = get_db_connection()
    c = conn.cursor()

    # احصل على بيانات المريض
    c.execute("SELECT name FROM patients WHERE id = %s", (patient_id,))
    patient = c.fetchone()

    if not patient:
        conn.close()
        return "المريض غير موجود", 404

    # احصل على الزيارات المرتبطة بهذا المريض
    c.execute("SELECT date, reason, image FROM visits WHERE patient_id = %s ORDER BY date DESC", (patient_id,))
    visits = c.fetchall()
    conn.close()
    return render_template("patient_details.html", patient_name=patient[0], visits=visits, patient_id=patient_id, page_title=f"زيارات المريض: {patient[0]}")


@app.route('/patients', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_patients():
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        c.execute("INSERT INTO patients (name) VALUES (%s)", (name,))
        conn.commit()

    c.execute("SELECT id, name FROM patients ORDER BY name")
    patients = c.fetchall()
    conn.close()
    return render_template("patients.html", patients=patients, page_title="إدارة المرضى")

@app.route('/edit-patient/<int:patient_id>', methods=['POST'])
@login_required
@admin_required

def edit_patient(patient_id):
    new_name = request.form['new_name']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE patients SET name = %s WHERE id = %s", (new_name, patient_id))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_patients'))

@app.route('/delete-patient/<int:patient_id>', methods=['POST'])
@login_required
@admin_required

def delete_patient(patient_id):
    if session.get('role') != 'admin':
        return "غير مصرح لك بحذف المرضى", 403


    conn = get_db_connection()
    c = conn.cursor()

    # احذف زيارات المريض أولاً
    c.execute("DELETE FROM visits WHERE patient_id = %s", (patient_id,))

    # ثم احذف المريض
    c.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_patients'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, role FROM users WHERE username = %s AND password = %s", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = username
            session['role'] = user[1]
            return redirect(url_for('index'))
        else:
            error = 'اسم المستخدم أو كلمة المرور غير صحيحة'

    return render_template('login.html', error=error, page_title="تسجيل الدخول")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    message = ''
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        user_id = session['user_id']

        if new_password != confirm_password:
            message = '❌ كلمة المرور الجديدة وتأكيدها غير متطابقين'
        else:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE id = %s", (user_id,))
            user = c.fetchone()

            if user and user[0] == current_password:
                c.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, user_id))
                conn.commit()
                message = '✅ تم تغيير كلمة المرور بنجاح'
            else:
                message = '❌ كلمة المرور الحالية غير صحيحة'

            conn.close()

    return render_template('change_password.html', message=message, page_title="تغيير كلمة الدخول")

@app.route('/create-user', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            conn.commit()
            message = '✅ تم إنشاء المستخدم بنجاح'
        except sqlite3.IntegrityError:
            message = '❌ اسم المستخدم موجود بالفعل'
        conn.close()

    return render_template('create_user.html', message=message, page_title="إنشاء مستخدم جديد")




if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
