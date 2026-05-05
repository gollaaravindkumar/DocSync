from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas, auth
from database import get_db
from datetime import datetime
from websockets_manager import manager

router = APIRouter(prefix="/doctor", tags=["doctor"])

def require_doctor(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != models.UserRole.doctor:
        raise HTTPException(status_code=403, detail="Require doctor role")
    return current_user

@router.get("/profile", response_model=schemas.DoctorResponse)
def get_profile(current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    return doctor

@router.put("/profile", response_model=schemas.DoctorResponse)
def update_profile(req: schemas.DoctorBase, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    doctor.specialization = req.specialization
    doctor.qualification = req.qualification
    doctor.experience_years = req.experience_years
    doctor.avg_consult_mins = req.avg_consult_mins
    db.commit()
    db.refresh(doctor)
    return doctor

@router.put("/availability")
def toggle_availability(is_available: bool, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    doctor.is_available = is_available
    db.commit()
    return {"is_available": doctor.is_available}

@router.post("/slots", response_model=schemas.DoctorSlotResponse)
def create_slot(req: schemas.DoctorSlotCreate, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    slot = models.DoctorSlot(
        doctor_id=doctor.id,
        date=req.date,
        start_time=req.start_time,
        end_time=req.end_time
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot

@router.get("/slots", response_model=List[schemas.DoctorSlotResponse])
def get_slots(date: Optional[str] = None, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    query = db.query(models.DoctorSlot).filter(models.DoctorSlot.doctor_id == doctor.id)
    if date:
        query = query.filter(models.DoctorSlot.date == date)
    return query.all()

@router.delete("/slots/{id}")
def delete_slot(id: int, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    slot = db.query(models.DoctorSlot).filter(models.DoctorSlot.id == id, models.DoctorSlot.doctor_id == doctor.id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.is_booked:
        raise HTTPException(status_code=400, detail="Cannot delete booked slot")
    db.delete(slot)
    db.commit()
    return {"message": "Deleted"}

@router.get("/appointments", response_model=List[schemas.AppointmentResponse])
def get_appointments(date: Optional[str] = None, status: Optional[models.AppointmentStatus] = None, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    query = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor.id)
    if date:
        query = query.filter(models.Appointment.appointment_date == date)
    if status:
        query = query.filter(models.Appointment.status == status)
    return query.order_by(models.Appointment.appointment_time.asc()).all()

@router.put("/appointments/{id}")
def update_appointment(id: int, notes: str, status: models.AppointmentStatus, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    appt = db.query(models.Appointment).filter(models.Appointment.id == id, models.Appointment.doctor_id == doctor.id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.notes = notes
    appt.status = status
    db.commit()
    return {"message": "Updated"}

@router.get("/queue")
def get_live_queue(current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    appts = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.id,
        models.Appointment.appointment_date == today_str,
        models.Appointment.status.in_([models.AppointmentStatus.waiting, models.AppointmentStatus.in_progress])
    ).order_by(models.Appointment.priority_score.desc(), models.Appointment.token_number.asc()).all()
    
    in_progress = [a for a in appts if a.status == models.AppointmentStatus.in_progress]
    waiting = [a for a in appts if a.status == models.AppointmentStatus.waiting]
    
    result = []
    if in_progress:
        a = in_progress[0]
        result.append({
            "id": a.id,
            "token": a.token_number,
            "patient_name": a.patient.user.name,
            "priority": a.priority_score,
            "symptoms": a.symptoms_at_booking,
            "wait_time": a.predicted_wait_mins,
            "status": a.status
        })
    for a in waiting:
        result.append({
            "id": a.id,
            "token": a.token_number,
            "patient_name": a.patient.user.name,
            "priority": a.priority_score,
            "symptoms": a.symptoms_at_booking,
            "wait_time": a.predicted_wait_mins,
            "status": a.status
        })
        
    return result

@router.put("/queue/{appointment_id}/next")
def call_next(appointment_id: int, background_tasks: BackgroundTasks, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    
    # Complete current in_progress
    current_in_progress = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.id,
        models.Appointment.status == models.AppointmentStatus.in_progress
    ).first()
    
    now = datetime.now()
    
    if current_in_progress:
        current_in_progress.status = models.AppointmentStatus.completed
        log = db.query(models.QueueLog).filter(models.QueueLog.appointment_id == current_in_progress.id).first()
        if log:
            log.consultation_end = now
            if log.consultation_start:
                start_naive = log.consultation_start.replace(tzinfo=None) if log.consultation_start.tzinfo else log.consultation_start
                diff = now - start_naive
                log.actual_consult_mins = diff.total_seconds() / 60.0
                
        # Send Thank You Message via Twilio WhatsApp
        import os
        from twilio.rest import Client
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        from_num = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        
        phone = current_in_progress.patient.user.phone
        notif_msg = f"Thank you for visiting {doctor.user.name} at DocSync! We are happy to serve you and wish you a speedy recovery! 🌟"
        
        if sid and token and phone:
            if not phone.startswith("+"):
                phone = "+91" + phone
            try:
                client = Client(sid, token)
                message = client.messages.create(
                    body=notif_msg,
                    from_=from_num,
                    to=f"whatsapp:{phone}"
                )
                print(f"✅ Twilio WhatsApp Thank You sent to {phone}: {message.sid}")
            except Exception as e:
                print(f"❌ Twilio WhatsApp Error: {e}")
        else:
            print(f"📱 WhatsApp (Simulated) to {phone}: {notif_msg}")
                
    if appointment_id == 0:
        db.commit()
        background_tasks.add_task(manager.broadcast_queue_update, doctor.id)
        return {"message": "Success"}
        
    # Next appointment
    next_appt = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id,
        models.Appointment.doctor_id == doctor.id
    ).first()
    
    if not next_appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    next_appt.status = models.AppointmentStatus.in_progress
    log = db.query(models.QueueLog).filter(models.QueueLog.appointment_id == next_appt.id).first()
    if log:
        log.consultation_start = now
        arrival_naive = log.arrival_time.replace(tzinfo=None) if log.arrival_time.tzinfo else log.arrival_time
        diff = now - arrival_naive
        log.actual_wait_mins = diff.total_seconds() / 60.0
        
    # Try sending via Twilio WhatsApp
    import os
    from twilio.rest import Client
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    
    phone = next_appt.patient.user.phone
    notif_msg = f"🔔 The Doctor is ready for you! Please proceed to {doctor.user.name}'s room. Token #{next_appt.token_number}."
    if sid and token and phone:
        if not phone.startswith("+"):
            phone = "+91" + phone
        try:
            client = Client(sid, token)
            message = client.messages.create(
                body=notif_msg,
                from_=from_num,
                to=f"whatsapp:{phone}"
            )
            print(f"✅ Twilio WhatsApp sent to {phone}: {message.sid}")
        except Exception as e:
            print(f"❌ Twilio WhatsApp Error: {e}")
    else:
        print(f"📱 WhatsApp (Simulated) to {phone}: {notif_msg}")

    db.commit()
    background_tasks.add_task(manager.broadcast_queue_update, doctor.id)
    return {"message": "Success"}

@router.post("/leaves", response_model=schemas.DoctorLeaveResponse)
def create_leave(req: schemas.DoctorLeaveCreate, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    leave = models.DoctorLeave(
        doctor_id=doctor.id,
        start_date=req.start_date,
        end_date=req.end_date,
        reason=req.reason
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave

@router.get("/search_availability")
def search_availability(doctor_name: Optional[str] = None, speciality: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.DoctorRoster).join(models.Doctor).join(models.User).join(models.Clinic)
    if doctor_name:
        query = query.filter(models.User.name.ilike(f"%{doctor_name}%"))
    if speciality:
        query = query.filter(models.Doctor.specialization.ilike(f"%{speciality}%"))
    
    rosters = query.all()
    result = []
    for r in rosters:
        result.append({
            "doctor_name": r.doctor.user.name,
            "speciality": r.doctor.specialization,
            "clinic_name": r.clinic.name,
            "day": r.day_of_week,
            "available_time": f"{r.start_time.strftime('%I:%M %p')} - {r.end_time.strftime('%I:%M %p')}"
        })
    return result

@router.get("/utilization")
def get_utilization(clinic_id: int, current_user: models.User = Depends(require_doctor), db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    
    # We count the actual appointments booked for this doctor at this clinic
    booked_slots = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.id,
        models.Appointment.clinic_id == clinic_id,
        models.Appointment.status.in_([models.AppointmentStatus.booked, models.AppointmentStatus.waiting, models.AppointmentStatus.in_progress, models.AppointmentStatus.completed])
    ).count()
    
    # A realistic approximation of total slots based on their roster
    rosters = db.query(models.DoctorRoster).filter(models.DoctorRoster.doctor_id == doctor.id, models.DoctorRoster.clinic_id == clinic_id).all()
    total_slots = 0
    # For a real system we'd calculate exact slot capacity over a time period, here we just show a daily average
    # assuming 1 month of capacity for demonstration purposes.
    if rosters:
        total_slots = 20 * len(rosters) * 4 # roughly 20 patients a day * days worked * 4 weeks
        
    if total_slots == 0:
        return {"utilization_percent": 0.0, "total_slots": 0, "booked_slots": booked_slots}
    
    utilization = (booked_slots / total_slots) * 100.0
    return {"utilization_percent": round(utilization, 2), "total_slots": total_slots, "booked_slots": booked_slots}
