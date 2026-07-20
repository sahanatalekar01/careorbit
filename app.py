import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from models import db, User, Prescription, LabTest, AmbulanceUnit, Notification, Appointment, Ward, Medicine, Patient, Report

app = Flask(__name__)

# --- App Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'careorbit.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'careorbit_secret_key_123'
app.config['UPLOAD_FOLDER'] = os.path.join("static", "uploads")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

with app.app_context():
    db.create_all()
    # Initial Seeding
    if not Ward.query.first():
        db.session.bulk_save_objects([
            Ward(name="Ward A (General)", type="General Medicine", total_beds=50, occupied_beds=42),
            Ward(name="Ward B (Paediatrics)", type="Special Care", total_beds=20, occupied_beds=18),
            Ward(name="Emergency Wing ICU", type="Intensive Care", total_beds=10, occupied_beds=8)
        ])
        db.session.commit()
    # ... (Add other seed logic here)

# --- Routes: Home & Authentication ---
@app.route("/")
def home(): return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- Routes: Patient Modules ---
@app.route("/patient-register", methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        patient = Patient(full_name=request.form.get("full_name"), email=request.form.get("email"), 
                          password=request.form.get("password"), age=int(request.form.get("age")))
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for("patient_login"))
    return render_template("patient_register.html")

@app.route("/patient-login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        patient = Patient.query.filter_by(email=request.form.get("email"), password=request.form.get("password")).first()
        if patient:
            session["patient_id"] = patient.id
            session["patient_name"] = patient.full_name
            return redirect(url_for("patient_dashboard"))
    return render_template("patient_login.html")

@app.route("/add-test-doctor")
def add_test_doctor():
    # Make sure you import User at the top of your app.py
    new_doctor = User(username="Dr. Smith", email="doctor@careorbit.com", password="password123", role="doctor")
    db.session.add(new_doctor)
    db.session.commit()
    return "Test doctor added! Now go to /doctor-login and use: doctor@careorbit.com / password123"

@app.route("/add-test-appointment")
def add_test_appointment():
    test_appt = Appointment(
        patient_id=1, # Link to the patient we just created
        patient_name="John Doe", 
        gender="Male", 
        age=35, 
        symptoms="Fever, Cough", 
        time="10:00 AM",
        status="Pending"
    )
    db.session.add(test_appt)
    db.session.commit()
    return "Test appointment added!"

@app.route("/check-patients")
def check_patients():
    from models import Patient # Import your Patient model
    patients = Patient.query.all()
    return f"Number of patients in database: {len(patients)}"

@app.route("/seed-patients")
def seed_patients():
    from models import Patient
    # Use 'full_name' instead of 'username'
    new_patient = Patient(
        full_name="John Doe", 
        email="john@example.com", 
        password="password", 
        age=30, 
        gender="Male"
    )
    db.session.add(new_patient)
    db.session.commit()
    return f"Patient added with ID: {new_patient.id}"

@app.route("/patient-dashboard")
def patient_dashboard():
    return render_template("patient_dashboard.html", patient_name=session.get("patient_name"))

@app.route("/patient-records/<int:id>")
def patient_records(id):
    from models import Appointment
    # This fetches the specific appointment by its ID
    appointment = Appointment.query.get_or_404(id)
    
    # This renders the patient_records.html page with the data
    return render_template("patient_records.html", appointment=appointment)

@app.route("/analyze", methods=["POST"])
def analyze():
    # ... (Include Sahana's AI analysis logic here)
    return jsonify({"status": "success", "message": "Analyzed"})

# --- Routes: Doctor & Admin Modules ---
from models import Appointment  # Make sure you import your model

@app.route("/doctor-dashboard")
def doctor_dashboard():
    # 1. Fetch data
    appointments_list = Appointment.query.all()

    # 2. Calculate Stats correctly
    todays_count = len(appointments_list) 
    completed_count = Appointment.query.filter_by(status='Completed').count()
    pending_count = Appointment.query.filter_by(status='Pending').count()

    # 3. Pass them to the template
    return render_template(
        "doctor_dashboard.html", 
        appointments=appointments_list,
        todays_count=todays_count,
        completed_count=completed_count,
        pending_count=pending_count
    )

from flask import render_template, request, redirect, url_for, session, flash

@app.route("/doctor-login", methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Query the User model
        user = User.query.filter_by(email=email, password=password, role='doctor').first()
        
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('doctor_dashboard'))
        else:
            flash("Invalid email or password.")
            
    return render_template("doctor_login.html")
# --- Routes: Hospital/Pharmacy/Lab/Ambulance ---
@app.route("/hospital-dashboard")
def hospital_dashboard(): return render_template("hospital_dashboard.html", wards=Ward.query.all())

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(error): return render_template("404.html"), 404

@app.route("/setup-db")
def setup_db():
    try:
        db.create_all()
        return "Database tables created successfully!"
    except Exception as e:
        return f"An error occurred: {e}"
if __name__ == "__main__":
    app.run(debug=True)