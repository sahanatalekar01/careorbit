import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
from models import (
    db, Patient, Appointment, Report, User, Prescription, LabTest, 
    AmbulanceUnit, Notification, Ward, Medicine, AuditLog, Analyzer
)

app = Flask(__name__)

# CONFIGURATION
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "careorbit.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "careorbit_secret_key_123"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)

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

# HELPER FUNCTION FOR PROFILE CHECK
def is_profile_complete(patient):
    """Checks if required profile fields are completed for a patient."""
    if not patient:
        return False
    
    contact = getattr(patient, 'emergency_contact', None) or getattr(patient, 'phone', None)
    
    required_fields = [
        patient.age,
        patient.gender,
        patient.blood_group,
        patient.address,
        contact,
        patient.medical_history
    ]
    return all(field is not None and str(field).strip() != "" for field in required_fields)


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
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("patient_register"))

        if Patient.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("patient_register"))

        age_input = request.form.get("age")
        age_val = int(age_input) if age_input and age_input.isdigit() else None

        phone_val = request.form.get("emergency_contact") or request.form.get("phone")

        patient_kwargs = {
            "full_name": full_name,
            "email": email,
            "password": password,
            "age": age_val,
            "gender": request.form.get("gender"),
            "blood_group": request.form.get("blood_group"),
            "address": request.form.get("address"),
            "medical_history": request.form.get("medical_history")
        }
        
        if hasattr(Patient, 'emergency_contact'):
            patient_kwargs['emergency_contact'] = phone_val
        if hasattr(Patient, 'phone'):
            patient_kwargs['phone'] = phone_val

        patient = Patient(**patient_kwargs)
        db.session.add(patient)
        db.session.commit()
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("patient_login"))
        
    return render_template("patient_register.html")


# PATIENT LOGIN
@app.route("/patient-login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = request.form.get("remember")

        patient = Patient.query.filter_by(email=email, password=password).first()

        if patient:
            session.permanent = True if remember else False
            session["patient_id"] = patient.id
            session["patient_name"] = patient.full_name
            flash("Login successful!", "success")

            if not is_profile_complete(patient):
                flash("Please complete your profile information to continue.", "info")
                return redirect(url_for("complete_profile"))

            return redirect(url_for("patient_dashboard"))

        flash("Invalid Email or Password.", "danger")
        return redirect(url_for("patient_login"))
        
    return render_template("patient_login.html")


# COMPLETE PROFILE
@app.route("/complete-profile", methods=["GET", "POST"])
def complete_profile():
    if "patient_id" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("patient_login"))
    
    patient = Patient.query.get_or_404(session["patient_id"])

    if request.method == "POST":
        age_val = request.form.get("age")
        patient.age = int(age_val) if age_val and age_val.isdigit() else patient.age
        patient.gender = request.form.get("gender")
        patient.blood_group = request.form.get("blood_group")
        patient.address = request.form.get("address")
        patient.medical_history = request.form.get("medical_history")

        contact_val = request.form.get("emergency_contact") or request.form.get("phone")
        if hasattr(patient, 'emergency_contact'):
            patient.emergency_contact = contact_val
        if hasattr(patient, 'phone'):
            patient.phone = contact_val

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("patient_dashboard"))

    return render_template("complete_profile.html", patient=patient)


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# PATIENT PRESCRIPTIONS
@app.route("/patient-prescriptions")
def patient_prescriptions():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    prescriptions = Prescription.query.filter_by(patient_name=session.get("patient_name")).all()
    return render_template("patient_prescriptions.html", prescriptions=prescriptions, patient_name=session.get("patient_name"))


# PATIENT DASHBOARD
@app.route("/patient-dashboard")
def patient_dashboard():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    patient = Patient.query.get_or_404(session["patient_id"])
    
    if not is_profile_complete(patient):
        flash("Please complete your profile details first.", "warning")
        return redirect(url_for("complete_profile"))

    return render_template("patient_dashboard.html", patient_name=session.get("patient_name", "Patient"), patient=patient)



# ============================================================
# PATIENT AMBULANCE BOOKING
# ============================================================

