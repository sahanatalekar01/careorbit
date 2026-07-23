from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# USER MODEL (Doctor/Admin/Staff)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default="Active")


# PRESCRIPTION MODEL
class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(150), nullable=False)
    medicine_name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), default="Pending")


# AMBULANCE MODEL
class AmbulanceUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(50), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(100), nullable=False)
    crew_assigned = db.Column(db.String(200), nullable=False)
    current_destination = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default="Available")


# NOTIFICATION MODEL
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_audience = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )
    is_active = db.Column(db.Boolean, default=True)


# WARD MODEL
class Ward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    total_beds = db.Column(db.Integer, nullable=False, default=0)
    occupied_beds = db.Column(db.Integer, nullable=False, default=0)


# MEDICINE MODEL
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(
        db.String(50),
        nullable=False,
        default="In Stock"
    )


# LAB TEST MODEL
class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    test_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    status = db.Column(
        db.String(50),
        nullable=False,
        default="Pending"
    )
    date_requested = db.Column(db.String(50), nullable=False)


# PATIENT MODEL
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    age = db.Column(
        db.Integer,
        nullable=False
    )

    gender = db.Column(
        db.String(20),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    blood_group = db.Column(
        db.String(10),
        nullable=True
    )

    address = db.Column(
        db.Text,
        nullable=True
    )

    medical_history = db.Column(
        db.Text,
        nullable=True
    )


# REPORT MODEL
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient.id"),
        nullable=False
    )

    report_title = db.Column(
        db.String(200),
        nullable=False
    )

    report_details = db.Column(
        db.Text,
        nullable=False
    )

    report_date = db.Column(
        db.Date,
        nullable=False
    )
    
class Doctor(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    phone = db.Column(db.String(15), unique=True)

    password = db.Column(db.String(200), nullable=False)

# APPOINTMENT MODEL (FIXED)
class Appointment(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient.id"),
        nullable=True
    )

    patient_name = db.Column(
        db.String(100),
        nullable=False
    )

    doctor_name = db.Column(
        db.String(150),
        nullable=False
    )

    age = db.Column(
        db.Integer,
        nullable=False
    )

    gender = db.Column(
        db.String(20),
        nullable=False
    )

    symptoms = db.Column(
        db.String(200),
        nullable=False
    )

    appointment_date = db.Column(
        db.Date,
        nullable=True
    )

    appointment_time = db.Column(
        db.String(50),
        nullable=True
    )

    time = db.Column(
        db.String(50),
        nullable=True
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )
