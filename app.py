import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Prescription, LabTest, AmbulanceUnit, Notification, Appointment, Ward, Medicine

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
    
    # 🏥 Seed Ward Data if empty
    if not Ward.query.first():
        sample_wards = [
            Ward(name="Ward A (General)", type="General Medicine", total_beds=50, occupied_beds=42),
            Ward(name="Ward B (Paediatrics)", type="Special Care", total_beds=20, occupied_beds=18),
            Ward(name="Emergency Wing ICU", type="Intensive Care", total_beds=10, occupied_beds=8)
        ]
        db.session.bulk_save_objects(sample_wards)
        db.session.commit()
    if not Medicine.query.first():
        sample_meds = [
            Medicine(name="Paracetamol 500mg", category="Analgesic", stock=120, status="In Stock"),
            Medicine(name="Amoxicillin 250mg", category="Antibiotic", stock=15, status="Low Stock"),
            Medicine(name="Metformin 850mg", category="Antidiabetic", stock=85, status="In Stock"),
            Medicine(name="Ibuprofen 400mg", category="NSAID", stock=0, status="Out of Stock")
        ]
        db.session.bulk_save_objects(sample_meds)
        db.session.commit()
        # 🧪 Seed LabTest Data if empty
    if not LabTest.query.first():
        sample_tests = [
            LabTest(patient_name="John Doe", test_name="Complete Blood Count (CBC)", category="Hematology", status="Pending", date_requested="2026-07-17"),
            LabTest(patient_name="Jane Smith", test_name="Chest X-Ray", category="Radiology", status="Processing", date_requested="2026-07-17"),
            LabTest(patient_name="Alice Johnson", test_name="Lipid Profile", category="Pathology", status="Completed", date_requested="2026-07-16"),
            LabTest(patient_name="Bob Brown", test_name="Urinalysis", category="Pathology", status="Pending", date_requested="2026-07-17")
        ]
        db.session.bulk_save_objects(sample_tests)
        db.session.commit()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/doctor-dashboard")
def doctor_dashboard():
    # 🔒 Security Guard: If the user is not authenticated as a doctor, kick them back to login!
    if 'role' not in session or session.get('role') != 'doctor':
        flash('Please log in as a doctor to access this dashboard.', 'danger')
        return redirect(url_for('doctor_login'))

    # Fetch the appointments list to display in the table
    appointments_list = Appointment.query.all()

    # 📊 Calculate Doctor Stats
    # 1. Today's Visits (Total scheduled appointments)
    todays_visits = Appointment.query.count()

    # 2. Completed Visits (Appointments with status 'Completed')
    completed_visits = Appointment.query.filter_by(status='Completed').count()

    # 3. Pending Approvals (Appointments with status 'Pending')
    pending_visits = Appointment.query.filter_by(status='Pending').count()

    # Render the dashboard normally and pass all our variables!
    return render_template(
        "doctor_dashboard.html", 
        patients=appointments_list,
        todays_visits=todays_visits,
        completed_visits=completed_visits,
        pending_visits=pending_visits
    )
@app.route("/patient-record/<int:patient_id>")

def patient_record(patient_id):
    # 🔒 Security Guard
    if 'role' not in session or session.get('role') != 'doctor':
        flash('Please log in as a doctor to access patient records.', 'danger')
        return redirect(url_for('doctor_login'))

    # 1. Find the specific patient/appointment by their ID
    patient = Appointment.query.get_or_404(patient_id)
    
    # 2. Render the patient records page and pass the patient data
    return render_template("patient_details.html", patient=patient)

@app.route("/prescribe/<int:patient_id>", methods=["POST"])
def prescribe(patient_id):
    # 🔒 Security Guard
    if 'role' not in session or session.get('role') != 'doctor':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('doctor_login'))

    # 1. Fetch the patient's record
    patient = Appointment.query.get_or_404(patient_id)
    
    # 2. Get the prescription text from the form
    prescription_text = request.form.get("prescription")
    
    if prescription_text:
        # 3. Save prescription and update status to 'Completed'
        patient.prescription = prescription_text  
        patient.status = 'Completed'
        
        db.session.commit()
        flash(f"Prescription successfully submitted for {patient.patient_name}!", "success")
    else:
        flash('Prescription cannot be empty.', 'warning')

    # 4. Redirect back to the doctor dashboard
    return redirect(url_for('doctor_dashboard'))
