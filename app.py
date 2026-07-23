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

@app.route("/appointments/<int:patient_id>")
def doctor_appointments(patient_id):
    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    patient = Patient.query.get_or_404(patient_id)

    return render_template(
        "appointments.html",
        patient=patient,
        appointments=appointments
    )


@app.route("/book-appointment", methods=["GET","POST"])
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


@app.route("/health-recommendations")
def health_recommendations():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    return render_template("health_recommendations.html")


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

        login = request.form.get("login")
        password = request.form.get("password")

        user = User.query.filter(
            ((User.username == login) | (User.email == login))
            & (User.role == "doctor")
        ).first()

        print("Login entered:", login)
        print("User found:", user)

        if user and user.password == password:
            session["logged_in"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"]= user.full_name
            session["role"] = user.role.lower()

            flash(f"Welcome back, Dr. {user.full_name}!", "success")
            return redirect(url_for("doctor_dashboard"))

        flash("Invalid username/email or password.", "danger")

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

    today = datetime.today().date()

    appointments_list = Appointment.query.all()

    todays_count = Appointment.query.filter_by(
        appointment_date=today
    ).count()

    completed_visits = Appointment.query.filter_by(status="Completed").count()

    pending_visits = Appointment.query.filter_by(status="Pending").count()

    return render_template(
        "doctor_dashboard.html",
        appointments=appointments_list,
        todays_count=todays_count,
        completed_count=completed_visits,
        pending_count=pending_visits,
        doctor_name=session.get("full_name", "Doctor")
    )


# PATIENT RECORDS
@app.route("/patient-records")
def patient_records():
    patients = Patient.query.all()
    for p in patients:
        print("ID:",p.id,"Name:",p.full_name)
    return render_template("patient_records.html", patients=patients)


@app.route("/patient-records/<int:patient_id>")
def patient_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template("patient_details.html", patient=patient)

#Doctor register
@app.route("/doctor-register", methods=["GET", "POST"])
def doctor_register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check password
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("doctor_register"))

        # Check username
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("doctor_register"))

        # Check email
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("doctor_register"))

        # Create doctor
        doctor = User(
            full_name=full_name,
            username=username,
            email=email,
            password=password,
            role="doctor"
        )

        db.session.add(doctor)
        db.session.commit()
        print("Doctor Registered:")
        print(doctor.username, doctor.email, doctor.role)

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("doctor_login"))

    return render_template("doctor_register.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":

        contact = request.form["contact"]

        user = User.query.filter(
            ((User.email == contact) | (User.username == contact))
            & (User.role == "doctor")
        ).first()

        if user:
            session["reset_user_id"] = user.id
            return redirect(url_for("verify_otp"))

        else:
            return "Doctor account not found"

    return render_template("forgot-password.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        otp = request.form["otp"]

        # Demo OTP verification
        if otp == "123456":

            return redirect(url_for("reset_password"))

        else:
            return "Invalid OTP"

    return render_template("verify_otp.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if request.method == "POST":

        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            return "Passwords do not match"

        user_id = session.get("reset_user_id")

        user = User.query.get(user_id)

        user.password = new_password

        db.session.commit()

        return redirect(url_for("password_success"))

    return render_template("reset_password.html")

@app.route("/password-success")
def password_success():

    return render_template("password_success.html")

@app.route("/prescriptions", methods=["GET", "POST"])
def prescriptions():
    if "role" not in session or session.get("role") != "doctor":
        flash("Please login as doctor.", "danger")
        return redirect(url_for("doctor_login"))

    if request.method == "POST":
        new_prescription = Prescription(
            patient_name=request.form.get("patient_name"),
            medicine_name=request.form.get("medicine_name"),
            dosage=request.form.get("dosage"),
            doctor_name=request.form.get("doctor_name"),
            status="Pending"
        )

        db.session.add(new_prescription)
        db.session.commit()

        flash("Prescription saved successfully.", "success")
        return redirect(url_for("prescriptions"))

    data = Prescription.query.all()
    return render_template("prescriptions.html", prescriptions=data)
# PRESCRIPTION
@app.route("/prescribe/<int:appointment_id>", methods=["POST"])
def prescribe(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    prescriptions_text = request.form.get("prescriptions")
    medicine_name = request.form.get("medicine_name") or prescriptions_text

    if prescriptions_text:
        appointment.prescription = prescriptions_text
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

@app.route("/appointment-status/<int:appointment_id>/<status>", methods=["POST"])
def update_appointment_status(appointment_id, status):
    appointment = Appointment.query.get_or_404(appointment_id)

    if status in ["Accepted", "Declined", "Completed", "Pending"]:
        appointment.status = status
        db.session.commit()
        flash(f"Appointment marked as {status}.", "success")

    return redirect(url_for("doctor_dashboard"))

# HOSPITAL DASHBOARD
@app.route("/hospital-dashboard")
def hospital_dashboard():
    wards_list = Ward.query.all()
    total_beds = sum(w.total_beds for w in wards_list if w.total_beds)
    occupied_beds = sum(w.occupied_beds for w in wards_list if w.occupied_beds)

    occupancy = int((occupied_beds / total_beds) * 100) if total_beds > 0 else 0
    icu = Ward.query.filter(Ward.name.ilike("%icu%")).first()
    icu_capacity = 0
    if icu and icu.total_beds:
        icu_capacity=int(
            (icu.occupied_beds/icu.total_beds)*100
        )

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

@app.route("/admin-settings")
def admin_settings():
    return render_template("admin_settings.html")


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
    if "role" not in session or session.get("role") != "doctor":
        flash("Please login as doctor.", "danger")
        return redirect(url_for("doctor_login"))

    appointments = Appointment.query.all()
    for a in appointments:
        print(
            a.patient_name,
            a.age,
            a.gender,
            a.symptoms,
            a.time,
            a.status,
        )

    pending_count = Appointment.query.filter_by(status="Pending").count()
    accepted_count = Appointment.query.filter_by(status="Accepted").count()

    return render_template(
        "doctor_appointements.html",
        appointments=appointments,
        pending_count=pending_count,
        accepted_count=accepted_count
    )

@app.route("/emergency-cases")
def emergency_cases():
    return render_template("emergency_cases.html")


@app.route("/system-nodes")
def system_nodes():
    return render_template("system_nodes.html")


@app.route("/audit-logs")
def audit_logs():
    return render_template("audit_logs.html")

@app.route("/doctor-logout")
def doctor_logout():

    session.clear()

    flash("You have been logged out successfully.", "success")

    return redirect(url_for("doctor_login"))

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