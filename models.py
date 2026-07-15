from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy object
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    department = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default='Active')

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(150), nullable=False)
    medicine_name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), default='Pending')

class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(150), nullable=False)
    test_modality = db.Column(db.String(150), nullable=False)
    requested_by = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), default='Awaiting Sample')

class AmbulanceUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(50), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(100), nullable=False)
    crew_assigned = db.Column(db.String(200), nullable=False)
    current_destination = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default='Available')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_audience = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)