@app.route("/appointments")
def appointments():
    return render_template("appointments.html")

@app.route("/prescriptions")
def prescriptions():
    return render_template("prescriptions.html")

@app.route("/emergency-cases")
def emergency_cases():
    return render_template("emergency_cases.html")

@app.route("/doctor-login", methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user=User.query.filter_by(email=email).first()
        if user and user.password == password:
            if user.role.lower() == "doctor":
        # Simple verification check for Dr. Smith
                session["logged_in"] = True
                session["user_id"] = user.id
                session["username"] = user.username 
                session['role'] = user.role
                flash(f"Welcome back, Dr. {user.username}!","success")
                return redirect(url_for('doctor_dashboard'))
        else:
            flash("Access denied. This portal is reserved for Doctors.", "danger")
    else:
        flash("Invalid email or password.", "danger")
    return render_template("doctor_login.html")

@app.route("/hospital-dashboard")
def hospital_dashboard():
    # 🔒 Security Gatekeeper
    #if 'role' not in session or session.get('role').lower() not in ['admin', 'hospital']:
     #   flash('Unauthorized access to hospital management portal.', 'danger')
      #  return redirect(url_for('doctor_login'))
    
    # 🏥 Fetch all wards for the main table
    wards_list = Ward.query.all() 
    
    # 📈 Dynamic Math for the Grid Analytics
    sum_total_beds = sum(w.total_beds for w in wards_list)
    sum_occupied = sum(w.occupied_beds for w in wards_list)
    
    # Avoid dividing by zero if your database is empty
    occupancy_percent = int((sum_occupied / sum_total_beds) * 100) if sum_total_beds > 0 else 0

    # Specifically look up the critical care ward data for Card 2
    icu_ward = Ward.query.filter(Ward.name.ilike('%icu%')).first()
    icu_percent = int((icu_ward.occupied_beds / icu_ward.total_beds) * 100) if icu_ward and icu_ward.total_beds > 0 else 0

    return render_template(
        "hospital_dashboard.html",
        wards=wards_list,
        bed_occupancy=occupancy_percent,
        icu_capacity=icu_percent
    )
@app.route("/pharmacy-dashboard")
def pharmacy_dashboard():
    # 1. Safely handle medicines list
    try:
        from models import Medicine
        medicines_list = Medicine.query.all()
        total_products = len(medicines_list)
        low_stock_count = Medicine.query.filter(Medicine.stock <= 20).count()
    except Exception:
        medicines_list = []
        total_products = 0
        low_stock_count = 0

    # 2. Hardcode a mock count for pending orders to bypass the Appointment model error
    pending_orders = 12 
    total_stock = 1248

    return render_template(
        "pharmacy_dashboard.html",
        medicines=medicines_list,
        total_products=total_products,
        low_stock_count=low_stock_count,
        pending_orders=pending_orders,
        total_stock=total_stock
    )

@app.route("/dispense-medication/<int:appointment_id>", methods=["POST"])
def dispense_medication(appointment_id):
    # 🔒 Security Guard: Match your dashboard check
    if 'role' not in session or session.get('role') != 'pharmacy':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('doctor_login'))

    # Fetch the appointment record
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Update status to 'Dispensed' so it shifts metrics dynamically
    appointment.status = 'Dispensed'
    db.session.commit()
    
    flash(f"Medications successfully dispensed for {appointment.patient_name}!", "success")
    return redirect(url_for('pharmacy_dashboard'))

@app.route("/laboratory-dashboard")
def laboratory_dashboard():
    try:
        from models import LabTest
        lab_tests = LabTest.query.all()
        total_tests = len(lab_tests)
        pending_tests = LabTest.query.filter_by(status="Pending").count()
        processing_tests = LabTest.query.filter_by(status="Processing").count()
    except Exception:
        lab_tests = []
        total_tests = 0
        pending_tests = 0
        processing_tests = 0

    return render_template(
        "laboratory_dashboard.html",
        lab_tests=lab_tests,
        total_tests=total_tests,
        pending_tests=pending_tests,
        processing_tests=processing_tests
    )

