import os
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, User, Prescription, LabTest, AmbulanceUnit, Notification

app = Flask(__name__)
# Configure the SQLite database path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'careorbit.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'careorbit_secret_key_123'

# Bind database & auto-create tables on launch
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/doctor-dashboard")
def doctor_dashboard():
    return render_template("doctor_dashboard.html")

@app.route("/patient-records")
def patient_records():
    return render_template("patient_records.html")

@app.route("/appointments")
def appointments():
    return render_template("appointments.html")

@app.route("/prescriptions")
def prescriptions():
    return render_template("prescriptions.html")

@app.route("/emergency-cases")
def emergency_cases():
    return render_template("emergency_cases.html")

@app.route("/doctor-login")
def doctor_login():
    return render_template("doctor_login.html")

@app.route("/hospital-dashboard")
def hospital_dashboard():
    return render_template("hospital_dashboard.html")

@app.route("/pharmacy-dashboard")
def pharmacy_dashboard():
    return render_template("pharmacy_dashboard.html")

@app.route("/laboratory-dashboard")
def laboratory_dashboard():
    return render_template("laboratory_dashboard.html")

@app.route("/ambulance-dashboard")
def ambulance_dashboard():
    return render_template("ambulance_dashboard.html")

@app.route("/admin-dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")

@app.route("/user-management")
def user_management():
    return render_template("user_management.html")

@app.route("/setup-db")
def setup_db():
    # 1. Clear any existing data to start fresh
    db.drop_all()
    db.create_all() 

    # 2. Add Dummy Users (Admin, Doctor, Patient, Pharmacist)
    u1 = User(username="admin_sarah", email="sarah@careorbit.com", role="Admin", department="Administration")
    u2 = User(username="dr_smith", email="smith@careorbit.com", role="Doctor", department="Cardiology")
    u3 = User(username="pharmacist_john", email="john@careorbit.com", role="Pharmacist", department="Pharmacy")
    u4 = User(username="patient_jane", email="jane@gmail.com", role="Patient", department=None)
    
    # 3. Add Dummy Prescriptions
    p1 = Prescription(patient_name="Jane Doe", medicine_name="Amoxicillin", dosage="500mg - twice daily", doctor_name="Dr. Smith", status="Pending")
    p2 = Prescription(patient_name="Mark Wilson", medicine_name="Metformin", dosage="1000mg - once daily", doctor_name="Dr. Adams", status="Completed")

    # 4. Add Dummy Lab Tests
    l1 = LabTest(patient_name="Jane Doe", test_modality="Blood Panel", requested_by="Dr. Smith", status="Sample Collected")
    l2 = LabTest(patient_name="Robert Chen", test_modality="X-Ray Chest", requested_by="Dr. Davis", status="Awaiting Sample")

    # 5. Add Dummy Ambulance Units
    a1 = AmbulanceUnit(vehicle_number="AMB-001", vehicle_type="Advanced Life Support", crew_assigned="Paramedic Jack, EMT Jill", current_destination="123 Maple St", status="En Route")
    a2 = AmbulanceUnit(vehicle_number="AMB-002", vehicle_type="Basic Life Support", crew_assigned="EMT Ross", current_destination=None, status="Available")

    # 6. Add Dummy Notifications
    n1 = Notification(target_audience="All Staff", severity="High", message="System maintenance scheduled for midnight tonight.")
    n2 = Notification(target_audience="Doctors", severity="Medium", message="New cardiology guidelines have been uploaded to the portal.")

    # Save everything to the database
    db.session.add_all([u1, u2, u3, u4, p1, p2, l1, l2, a1, a2, n1, n2])
    db.session.commit()

    return "Database successfully populated with mock data! Go back to your dashboards."


if __name__ == "__main__":
    app.run(debug=True)