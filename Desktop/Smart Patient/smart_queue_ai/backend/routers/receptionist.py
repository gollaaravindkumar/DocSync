from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import models, schemas, auth
from database import get_db
from datetime import datetime
from websockets_manager import manager

router = APIRouter(prefix="/receptionist", tags=["receptionist"])

def require_receptionist(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != models.UserRole.receptionist:
        raise HTTPException(status_code=403, detail="Require receptionist role")
    return current_user

@router.get("/appointments", response_model=List[schemas.AppointmentResponse])
def today_appointments(current_user: models.User = Depends(require_receptionist), db: Session = Depends(get_db)):
    today_str = datetime.now().strftime("%Y-%m-%d")
    appts = db.query(models.Appointment).filter(models.Appointment.appointment_date == today_str).order_by(models.Appointment.appointment_time.asc()).all()
    return appts

@router.post("/checkin/{appointment_id}")
def check_in(appointment_id: int, background_tasks: BackgroundTasks, current_user: models.User = Depends(require_receptionist), db: Session = Depends(get_db)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if appt.status not in [models.AppointmentStatus.booked, models.AppointmentStatus.waiting]:
        raise HTTPException(status_code=400, detail="Can only check in booked appointments")
        
    appt.status = models.AppointmentStatus.waiting
    
    # queue length
    today_str = datetime.now().strftime("%Y-%m-%d")
    queue_length = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == appt.doctor_id,
        models.Appointment.appointment_date == today_str,
        models.Appointment.status.in_([models.AppointmentStatus.waiting, models.AppointmentStatus.in_progress])
    ).count()
    
    log = models.QueueLog(
        appointment_id=appt.id,
        doctor_id=appt.doctor_id,
        queue_length_at_arrival=queue_length,
        priority_score=appt.priority_score
    )
    db.add(log)
    
    notif_msg = f"Your DocSync appointment is confirmed! You are checked in. Token #{appt.token_number}."
    notif = models.Notification(
        user_id=appt.patient.user.id,
        type="SMS",
        message=notif_msg,
        status=models.NotificationStatus.sent,
        sent_at=datetime.utcnow()
    )
    db.add(notif)
    
    # Try sending via Twilio WhatsApp
    import os
    from twilio.rest import Client
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_num = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    
    phone = appt.patient.user.phone
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
    background_tasks.add_task(manager.broadcast_queue_update, appt.doctor_id)
    return {"message": "Checked in successfully"}

@router.get("/queue")
def all_doctor_queues(current_user: models.User = Depends(require_receptionist), db: Session = Depends(get_db)):
    today_str = datetime.now().strftime("%Y-%m-%d")
    doctors = db.query(models.Doctor).all()
    result = []
    
    for d in doctors:
        waiting = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == d.id,
            models.Appointment.appointment_date == today_str,
            models.Appointment.status == models.AppointmentStatus.waiting
        ).count()
        
        current = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == d.id,
            models.Appointment.appointment_date == today_str,
            models.Appointment.status == models.AppointmentStatus.in_progress
        ).first()
        
        result.append({
            "doctor_name": d.user.name,
            "waiting_count": waiting,
            "current_token": current.token_number if current else None
        })
        
    return result

@router.post("/appointments", response_model=schemas.AppointmentResponse)
def walk_in_booking(req: schemas.AppointmentCreate, patient_id: int, current_user: models.User = Depends(require_receptionist), db: Session = Depends(get_db)):
    from routers.patients import scorer
    from predictor import predictor
    
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    doctor = db.query(models.Doctor).filter(models.Doctor.id == req.doctor_id).first()
    
    if req.slot_id:
        slot = db.query(models.DoctorSlot).filter(models.DoctorSlot.id == req.slot_id, models.DoctorSlot.is_booked == False).first()
        if slot:
            slot.is_booked = True
            
    existing_count = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == req.doctor_id,
        models.Appointment.appointment_date == req.appointment_date
    ).count()
    token_number = existing_count + 1
    
    score_data = scorer.score(req.symptoms_at_booking)
    priority_score = score_data["priority_score"]
    
    queue_length = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == req.doctor_id,
        models.Appointment.appointment_date == req.appointment_date,
        models.Appointment.status.in_([models.AppointmentStatus.waiting, models.AppointmentStatus.in_progress])
    ).count()
    
    try:
        appt_datetime = datetime.strptime(f"{req.appointment_date} {req.appointment_time}", "%Y-%m-%d %H:%M")
    except:
        appt_datetime = datetime.now()
        
    predicted_wait, _ = predictor.predict(doctor.avg_consult_mins, priority_score, appt_datetime, queue_length)
    
    appointment = models.Appointment(
        patient_id=patient.id,
        doctor_id=req.doctor_id,
        slot_id=req.slot_id,
        appointment_date=req.appointment_date,
        appointment_time=req.appointment_time,
        token_number=token_number,
        predicted_wait_mins=predicted_wait,
        symptoms_at_booking=req.symptoms_at_booking,
        priority_score=priority_score,
        status=models.AppointmentStatus.booked,
        notes=req.notes
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment

@router.put("/appointments/{id}")
def update_status(id: int, status: models.AppointmentStatus, current_user: models.User = Depends(require_receptionist), db: Session = Depends(get_db)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Not found")
    appt.status = status
    db.commit()
    return {"message": "Updated"}