@app.route("/ambulance-dashboard")
def ambulance_dashboard():
    # Hardcoded list to perfectly bypass the database schema error for now
    ambulances_list = [
        {"id": 1, "vehicle_number": "AMB-001", "driver_name": "Michael Scott", "status": "Available", "current_location": "Station A"},
        {"id": 2, "vehicle_number": "AMB-002", "driver_name": "Dwight Schrute", "status": "On Mission", "current_location": "Route 101 - Trauma Center"},
        {"id": 3, "vehicle_number": "AMB-003", "driver_name": "Jim Halpert", "status": "Available", "current_location": "Station B"},
        {"id": 4, "vehicle_number": "AMB-004", "driver_name": "Pam Beesly", "status": "Out of Service", "current_location": "Main Workshop"}
    ]
    
    total_fleet = len(ambulances_list)
    available_units = 2
    on_mission = 1

    return render_template(
        "ambulance_dashboard.html",
        ambulances=ambulances_list,
        total_fleet=total_fleet,
        available_units=available_units,
        on_mission=on_mission
    )

@app.route("/admin-dashboard")
def admin_dashboard():
    total_appointments = Appointment.query.count()
    completed_visits = Appointment.query.filter_by(status='Completed').count()
    
    active_system_users = 15  
    unread_notifications = 3  
    
    # 📝 Mock data array matching the exact structure your table loop expects
    mock_logs = [
        {
            "timestamp": "Just now",
            "admin_user": "System Admin (Root)",
            "event_scope": "Modified Global Variable",
            "target_reference": "/config/routes",
            "security_level": "Config"
        },
        {
            "timestamp": "5 mins ago",
            "admin_user": "Moderator_02",
            "event_scope": "Verified Healthcare Professional",
            "target_reference": "Dr. Shruti (ID: 808)",
            "security_level": "Approval"
        },
        {
            "timestamp": "12 mins ago",
            "admin_user": "SecOps Daemon",
            "event_scope": "Database Migration Block Executed",
            "target_reference": "db_cluster_prod",
            "security_level": "System"
        }
    ]
    
    return render_template(
        "admin_dashboard.html",
        total_appointments=total_appointments,
        completed_visits=completed_visits,
        user_count=active_system_users,
        notice_count=unread_notifications,
        records=mock_logs  # 👈 Sending the mock log list to the loop!
    )

@app.route("/user-management")
def user_management():
    # 🔒 Security Guard (Temporarily disabled for easy testing)
    # if 'role' not in session or session.get('role') != 'admin':
    #     flash('Unauthorized access.', 'danger')
    #     return redirect(url_for('doctor_login'))

    # Fetch all logs/records so the administrator can audit system entries
    all_records = Appointment.query.all()
    
    return render_template(
        "user_management.html",
        records=all_records
    )

@app.route("/setup-db")
def setup_db():
    # 1. Clear any existing data to start fresh
    db.drop_all()
    db.create_all() 

    # 2. Add Dummy Users (Admin, Doctor, Patient, Pharmacist)
    u1 = User(username="admin_sarah", email="sarah@careorbit.com", password="password123", role="Admin", department="Administration")
    u2 = User(username="dr_smith", email="smith@careorbit.com", password="password123", role="Doctor", department="Cardiology")
    u3 = User(username="pharmacist_john", email="john@careorbit.com", password="password123", role="Pharmacist", department="Pharmacy")
    u4 = User(username="patient_jane", email="jane@gmail.com", password="password123", role="Patient", department=None)
    
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

    ap1 = Appointment(patient_name="Sarah Connor", age=29, gender="Female", symptoms="Severe Migraine, light sensitivity", time="09:30 AM", status="Completed")
    ap2 = Appointment(patient_name="John Doe", age=45, gender="Male", symptoms="Chronic cough, high fever", time="10:15 AM", status="Pending")
    ap3 = Appointment(patient_name="Bruce Wayne", age=38, gender="Male", symptoms="Sprained ankle, physical trauma", time="11:00 AM", status="Pending")
    db.session.add_all([u1, u2, u3, u4, p1, p2, l1, l2, a1, a2, n1, n2, ap1, ap2, ap3])
    db.session.commit()

    return "Database successfully populated with mock data! Go back to your dashboards."
if __name__ == "__main__":
    app.run(debug=True)