@app.route("/book-ambulance", methods=["POST"])
def book_ambulance():
    from models import AmbulanceBooking

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient = Patient.query.get_or_404(session["patient_id"])

    pickup_location = request.form.get("pickup_location", "").strip()
    emergency_category = request.form.get(
        "emergency_category",
        "Emergency"
    ).strip()

    destination = request.form.get(
        "destination",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    pickup_latitude = request.form.get("pickup_latitude")
    pickup_longitude = request.form.get("pickup_longitude")

    if not pickup_location:
        flash("Please enter your pickup location.", "warning")
        return redirect(url_for("patient_dashboard"))

    # Find the first available ambulance
    ambulance = AmbulanceUnit.query.filter_by(
        status="Available"
    ).first()

    if not ambulance:
        flash(
            "No ambulance is currently available. Please try again shortly.",
            "warning"
        )
        return redirect(url_for("patient_dashboard"))

    # Convert coordinates safely
    lat = None
    lng = None

    try:
        if pickup_latitude:
            lat = float(pickup_latitude)

        if pickup_longitude:
            lng = float(pickup_longitude)
    except (ValueError, TypeError):
        lat = None
        lng = None

    # Create booking
    booking = AmbulanceBooking(
        patient_id=patient.id,
        ambulance_id=ambulance.id,
        emergency_category=emergency_category,
        description=description,
        pickup_location=pickup_location,
        pickup_latitude=lat,
        pickup_longitude=lng,
        destination=destination or None,
        status="Accepted",
        accepted_at=datetime.utcnow()
    )

    # Update ambulance
    ambulance.status = "On Mission"
    ambulance.current_destination = (
        destination if destination else pickup_location
    )

    if lat is not None and lng is not None:
        ambulance.latitude = lat
        ambulance.longitude = lng

    db.session.add(booking)
    db.session.commit()

    flash(
        f"Ambulance {ambulance.vehicle_number} has been assigned successfully.",
        "success"
    )

    return redirect(url_for("patient_dashboard"))

# PATIENT PROFILE
@app.route("/patient-profile")
def patient_profile():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    patient = Patient.query.get(session["patient_id"])
    return render_template("patient_profile.html", patient=patient)


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
    risk, recommendation = "Low", "Drink plenty of water and take proper rest."

    if "fever" in symptoms_lower:
        risk, recommendation = "Moderate", "Monitor your temperature and consult a doctor if fever continues."
    if "chest pain" in symptoms_lower or "difficulty breathing" in symptoms_lower:
        risk, recommendation = "High", "Seek immediate medical attention."

    return jsonify({
        "status": "success", "symptoms": symptoms, "risk": risk,
        "recommendation": recommendation, "uploaded_image": uploaded_image
    })


# APPOINTMENT
@app.route("/appointment")
def appointment():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    appointments = Appointment.query.filter_by(patient_id=session["patient_id"]).all()
    return render_template("appointment.html", appointments=appointments)


@app.route("/doctor-appointments-list")
def doctor_appointments_list():
    appointments = Appointment.query.all()
    return render_template("doctor_appointment.html", appointments=appointments)


@app.route("/appointments/<int:patient_id>")
def doctor_appointments(patient_id):
    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    patient = Patient.query.get_or_404(patient_id)
    pending_count = Appointment.query.filter_by(patient_id=patient_id, status="Pending").count()
    accepted_count = Appointment.query.filter_by(patient_id=patient_id, status="Accepted").count()
    return render_template(
        "doctor_appointment.html", patient=patient, appointments=appointments,
        pending_count=pending_count, accepted_count=accepted_count
    )


@app.route("/book-appointment", methods=["GET", "POST"])
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
        patient_name=(patient.full_name if patient else request.form.get("patient_name")),
        age=(patient.age if patient else (int(request.form.get("age")) if request.form.get("age") and request.form.get("age").isdigit() else None)),
        gender=(patient.gender if patient else request.form.get("gender")),
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


# REPORTS & LABORATORY
@app.route("/reports")
def reports():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    patient_reports = Report.query.filter_by(patient_id=session["patient_id"]).all()
    return render_template("reports.html", reports=patient_reports)


@app.route("/laboratory-dashboard")
def laboratory_dashboard():
    tests = LabTest.query.all()
    return render_template("laboratory_dashboard.html", tests=tests)


@app.route("/patient-lab-reports")
def patient_lab_reports():
    if "patient_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("patient_login"))
    patient = Patient.query.get_or_404(session["patient_id"])
    tests = LabTest.query.filter_by(patient_name=patient.full_name).all()
    return render_template("patient_lab_reports.html", patient=patient, tests=tests)


@app.route("/update-lab-status/<int:id>/<status>")
def update_lab_status(id, status):
    test = LabTest.query.get_or_404(id)
    test.status = status
    if status == "Completed":
        notification = Notification(
            target_audience=test.patient_name, severity="Success",
            message=f'Your "{test.test_name}" test has been completed.', is_active=True
        )
        db.session.add(notification)
    db.session.commit()
    flash("Lab test status updated successfully.", "success")
    return redirect(url_for("laboratory_dashboard"))


@app.route("/health-recommendations")      
def health_recommendations():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    return render_template("health_recommendations.html")


@app.route("/view-lab-report/<int:id>")
def view_lab_report(id):
    test = LabTest.query.get_or_404(id)
    return render_template("view_lab_report.html", test=test)


@app.route("/save-report", methods=["POST"])
def save_report():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    title = request.form.get("report_title") or request.form.get("title")
    details = request.form.get("report_details") or request.form.get("details")
    report = Report(
        patient_id=session["patient_id"], report_title=title,
        report_details=details, report_date=datetime.today().date()
    )
    db.session.add(report)
    db.session.commit()
    return redirect(url_for("reports"))


@app.route("/complete-lab-report/<int:id>", methods=["GET", "POST"])
def complete_lab_report(id):
    test = LabTest.query.get_or_404(id)
    if request.method == "POST":
        test.result = request.form.get("result")
        test.unit = request.form.get("unit")
        test.reference_range = request.form.get("reference_range")
        test.interpretation = request.form.get("interpretation")
        test.remarks = request.form.get("remarks")
        test.verified_by = request.form.get("verified_by")
        test.status = "Completed"
        test.completed_date = datetime.now().strftime("%d-%m-%Y")

        notification = Notification(
            target_audience=test.patient_name, severity="Success",
            message=f"Your {test.test_name} test has been completed. Click 'View Report' to see your laboratory report.",
            is_active=True
        )
        db.session.add(notification)
        db.session.commit()
        flash("Laboratory report saved successfully.", "success")
        return redirect(url_for("laboratory_dashboard"))
    return render_template("complete_lab_report.html", test=test)


# ADMIN & USER MANAGEMENT
@app.route("/admin-register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        flash("Admin registration feature is processed.", "success")
        return redirect(url_for("home"))
    return render_template("user_management.html")


@app.route("/user-management")
def user_management():
    users = User.query.all()
    return render_template("user_management.html", users=users)


# DOCTOR LOGIN & DASHBOARD
@app.route("/doctor-login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")
        remember = request.form.get("remember")

        user = User.query.filter(((User.username == login) | (User.email == login)) & (User.role == "doctor")).first()

        if user and user.password == password:
            if user.verification_status == "Pending":
                flash("Your account is under admin verification. Please wait until it is approved.", "warning")
                return redirect(url_for("doctor_login"))

            if user.verification_status == "Rejected":
                flash(f"Your account has been rejected. {user.admin_remark or ''}", "danger")
                return redirect(url_for("doctor_login"))

            session.permanent = True if remember else False
            session["logged_in"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"] = user.full_name
            session["role"] = user.role.lower()
            flash(f"Welcome back, Dr. {user.full_name}!", "success")
            return redirect(url_for("doctor_dashboard"))

        flash("Invalid username/email or password.", "danger")
        return redirect(url_for("doctor_login"))

    return render_template("doctor_login.html")


@app.route("/doctor-dashboard")
def doctor_dashboard():
    if "role" not in session or session.get("role") != "doctor":
        flash("Please login as doctor.", "danger")
        return redirect(url_for("doctor_login"))

    today = datetime.today().date()
    appointments_list = Appointment.query.all()
    todays_count = Appointment.query.filter_by(appointment_date=today).count()
    completed_visits = Appointment.query.filter_by(status="Completed").count()
    pending_visits = Appointment.query.filter_by(status="Pending").count()

    doctor = User.query.get(session["user_id"])

    return render_template(
        "doctor_dashboard.html",
        appointments=appointments_list,
        todays_count=todays_count,
        completed_count=completed_visits,
        pending_count=pending_visits,
        doctor_name=doctor.full_name,
        doctor=doctor
    )


# PATIENT RECORDS
@app.route("/patient-records")
def patient_records():
    search = request.args.get("search", "").strip()

    if search:
        patients = Patient.query.filter(Patient.full_name.ilike(f"%{search}%")).all()
        if not patients and search.isdigit():
            patient = Patient.query.get(int(search))
            if patient:
                patients = [patient]
    else:
        patients = Patient.query.all()

    return render_template("patient_records.html", patients=patients, search=search)


@app.route("/patient-records/<int:patient_id>")
def patient_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointment = Appointment.query.filter_by(patient_id=patient_id).first()
    return render_template("patient_details.html", patient=patient, appointment=appointment)


@app.route("/patient-notifications")
def patient_notifications():
    if "patient_name" not in session:
        return redirect(url_for("patient_login"))
    notifications = Notification.query.filter_by(
        target_audience=session["patient_name"], is_active=True
    ).order_by(Notification.timestamp.desc()).all()
    return render_template("patient_notifications.html", notifications=notifications)


# DOCTOR REGISTER & MANAGEMENT
@app.route("/doctor-register", methods=["GET", "POST"])
def doctor_register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        email = request.form["email"]
        phone = request.form["phone"]
        qualification = request.form["qualification"]
        specialization = request.form["specialization"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        profile_photo = request.files.get("profile_photo")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("doctor_register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("doctor_register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("doctor_register"))

        profile_photo_filename = None
        if profile_photo and profile_photo.filename:
            profile_photo_filename = secure_filename(profile_photo.filename)
            profile_photo.save(os.path.join(app.config["UPLOAD_FOLDER"], profile_photo_filename))

        doctor = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone,
            qualification=qualification,
            specialization=specialization,
            profile_photo=profile_photo_filename,
            password=password,
            role="doctor",
            status="Active",
            verification_status="Pending",
            admin_remark=None
        )

        db.session.add(doctor)
        db.session.commit()

        flash("Registration submitted successfully. Your account will be activated after admin verification.", "success")
        return redirect(url_for("doctor_login"))

    return render_template("doctor_register.html")


@app.route("/doctor-verification")
def doctor_verification():
    if "role" not in session or session["role"] != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctors = User.query.filter_by(role="doctor", verification_status="Pending").all()
    pending_doctors = User.query.filter_by(role="doctor", verification_status="Pending").count()
    approved_doctors = User.query.filter_by(role="doctor", verification_status="Approved").count()
    rejected_doctors = User.query.filter_by(role="doctor", verification_status="Rejected").count()

    return render_template(
        "doctor_verification.html",
        doctors=doctors,
        pending_doctors=pending_doctors,
        approved_doctors=approved_doctors,
        rejected_doctors=rejected_doctors
    )


@app.route("/approve-doctor/<int:doctor_id>")
def approve_doctor(doctor_id):
    if "role" not in session or session["role"] != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctor = User.query.get_or_404(doctor_id)
    doctor.verification_status = "Approved"
    doctor.status = "Active"
    doctor.admin_remark = None

    notification = Notification(
        target_audience="Doctor",
        severity="Success",
        message=f"Congratulations Dr. {doctor.full_name}! Your CareOrbit account has been approved by the admin.",
        is_active=True
    )

    db.session.add(notification)
    db.session.commit()

    flash("Doctor approved successfully.", "success")
    return redirect(url_for("doctor_verification"))


@app.route("/reject-doctor/<int:doctor_id>")
def reject_doctor(doctor_id):
    if "role" not in session or session["role"] != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctor = User.query.get_or_404(doctor_id)
    doctor.verification_status = "Rejected"
    doctor.status = "Inactive"
    doctor.admin_remark = "Verification rejected by administrator."

    notification = Notification(
        target_audience="doctor",
        severity="danger",
        message=f"Doctor verification rejected for {doctor.full_name}.",
        is_active=True
    )

    db.session.add(notification)
    db.session.commit()

    flash("Doctor rejected.", "warning")
    return redirect(url_for("doctor_verification"))


@app.route("/delete-user/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("user_management"))


@app.route("/edit-doctor-profile", methods=["GET", "POST"])
def edit_doctor_profile():
    if "role" not in session or session["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctor = User.query.get_or_404(session["user_id"])

    if request.method == "POST":
        doctor.full_name = request.form.get("full_name")
        doctor.email = request.form.get("email")
        doctor.phone = request.form.get("phone")
        doctor.qualification = request.form.get("qualification")
        doctor.specialization = request.form.get("specialization")
        doctor.experience = request.form.get("experience")

        profile_photo = request.files.get("profile_photo")

        if profile_photo and profile_photo.filename != "":
            filename = secure_filename(profile_photo.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            profile_photo.save(filepath)
            doctor.profile_photo = filename

        db.session.commit()
        session["full_name"] = doctor.full_name

        flash("Profile updated successfully.", "success")
        return redirect(url_for("doctor_profile"))

    return render_template("edit_doctor_profile.html", doctor=doctor)


@app.route("/doctor-profile")
def doctor_profile():
    if "role" not in session or session["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctor = User.query.get(session["user_id"])
    return render_template("doctor_profile.html", doctor=doctor)


# PASSWORD RECOVERY
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        contact = request.form["contact"]
        user = User.query.filter(((User.email == contact) | (User.username == contact)) & (User.role == "doctor")).first()
        if user:
            session["reset_user_id"] = user.id
            return redirect(url_for("verify_otp"))
        return "Doctor account not found"
    return render_template("forgot-password.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        if request.form["otp"] == "123456":
            return redirect(url_for("reset_password"))
        return "Invalid OTP"
    return render_template("verify_otp.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        if request.form["new_password"] != request.form["confirm_password"]:
            return "Passwords do not match"
        user = User.query.get(session.get("reset_user_id"))
        user.password = request.form["new_password"]
        db.session.commit()
        return redirect(url_for("password_success"))
    return render_template("reset_password.html")


@app.route("/password-success")
def password_success():
    return render_template("password_success.html")


# PHARMACY DASHBOARD
@app.route("/pharmacy-dashboard")
def pharmacy_dashboard():
    medicines = Medicine.query.all()
    return render_template("pharmacy_dashboard.html", medicines=medicines)


@app.route("/add-medicine", methods=["GET", "POST"])
def add_medicine():
    if request.method == "POST":
        medicine = Medicine(
            name=request.form.get("name"), category=request.form.get("category"),
            stock=request.form.get("stock"), status=request.form.get("status")
        )
        db.session.add(medicine)
        db.session.commit()
        flash("Medicine added successfully!", "success")
        return redirect(url_for("pharmacy_dashboard"))
    return render_template("add_medicine.html")


@app.route("/edit-user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.full_name = request.form["full_name"]
        user.email = request.form["email"]
        user.phone = request.form["phone"]

        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("user_management"))

    return render_template("edit_user.html", user=user)


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

    return render_template("prescriptions.html", prescriptions=Prescription.query.all(), doctor_name=session.get("username"))


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

        new_prescription = Prescription(
            patient_name=patient_name or "Patient", medicine_name=medicine_name,
            dosage=request.form.get("dosage", "As directed"),
            doctor_name=session.get("username") or appointment.doctor_name or "Doctor",
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
    return redirect(url_for("doctor_appointments_list"))


# AMBULANCE DASHBOARD
@app.route("/ambulance-dashboard", methods=["GET"])
def ambulance_dashboard():
    from models import AmbulanceBooking

    ambulances = AmbulanceUnit.query.all()
    ambulance_bookings = AmbulanceBooking.query.filter(
        AmbulanceBooking.status.in_(["Pending", "Accepted", "On Mission"])
    ).order_by(AmbulanceBooking.created_at.desc()).all()
    
    total_fleet = len(ambulances)
    dispatch_count = AmbulanceUnit.query.filter_by(status="On Mission").count()
    available_ambulances = AmbulanceUnit.query.filter_by(status="Available").count()
    
    return render_template(
        "ambulance_dashboard.html",
        ambulances=ambulances,
        total_fleet=total_fleet,
        dispatch_count=dispatch_count,
        available_ambulances=available_ambulances,
        ambulance_bookings=ambulance_bookings
    )


# DISPATCH AMBULANCE
@app.route("/dispatch-ambulance", methods=["POST"])
def dispatch_ambulance():
    category = request.form.get("category")
    location = request.form.get("location")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")

    if not location:
        flash("Please enter a valid pickup location.", "warning")
        return redirect(url_for("ambulance_dashboard"))

    available_unit = AmbulanceUnit.query.filter_by(status="Available").first()

    if available_unit:
        available_unit.status = "On Mission"
        destination_info = f"{location} ({category})" if category else location
        available_unit.current_destination = destination_info
        
        if latitude and longitude:
            try:
                available_unit.latitude = float(latitude)
                available_unit.longitude = float(longitude)
            except ValueError:
                pass

        db.session.commit()
        flash(f"Unit {available_unit.vehicle_number} successfully dispatched to {location}!", "success")
    else:
        flash("Dispatch failed: No available ambulance units currently on standby.", "danger")

    return redirect(url_for("ambulance_dashboard"))


# HOSPITAL DASHBOARD
@app.route("/hospital-dashboard")
def hospital_dashboard():
    if not session.get("logged_in") or session.get("role") != "admin":
        flash("Access denied. Admin login required.", "danger")
        return redirect(url_for("home"))
    return render_template("system_nodes.html")


if __name__ == "__main__":
    app.run(debug=True)


