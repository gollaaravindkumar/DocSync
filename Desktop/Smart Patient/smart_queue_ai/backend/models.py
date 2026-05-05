from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum, DateTime, Text, Date, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    doctor = "doctor"
    patient = "patient"
    receptionist = "receptionist"

class AppointmentStatus(str, enum.Enum):
    booked = "booked"
    waiting = "waiting"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    noshow = "noshow"

class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    password_hash = Column(String)
    role = Column(Enum(UserRole))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    patient_profile = relationship("Patient", back_populates="user", uselist=False)
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)

class Clinic(Base):
    __tablename__ = "clinics"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rosters = relationship("DoctorRoster", back_populates="clinic")
    appointments = relationship("Appointment", back_populates="clinic")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date_of_birth = Column(String) # YYYY-MM-DD
    blood_group = Column(String)
    medical_history = Column(Text)
    symptoms = Column(Text)
    priority_score = Column(Integer, default=1) # 1-5
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="patient_profile")
    appointments = relationship("Appointment", back_populates="patient")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    specialization = Column(String)
    qualification = Column(String)
    experience_years = Column(Integer)
    avg_consult_mins = Column(Float, default=15.0) # Changed default to 15.0 per the prompt requirements
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="doctor_profile")
    slots = relationship("DoctorSlot", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")
    leaves = relationship("DoctorLeave", back_populates="doctor")
    rosters = relationship("DoctorRoster", back_populates="doctor")

class DoctorLeave(Base):
    __tablename__ = "doctor_leaves"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(String) # Sick Leave, Conference, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    doctor = relationship("Doctor", back_populates="leaves")

class DoctorRoster(Base):
    __tablename__ = "doctor_rosters"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    clinic_id = Column(Integer, ForeignKey("clinics.id"))
    day_of_week = Column(String) # e.g., 'Monday'
    start_time = Column(Time)
    end_time = Column(Time)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    doctor = relationship("Doctor", back_populates="rosters")
    clinic = relationship("Clinic", back_populates="rosters")

class DoctorSlot(Base):
    __tablename__ = "doctor_slots"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    date = Column(String) # YYYY-MM-DD
    start_time = Column(String) # HH:MM
    end_time = Column(String) # HH:MM
    is_booked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    doctor = relationship("Doctor", back_populates="slots")
    appointment = relationship("Appointment", back_populates="slot", uselist=False)

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    clinic_id = Column(Integer, ForeignKey("clinics.id"))
    slot_id = Column(Integer, ForeignKey("doctor_slots.id"), nullable=True)
    booking_time = Column(DateTime(timezone=True), server_default=func.now())
    appointment_date = Column(String) # YYYY-MM-DD
    appointment_time = Column(String) # HH:MM
    token_number = Column(Integer)
    predicted_wait_mins = Column(Float)
    actual_wait_mins = Column(Float, nullable=True)
    symptoms_at_booking = Column(Text)
    priority_score = Column(Integer) # 1-5
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.booked)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    clinic = relationship("Clinic", back_populates="appointments")
    slot = relationship("DoctorSlot", back_populates="appointment")
    queue_log = relationship("QueueLog", back_populates="appointment", uselist=False)

class QueueLog(Base):
    __tablename__ = "queue_logs"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    arrival_time = Column(DateTime(timezone=True), default=func.now())
    consultation_start = Column(DateTime(timezone=True), nullable=True)
    consultation_end = Column(DateTime(timezone=True), nullable=True)
    actual_wait_mins = Column(Float, nullable=True)
    actual_consult_mins = Column(Float, nullable=True)
    queue_length_at_arrival = Column(Integer)
    priority_score = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    appointment = relationship("Appointment", back_populates="queue_log")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)
    message = Column(Text)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.pending)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
