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
    
    # Check phone or emergency_contact depending on schema attribute
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


# PATIENT REGISTER (Single-Step Form with Health & Personal Details)
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
        
        # Dynamically map phone or emergency_contact based on model definition
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

            # Check if profile details are incomplete
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
    
    # Enforce profile completion check
    if not is_profile_complete(patient):
        flash("Please complete your profile details first.", "warning")
        return redirect(url_for("complete_profile"))

    return render_template("patient_dashboard.html", patient_name=session.get("patient_name", "Patient"), patient=patient)


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


# REPORTS
@app.route("/reports")
def reports():
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))
    patient_reports = Report.query.filter_by(patient_id=session["patient_id"]).all()
    return render_template("reports.html", reports=patient_reports)


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


# DOCTOR LOGIN
@app.route("/doctor-login", methods=["GET", "POST"])
def doctor_login():

    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")
        remember = request.form.get("remember")

        user = User.query.filter(((User.username == login) | (User.email == login)) & (User.role == "doctor")).first()

        if user and user.password == password:
            session.permanent = True if remember else False
            session["logged_in"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"] = user.full_name
            session["role"] = user.role.lower()
            flash(f"Welcome back, Dr. {user.full_name}!", "success")
            return redirect(url_for("doctor_dashboard"))

        flash("Invalid username/email or password.", "danger")
        user = User.query.filter(
            (
                (User.username == login) |
                (User.email == login)
            ) &
            (User.role == "doctor")
        ).first()

        print("Login entered:", login)
        print("User found:", user)

        if not user:
            flash("Doctor account not found.", "danger")
            return redirect(url_for("doctor_login"))

        if user.password != password:
            flash("Invalid password.", "danger")
            return redirect(url_for("doctor_login"))

        if user.verification_status == "Pending":
            flash(
                "Your account is under admin verification. Please wait until it is approved.",
                "warning"
            )
            return redirect(url_for("doctor_login"))

        if user.verification_status == "Rejected":
            flash(
                f"Your account has been rejected. {user.admin_remark or ''}",
                "danger"
            )
            return redirect(url_for("doctor_login"))

        session["logged_in"] = True
        session["user_id"] = user.id
        session["username"] = user.username
        session["full_name"] = user.full_name
        session["role"] = user.role.lower()

        flash(
            f"Welcome back, Dr. {user.full_name}!",
            "success"
        )

        return redirect(url_for("doctor_dashboard"))

    return render_template("doctor_login.html")


# ADD TEST DOCTOR
@app.route("/add-test-doctor")
def add_test_doctor():
    existing_doctor = User.query.filter_by(email="doctor@careorbit.com").first()
    if not existing_doctor:
        doctor = User(username="Dr. Smith", email="doctor@careorbit.com", password="password123", role="doctor")


        doctor = User(
            full_name="Dr. Smith",
            username="drsmith",
            email="doctor@careorbit.com",
            password="password123",
            role="doctor",
            verification_status="Approved"
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
    todays_count = Appointment.query.filter_by(appointment_date=today).count()
    completed_visits = Appointment.query.filter_by(status="Completed").count()
    pending_visits = Appointment.query.filter_by(status="Pending").count()

    return render_template(
        "doctor_dashboard.html", appointments=appointments_list,
        todays_count=todays_count, completed_count=completed_visits,
        pending_count=pending_visits, doctor_name=session.get("full_name", "Doctor")
    )


# PATIENT RECORDS
@app.route("/patient-records")
def patient_records():
    patients = Patient.query.all()
    return render_template("patient_records.html", patients=patients)


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


# DOCTOR REGISTER
@app.route("/doctor-register", methods=["GET", "POST"])
def doctor_register():
    if request.method == "POST":

        full_name, username = request.form["full_name"], request.form["username"]
        email, phone = request.form["email"], request.form["phone"]
        password, confirm_password = request.form["password"], request.form["confirm_password"]


        full_name = request.form["full_name"]
        username = request.form["username"]
        email = request.form["email"]
        phone = request.form["phone"]

        qualification = request.form["qualification"]
        specialization = request.form["specialization"]

        profile_photo = request.files["profile_photo"]

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("doctor_register"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("doctor_register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("doctor_register"))

        doctor = User(full_name=full_name, username=username, email=email, phone=phone, password=password, role="doctor")
        db.session.add(doctor)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        profile_photo_filename = secure_filename(profile_photo.filename)

        profile_photo.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                profile_photo_filename
            )
        )

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

            verification_status="Pending",
            admin_remark=None
        )

        db.session.add(doctor)
        db.session.commit()

        flash(
            "Registration submitted successfully. Your account will be activated after admin verification.",
            "success"
        )
        return redirect(url_for("doctor_login"))

    return render_template("doctor_register.html")

@app.route("/doctor-verification")
def doctor_verification():

    if "role" not in session or session["role"] != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctors = User.query.filter_by(
        role="doctor",
        verification_status="Pending"
    ).all()

    pending_doctors = User.query.filter_by(
        role="doctor",
        verification_status="Pending"
    ).count()

    approved_doctors = User.query.filter_by(
        role="doctor",
        verification_status="Approved"
    ).count()

    rejected_doctors = User.query.filter_by(
        role="doctor",
        verification_status="Rejected"
    ).count()

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

    # Create notification
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
        admin_user="Admin",
        event_scope="Doctor Verification",
        target_reference=doctor.full_name,
        security_level="Rejected"
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

        doctor.full_name = request.form["full_name"]
        doctor.email = request.form["email"]
        doctor.phone = request.form["phone"]

        profile_photo = request.files.get("profile_photo")

        if profile_photo and profile_photo.filename != "":

            filename = secure_filename(profile_photo.filename)

            profile_photo.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            doctor.profile_photo = filename

        db.session.commit()

        session["full_name"] = doctor.full_name

        flash(
            "Profile updated successfully.",
            "success"
        )

        return redirect(url_for("doctor_profile"))

    return render_template(
        "edit_doctor_profile.html",
        doctor=doctor
    )

@app.route("/doctor-profile")
def doctor_profile():

    if "role" not in session or session["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctor = User.query.get(session["user_id"])

    return render_template(
        "doctor_profile.html",
        doctor=doctor
    )



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


@app.route("/password-success")
def password_success():
    return render_template("password_success.html")


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
    return redirect(url_for("doctor_dashboard"))


# HOSPITAL DASHBOARD
@app.route("/hospital-dashboard")
def hospital_dashboard():
    wards_list = Ward.query.all()
    total_beds = sum(w.total_beds for w in wards_list if w.total_beds)
    occupied_beds = sum(w.occupied_beds for w in wards_list if w.occupied_beds)
    occupancy = int((occupied_beds / total_beds) * 100) if total_beds > 0 else 0

    icu = Ward.query.filter(Ward.name.ilike("%icu%")).first()
    icu_capacity = int((icu.occupied_beds / icu.total_beds) * 100) if icu and icu.total_beds else 0

    return render_template(
        "hospital_dashboard.html", wards=wards_list, bed_occupancy=occupancy,
        icu_capacity=icu_capacity, total_beds=total_beds, occupied_beds=occupied_beds,
        icu_ward=icu, doctors_on_duty=User.query.filter_by(role="doctor").count(),
        opd_queue=Appointment.query.filter_by(status="Pending").count(),
        services=[
            {"name": "Pharmacy Hub", "description": "Fully Stocked", "status": "Online"},
            {"name": "Diagnostics Lab", "description": "Processing Reports", "status": "Online"},
            {"name": "Emergency Response", "description": "Ambulance Available", "status": "Online"}
        ]
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
    today = datetime.now().strftime("%d-%m-%Y")
    return render_template(
        "laboratory_dashboard.html", lab_tests=LabTest.query.all(), analyzers=Analyzer.query.all(),
        pending_tests=LabTest.query.filter_by(status="Pending").count(),
        processing_tests=LabTest.query.filter_by(status="Processing").count(),
        completed_tests=LabTest.query.filter_by(status="Completed").count(),
        urgent_tests=LabTest.query.filter_by(priority="High Priority").count()
    )


# AMBULANCE DASHBOARD
@app.route("/ambulance-dashboard")
def ambulance_dashboard():
    ambulances = AmbulanceUnit.query.all()
    return render_template(
        "ambulance_dashboard.html", ambulances=ambulances, total_fleet=len(ambulances),
        dispatch_count=AmbulanceUnit.query.filter_by(status="On Mission").count(),
        available_ambulances=AmbulanceUnit.query.filter_by(status="Available").count()
    )


# ADMIN DASHBOARD
@app.route("/admin-dashboard")
def admin_dashboard():
    if "role" not in session or session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    notifications = Notification.query.all()
    return render_template(
        "admin_dashboard.html", total_appointments=Appointment.query.count(),
        completed_visits=Appointment.query.filter_by(status="Completed").count(),
        user_count=User.query.count(), notice_count=len(notifications), records=notifications
    total_appointments = Appointment.query.count()

    completed_visits = Appointment.query.filter_by(
        status="Completed"
    ).count()

    users = User.query.count()

    pending_doctors = User.query.filter_by(
        role="doctor",
        verification_status="Pending"
    ).count()

    records = AuditLog.query.order_by(
        AuditLog.timestamp.desc()
    ).all()

    return render_template(
        "admin_dashboard.html",
        total_appointments=total_appointments,
        completed_visits=completed_visits,
        user_count=users,
        pending_doctors=pending_doctors,
        records=records
    )


# USER MANAGEMENT
@app.route("/user-management")
def user_management():
    if "role" not in session or session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))
    return render_template("user_management.html", users=User.query.all())


@app.route("/admin/search")
def admin_search():
    if "role" not in session or session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    query = request.args.get("query", "")
    results = User.query.filter((User.username.like(f"%{query}%")) | (User.email.like(f"%{query}%"))).all() if query else User.query.all()
    return render_template("user_management.html", users=results)

    return render_template(
        "user_management.html",
        users=results
    )


@app.route("/admin-register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        admin = User(
            username=request.form.get("username"), email=request.form.get("email"),
            password=request.form.get("password"), role="admin"


        full_name = request.form.get("full_name")
        username = request.form.get("username")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("admin_register"))

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("admin_register"))

        admin = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone,
            password=password,
            role="admin",
            status="Active"

        )
        db.session.add(admin)
        db.session.commit()
        flash("Admin registered successfully.", "success")
        return redirect(url_for("admin_login"))
    return render_template("admin_register.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email, password = request.form.get("email"), request.form.get("password")
        admin = User.query.filter_by(email=email, password=password, role="admin").first()

        if admin:
            session["logged_in"] = True
            session["user_id"] = admin.id
            session["role"] = "admin"
            session["username"] = admin.username
            db.session.add(AuditLog(user=admin.username, action="Login", details="Admin logged into CareOrbit"))
            db.session.commit()
            flash("Admin login success")
            return redirect(url_for("admin_dashboard"))

            # Create Audit Log
            log = AuditLog(
                admin_user=admin.username,
                event_scope="Admin Login",
                target_reference="CareOrbit Admin Panel",
                security_level="Login"
            )

            db.session.add(log)
            db.session.commit()

            flash("Admin login successful.", "success")

            return redirect(url_for("admin_dashboard"))

        else:
            flash("Invalid admin credentials.", "danger") 
        flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")


@app.route("/admin-settings", methods=["GET", "POST"])
def admin_settings():
    if "role" not in session or session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        notification = Notification(message=request.form.get("message"), target=request.form.get("target"))
        db.session.add(notification)
        db.session.commit()
        flash("Notification sent successfully", "success")
    return render_template("admin_settings.html")


# PHARMACY DASHBOARD
@app.route("/pharmacy-dashboard")
def pharmacy_dashboard():
    return render_template(
        "pharmacy_dashboard.html", medicines=Medicine.query.all(),
        total_stock=Medicine.query.count(), low_stock=Medicine.query.filter(Medicine.stock <= 10).count(),
        pending_orders=Prescription.query.filter_by(status="Pending").count(),
        dispensed_today=Prescription.query.filter_by(status="Completed").count(),
        prescriptions=Prescription.query.all()
    )


@app.route("/dispatch-ambulance", methods=["POST"])
def dispatch_ambulance():
    category, location = request.form.get("category"), request.form.get("location")
    latitude, longitude = request.form.get("latitude"), request.form.get("longitude")
    ambulance = AmbulanceUnit.query.filter_by(status="Available").first()

    if ambulance:
        ambulance.status = "On Mission"
        ambulance.current_destination = location
        if latitude and longitude:
            ambulance.latitude = float(latitude)
            ambulance.longitude = float(longitude)
        db.session.commit()
        flash(f"Ambulance dispatched for {category}", "success")
    else:
        flash("No ambulance available currently.", "danger")
    return redirect(url_for("ambulance_dashboard"))


@app.route("/lab-request/<int:id>", methods=["GET", "POST"])
def lab_request(id):
    if "role" not in session or session.get("role") != "doctor":
        flash("Please login as doctor.", "danger")
        return redirect(url_for("doctor_login"))

    appointment = Appointment.query.get_or_404(id)
    if request.method == "POST":
        test = LabTest(
            patient_name=appointment.patient_name, test_name=request.form.get("test_name"),
            category=request.form.get("sample_type"), status="Pending",
            date_requested=datetime.now().strftime("%d-%m-%Y %H:%M")
        )
        db.session.add(test)
        db.session.commit()
        flash("Lab test request submitted successfully.", "success")
        return redirect(url_for("laboratory_dashboard"))

    return render_template(
        "lab_request.html", appointment=appointment, doctor_name=session.get("full_name", "Doctor"),
        current_date=datetime.now().strftime("%d-%m-%Y"), current_time=datetime.now().strftime("%I:%M %p")
    )


# EXTRA PAGES
@app.route("/appointments")
def doctor_appointments_list():
    if "role" not in session or session.get("role") != "doctor":
        flash("Please login as doctor.", "danger")
        return redirect(url_for("doctor_login"))
    return render_template(
        "doctor_appointment.html", appointments=Appointment.query.all(),
        pending_count=Appointment.query.filter_by(status="Pending").count(),
        accepted_count=Appointment.query.filter_by(status="Accepted").count()
    )


@app.route("/emergency-cases")
def emergency_cases():
    return render_template("emergency_cases.html", emergency_cases=[])


@app.route("/system-nodes")
def system_nodes():
    return render_template("system_nodes.html")


@app.route("/audit-logs")
def audit_logs():
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("admin_login"))
    return render_template("audit_logs.html", records=AuditLog.query.all())


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

@app.route("/doctor-notifications")
def doctor_notifications():

    if "role" not in session or session["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    notifications = Notification.query.filter_by(
        target_audience="Doctor",
        is_active=True
    ).order_by(Notification.timestamp.desc()).all()

    return render_template(
        "doctor_notifications.html",
        notifications=notifications
    )

# RUN APPLICATION
if __name__ == "__main__":
    app.run(debug=True)