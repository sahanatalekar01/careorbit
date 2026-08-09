from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

db = SQLAlchemy()


# ============================================================
# USER MODEL (Doctor/Admin/Staff)
# ============================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Basic User Information
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    gender = db.Column(db.String(10), nullable=True)
    password = db.Column(db.String(255), nullable=False)

    # Role & Hospital Information
    role = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    hospital_name = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default="Active")

    # Doctor Details
    qualification = db.Column(db.String(200), nullable=True)
    specialization = db.Column(db.String(200), nullable=True)
    experience = db.Column(db.String(100), nullable=True)

    # Optional Profile Photo
    profile_photo = db.Column(db.String(255), nullable=True)

    # Verification Status
    verification_status = db.Column(
        db.String(30),
        default="Pending"
    )

    # Admin Remark
    admin_remark = db.Column(
        db.Text,
        nullable=True
    )


# ============================================================
# PRESCRIPTION MODEL
# ============================================================

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_name = db.Column(
        db.String(150),
        nullable=False
    )

    medicine_name = db.Column(
        db.String(150),
        nullable=False
    )

    dosage = db.Column(
        db.String(100),
        nullable=False
    )

    doctor_name = db.Column(
        db.String(150),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )


# ============================================================
# AMBULANCE UNIT MODEL
# ============================================================

class AmbulanceUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    vehicle_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    vehicle_type = db.Column(
        db.String(100),
        nullable=False
    )

    crew_assigned = db.Column(
        db.String(200),
        nullable=False
    )

    current_destination = db.Column(
        db.String(200),
        nullable=True
    )

    status = db.Column(
        db.String(50),
        default="Available"
    )

    latitude = db.Column(
        db.Float,
        default=18.6298
    )

    longitude = db.Column(
        db.Float,
        default=73.7997
    )


# ============================================================
# NOTIFICATION MODEL
# ============================================================


# ============================================================
# AMBULANCE BOOKING MODEL
# ============================================================

class AmbulanceBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patient.id"),
        nullable=False
    )

    ambulance_id = db.Column(
        db.Integer,
        db.ForeignKey("ambulance_unit.id"),
        nullable=False
    )

    emergency_category = db.Column(
        db.String(100),
        nullable=False,
        default="Emergency"
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    pickup_location = db.Column(
        db.String(255),
        nullable=False
    )

    pickup_latitude = db.Column(
        db.Float,
        nullable=True
    )

    pickup_longitude = db.Column(
        db.Float,
        nullable=True
    )

    destination = db.Column(
        db.String(255),
        nullable=True
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="Pending"
    )

    accepted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)

    target_audience = db.Column(
        db.String(100),
        nullable=False
    )

    severity = db.Column(
        db.String(50),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )


# ============================================================
# WARD MODEL
# ============================================================

class Ward(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    hospital_name = db.Column(
        db.String(150),
        nullable=False
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    type = db.Column(
        db.String(100),
        nullable=False
    )

    total_beds = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    occupied_beds = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )


# ============================================================
# MEDICINE MODEL
# ============================================================

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=False
    )

    stock = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="In Stock"
    )


# ============================================================
# LAB TEST MODEL
# ============================================================

class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_name = db.Column(
        db.String(100),
        nullable=False
    )

    test_name = db.Column(
        db.String(100),
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="Pending"
    )

    date_requested = db.Column(
        db.String(50),
        nullable=False
    )

    doctor_name = db.Column(
        db.String(100)
    )

    priority = db.Column(
        db.String(50)
    )

    notes = db.Column(
        db.Text
    )

    sample_type = db.Column(
        db.String(50)
    )

    appointment_id = db.Column(
        db.Integer
    )

    result = db.Column(
        db.String(100)
    )

    unit = db.Column(
        db.String(30)
    )

    reference_range = db.Column(
        db.String(50)
    )

    interpretation = db.Column(
        db.String(50)
    )

    remarks = db.Column(
        db.Text
    )

    verified_by = db.Column(
        db.String(100)
    )

    completed_date = db.Column(
        db.String(50)
    )


# ============================================================
# PATIENT MODEL
# ============================================================

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

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    age = db.Column(
        db.Integer,
        nullable=True
    )

    gender = db.Column(
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

    emergency_contact = db.Column(
        db.String(20),
        nullable=True
    )

    medical_history = db.Column(
        db.Text,
        nullable=True
    )


# ============================================================
# AMBULANCE BOOKING MODEL
# ============================================================
# Patient creates a booking.
# The booking is linked to both the patient and ambulance.
# Driver/ambulance dashboard can use this information.
# ============================================================

class Report(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

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

    # Laboratory report fields
    result = db.Column(
        db.String(100)
    )

    unit = db.Column(
        db.String(50)
    )

    reference_range = db.Column(
        db.String(100)
    )

    interpretation = db.Column(
        db.Text
    )

    remarks = db.Column(
        db.Text
    )

    verified_by = db.Column(
        db.String(100)
    )


# ============================================================
# DOCTOR MODEL
# ============================================================

class Doctor(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(15),
        unique=True
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )


# ============================================================
# APPOINTMENT MODEL
# ============================================================

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


# ============================================================
# AUDIT LOG MODEL
# ============================================================

class AuditLog(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    admin_user = db.Column(
        db.String(100),
        nullable=False
    )

    action = db.Column(
        db.String(255),
        nullable=False
    )

    event_scope = db.Column(
        db.String(150),
        nullable=False
    )

    target_reference = db.Column(
        db.String(200),
        nullable=False
    )

    details = db.Column(
        db.String(300)
    )

    security_level = db.Column(
        db.String(50),
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# ============================================================
# ANALYZER MODEL
# ============================================================

class Analyzer(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        nullable=False
    )
