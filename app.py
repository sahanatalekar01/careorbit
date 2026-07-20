import os
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash
)

from werkzeug.utils import secure_filename

from models import (
    db,
    Patient,
    Appointment,
    Report,
    User,
    Prescription,
    LabTest,
    AmbulanceUnit,
    Notification,
    Ward,
    Medicine
)


app = Flask(__name__)


# CONFIGURATION
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "careorbit.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "careorbit_secret_key_123"

UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# DATABASE INITIALIZATION
db.init_app(app)

with app.app_context():
    db.create_all()


# IMAGE UPLOAD SETTINGS
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# HOME
@app.route("/")
def home():
    return render_template("index.html")


# PATIENT REGISTER
@app.route("/patient-register", methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        blood_group = request.form.get("blood_group")
        address = request.form.get("address")
        medical_history = request.form.get("medical_history")

        existing = Patient.query.filter_by(email=email).first()
        if existing:
            return "Email already registered."

        patient = Patient(
            full_name=full_name,
            email=email,
            password=password,
            age=int(age) if age and age.isdigit() else 0,
            gender=gender,
            phone=phone,
            blood_group=blood_group,
            address=address,
            medical_history=medical_history
        )
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for("patient_login"))

    return render_template("patient_register.html")


# PATIENT LOGIN
@app.route("/patient-login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        patient = Patient.query.filter_by(email=email, password=password).first()
        if patient:
            session["patient_id"] = patient.id
            session["patient_name"] = patient.full_name
            return redirect(url_for("patient_dashboard"))

        return "Invalid Email or Password"

    return render_template("patient_login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# PATIENT DASHBOARD
@app.route("/patient-dashboard")
def patient_dashboard():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    return render_template("patient_dashboard.html", patient_name=session.get("patient_name", "Patient"))


# SYMPTOM ANALYSIS
@app.route("/symptom-analysis")
def symptom_analysis():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    return render_template("symptom_analysis.html")


@app.route("/patient-results")
def patient_results():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    return render_template("result.html")


# AI ANALYSIS
@app.route("/analyze", methods=["POST"])
def analyze():
    if "patient_id" not in session:
        return jsonify({"status": "error", "message": "Please login first."}), 401

    symptoms = request.form.get("symptoms", "").strip()
    if symptoms == "":
        return jsonify({"status": "error", "message": "Please enter symptoms."})

    uploaded_image = None
    if "image" in request.files:
        image = request.files["image"]
        if image.filename != "" and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            uploaded_image = filename

    symptoms_lower = symptoms.lower()
    risk = "Low"
    recommendation = "Drink plenty of water and take proper rest."

    if "fever" in symptoms_lower:
        risk = "Moderate"
        recommendation = "Monitor your temperature and consult a doctor if fever continues."

    if "chest pain" in symptoms_lower or "difficulty breathing" in symptoms_lower:
        risk = "High"
        recommendation = "Seek immediate medical attention."

    return jsonify({
        "status": "success",
        "symptoms": symptoms,
        "risk": risk,
        "recommendation": recommendation,
        "uploaded_image": uploaded_image
    })


# APPOINTMENT
@app.route("/appointment")
def appointment():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    appointments = Appointment.query.filter_by(patient_id=session["patient_id"]).all()
    return render_template("appointment.html", appointments=appointments)


@app.route("/book-appointment", methods=["POST"])
def book_appointment():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient = db.session.get(Patient, session["patient_id"])
    appt_date_str = request.form.get("appointment_date")
    appointment_date = None
    if appt_date_str:
        try:
            appointment_date = datetime.strptime(appt_date_str, "%Y-%m-%d").date()
        except ValueError:
            appointment_date = datetime.today().date()

    time_val = request.form.get("appointment_time") or request.form.get("time")

    appointment = Appointment(
        patient_id=session["patient_id"],
        patient_name=patient.full_name if patient else request.form.get("patient_name"),
        age=patient.age if patient else (int(request.form.get("age")) if request.form.get("age") and request.form.get("age").isdigit() else None),
        gender=patient.gender if patient else request.form.get("gender"),
        symptoms=request.form.get("symptoms"),
        doctor_name=request.form.get("doctor_name"),
        appointment_date=appointment_date,
        appointment_time=time_val,
        time=time_val,
        status="Pending"
    )
    db.session.add(appointment)
    db.session.commit()
    return redirect(url_for("appointment"))


# REPORTS
@app.route("/reports")
def reports():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    patient_reports = Report.query.filter_by(patient_id=session["patient_id"]).all()
    return render_template("reports.html", reports=patient_reports)


@app.route("/health-recommendation")
def health_recommendation():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    return render_template("health_recommendation.html")


@app.route("/save-report", methods=["POST"])
def save_report():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    title = request.form.get("report_title") or request.form.get("title")
    details = request.form.get("report_details") or request.form.get("details")

    report = Report(
        patient_id=session["patient_id"],
        report_title=title,
        report_details=details,
        report_date=datetime.today().date()
    )
    db.session.add(report)
    db.session.commit()
    return redirect(url_for("reports"))


# DOCTOR LOGIN
@app.route("/doctor-login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and user.password == password and user.role.lower() == "doctor":
            session["logged_in"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role.lower()
            flash(f"Welcome back, Dr. {user.username}!", "success")
            return redirect(url_for("doctor_dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("doctor_login.html")


# ADD TEST DOCTOR
@app.route("/add-test-doctor")
def add_test_doctor():
    existing_doctor = User.query.filter_by(email="doctor@careorbit.com").first()
    if not existing_doctor:
        doctor = User(
            username="Dr. Smith",
            email="doctor@careorbit.com",
            password="password123",
            role="doctor"
        )
        db.session.add(doctor)
        db.session.commit()
        return "Test doctor created successfully! Email: doctor@careorbit.com, Password: password123"

    return "Test doctor already exists."


# DOCTOR DASHBOARD
@app.route("/doctor-dashboard")
def doctor_dashboard():
    if "role" not in session or session.get("role") != "doctor":
        flash("Please login as doctor.", "danger")
        return redirect(url_for("doctor_login"))

    appointments_list = Appointment.query.all()
    completed_visits = Appointment.query.filter_by(status="Completed").count()
    pending_visits = Appointment.query.filter_by(status="Pending").count()

    return render_template(
        "doctor_dashboard.html",
        appointments=appointments_list,
        todays_count=len(appointments_list),
        completed_count=completed_visits,
        pending_count=pending_visits
    )


# PATIENT RECORDS
@app.route("/patient-records")
def patient_records():
    patients = Patient.query.all()
    return render_template("patient_records.html", patients=patients)


@app.route("/patient-records/<int:patient_id>")
def patient_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template("patient_details.html", patient=patient)


# PRESCRIPTION
@app.route("/prescribe/<int:appointment_id>", methods=["POST"])
def prescribe(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    prescription_text = request.form.get("prescription")
    medicine_name = request.form.get("medicine_name") or prescription_text

    if prescription_text:
        appointment.prescription = prescription_text
        appointment.status = "Completed"

        patient_name = appointment.patient_name
        if not patient_name and appointment.patient_id:
            p = db.session.get(Patient, appointment.patient_id)
            if p:
                patient_name = p.full_name

        doctor_name = session.get("username") or appointment.doctor_name or "Doctor"

        new_prescription = Prescription(
            patient_name=patient_name or "Patient",
            medicine_name=medicine_name,
            dosage=request.form.get("dosage", "As directed"),
            doctor_name=doctor_name,
            status="Pending"
        )
        db.session.add(new_prescription)
        db.session.commit()
        flash("Prescription saved successfully.", "success")

    return redirect(url_for("doctor_dashboard"))


# HOSPITAL DASHBOARD
@app.route("/hospital-dashboard")
def hospital_dashboard():
    wards_list = Ward.query.all()
    total_beds = sum(w.total_beds for w in wards_list if w.total_beds)
    occupied_beds = sum(w.occupied_beds for w in wards_list if w.occupied_beds)

    occupancy = int((occupied_beds / total_beds) * 100) if total_beds > 0 else 0
    icu = Ward.query.filter(Ward.name.ilike("%icu%")).first()
    icu_capacity = int((icu.occupied_beds / icu.total_beds) * 100) if icu and icu.total_beds and icu.total_beds > 0 else 0

    return render_template(
        "hospital_dashboard.html",
        wards=wards_list,
        bed_occupancy=occupancy,
        icu_capacity=icu_capacity,
        total_beds=total_beds,
        occupied_beds=occupied_beds,
        icu_ward=icu
    )


# PHARMACY DASHBOARD
@app.route("/pharmacy-dashboard")
def pharmacy_dashboard():
    medicines = Medicine.query.all()
    total_products = len(medicines)
    low_stock = Medicine.query.filter(Medicine.stock <= 20).count()
    total_stock_val = sum(m.stock for m in medicines if m.stock)

    return render_template(
        "pharmacy_dashboard.html",
        medicines=medicines,
        total_products=total_products,
        low_stock_count=low_stock,
        pending_orders=12,
        total_stock=total_stock_val
    )


@app.route("/dispense-medication/<int:appointment_id>", methods=["POST"])
def dispense_medication(appointment_id):
    appointment_rec = Appointment.query.get_or_404(appointment_id)
    appointment_rec.status = "Dispensed"
    db.session.commit()
    flash("Medicine dispensed successfully.", "success")
    return redirect(url_for("pharmacy_dashboard"))


# LABORATORY DASHBOARD
@app.route("/laboratory-dashboard")
def laboratory_dashboard():
    tests = LabTest.query.all()
    return render_template(
        "laboratory_dashboard.html",
        lab_tests=tests,
        total_tests=len(tests),
        pending_tests=LabTest.query.filter_by(status="Pending").count(),
        processing_tests=LabTest.query.filter_by(status="Processing").count()
    )


# AMBULANCE DASHBOARD
@app.route("/ambulance-dashboard")
def ambulance_dashboard():
    ambulances = AmbulanceUnit.query.all()
    return render_template(
        "ambulance_dashboard.html",
        ambulances=ambulances,
        total_fleet=len(ambulances),
        available_units=AmbulanceUnit.query.filter_by(status="Available").count(),
        on_mission=AmbulanceUnit.query.filter_by(status="On Mission").count()
    )


# ADMIN DASHBOARD
@app.route("/admin-dashboard")
def admin_dashboard():
    total_appointments = Appointment.query.count()
    completed_visits = Appointment.query.filter_by(status="Completed").count()
    users = User.query.count()
    notifications = Notification.query.all()

    return render_template(
        "admin_dashboard.html",
        total_appointments=total_appointments,
        completed_visits=completed_visits,
        user_count=users,
        notice_count=len(notifications),
        records=notifications
    )


# USER MANAGEMENT
@app.route("/user-management")
def user_management():
    users = User.query.all()
    return render_template("user_management.html", users=users)


@app.route("/admin/search")
def admin_search():
    query = request.args.get("query", "")
    if query:
        results = User.query.filter((User.username.like(f"%{query}%")) | (User.email.like(f"%{query}%"))).all()
    else:
        results = []
    return render_template("user_management.html", users=results)


@app.route("/delete-user/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("user_management"))


# EDIT USER
@app.route("/edit-user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        user.username = request.form.get("username")
        user.email = request.form.get("email")
        user.role = request.form.get("role")
        db.session.commit()
        return redirect(url_for("user_management"))

    return render_template("edit_user.html", user=user)


# EXTRA PAGES
@app.route("/appointments")
def appointments():
    return render_template("appointments.html")


@app.route("/prescriptions")
def prescriptions():
    data = Prescription.query.all()
    return render_template("prescriptions.html", prescriptions=data)


@app.route("/emergency-cases")
def emergency_cases():
    return render_template("emergency_cases.html")


@app.route("/system-nodes")
def system_nodes():
    return render_template("system_nodes.html")


@app.route("/audit-logs")
def audit_logs():
    return render_template("audit_logs.html")


# ERROR HANDLERS
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500


# RUN APPLICATION
if __name__ == "__main__":
    app.run(debug=True)