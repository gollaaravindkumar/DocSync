from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import models, schemas, auth
from database import get_db
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Require admin role")
    return current_user
    
from datetime import time

@router.post("/add_doctor_to_clinic")
def admin_add_doctor(req: schemas.AdminAddDoctorRequest, current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    # 1. Create User
    existing = db.query(models.User).filter(models.User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    doc_user = models.User(
        name=req.name,
        email=req.email,
        password_hash=auth.hash_password(req.password),
        role=models.UserRole.doctor
    )
    db.add(doc_user)
    db.commit()
    db.refresh(doc_user)
    
    # 2. Create Doctor Profile
    doc_profile = models.Doctor(
        user_id=doc_user.id,
        specialization=req.specialization,
        qualification="MD",
        experience_years=req.experience_years,
        avg_consult_mins=15.0
    )
    db.add(doc_profile)
    db.commit()
    db.refresh(doc_profile)
    
    # 3. Create Roster for clinic
    for day in req.days_of_week:
        roster = models.DoctorRoster(
            doctor_id=doc_profile.id,
            clinic_id=req.clinic_id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        db.add(roster)
    db.commit()
    return {"message": "Doctor added successfully", "doctor_id": doc_profile.id}

@router.get("/users", response_model=List[schemas.UserResponse])
def get_users(role: Optional[models.UserRole] = None, current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    return query.all()

@router.put("/users/{id}/toggle")
def toggle_user(id: int, current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    return {"is_active": user.is_active}

@router.post("/doctors", response_model=schemas.DoctorResponse)
def create_doctor_profile(user_id: int, req: schemas.DoctorCreate, current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or user.role != models.UserRole.doctor:
        raise HTTPException(status_code=400, detail="User not found or not a doctor")
    
    existing = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile exists")
        
    doctor = models.Doctor(
        user_id=user.id,
        specialization=req.specialization,
        qualification=req.qualification,
        experience_years=req.experience_years,
        avg_consult_mins=req.avg_consult_mins
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

@router.get("/doctors")
def get_admin_doctors(current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    doctors = db.query(models.Doctor).all()
    today_str = datetime.now().strftime("%Y-%m-%d")
    result = []
    for d in doctors:
        count = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == d.id,
            models.Appointment.appointment_date == today_str
        ).count()
        result.append({
            "id": d.id,
            "name": d.user.name,
            "specialization": d.specialization,
            "is_available": d.is_available,
            "today_appointments": count,
            "avg_consult_mins": d.avg_consult_mins
        })
    return result

@router.get("/appointments", response_model=List[schemas.AppointmentResponse])
def get_all_appointments(date: Optional[str] = None, status: Optional[models.AppointmentStatus] = None, doctor_id: Optional[int] = None, current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(models.Appointment)
    if date:
        query = query.filter(models.Appointment.appointment_date == date)
    if status:
        query = query.filter(models.Appointment.status == status)
    if doctor_id:
        query = query.filter(models.Appointment.doctor_id == doctor_id)
    return query.all()

@router.delete("/appointments/{id}")
def admin_cancel_appointment(id: int, current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appt.status = models.AppointmentStatus.cancelled
    if appt.slot_id:
        slot = db.query(models.DoctorSlot).filter(models.DoctorSlot.id == appt.slot_id).first()
        if slot:
            slot.is_booked = False
    db.commit()
    return {"message": "Cancelled"}

@router.get("/stats")
def get_stats(current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    total_patients = db.query(models.Patient).count()
    total_doctors = db.query(models.Doctor).count()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    total_appts_today = db.query(models.Appointment).filter(models.Appointment.appointment_date == today_str).count()
    
    logs_today = db.query(models.QueueLog).join(models.Appointment).filter(
        models.Appointment.appointment_date == today_str,
        models.QueueLog.actual_wait_mins != None
    ).all()
    
    avg_wait = sum([l.actual_wait_mins for l in logs_today]) / len(logs_today) if logs_today else 0.0
    
    waiting = db.query(models.Appointment).filter(
        models.Appointment.appointment_date == today_str,
        models.Appointment.status == models.AppointmentStatus.waiting
    ).count()
    
    busiest = db.query(
        models.Appointment.doctor_id, 
        func.count(models.Appointment.id).label('total')
    ).filter(models.Appointment.appointment_date == today_str).group_by(models.Appointment.doctor_id).order_by(func.count(models.Appointment.id).desc()).first()
    
    busiest_doctor_name = "None"
    if busiest:
        doc = db.query(models.Doctor).filter(models.Doctor.id == busiest.doctor_id).first()
        if doc:
            busiest_doctor_name = doc.user.name
            
    return {
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_appointments_today": total_appts_today,
        "avg_wait_time_today": avg_wait,
        "currently_waiting": waiting,
        "busiest_doctor": busiest_doctor_name
    }

@router.get("/analytics")
def get_analytics(current_user: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    # 1. Priority Distribution Today
    today_str = datetime.now().strftime("%Y-%m-%d")
    appts = db.query(models.Appointment).filter(models.Appointment.appointment_date == today_str).all()
    
    priority_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    status_dist = {"scheduled": 0, "waiting": 0, "in_progress": 0, "completed": 0, "cancelled": 0}
    
    for a in appts:
        priority_dist[a.priority_score] += 1
        status_dist[a.status.value] += 1
        
    return {
        "priority_distribution": priority_dist,
        "status_distribution": status_dist
    }
