from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas, auth
from database import get_db
from priority import PriorityScorer
from predictor import predictor
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patient", tags=["patient"])
scorer = PriorityScorer()

def require_patient(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != models.UserRole.patient:
        raise HTTPException(status_code=403, detail="Require patient role")
    return current_user

@router.get("/profile", response_model=schemas.PatientResponse)
def get_profile(current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    return patient

@router.put("/profile", response_model=schemas.PatientResponse)
def update_profile(req: schemas.PatientBase, current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    
    if req.date_of_birth is not None:
        patient.date_of_birth = req.date_of_birth
    if req.blood_group is not None:
        patient.blood_group = req.blood_group
    if req.medical_history is not None:
        patient.medical_history = req.medical_history
    if req.symptoms is not None:
        patient.symptoms = req.symptoms
        score_data = scorer.score(patient.symptoms)
        patient.priority_score = score_data["priority_score"]
        
    db.commit()
    db.refresh(patient)
    return patient

@router.get("/doctors", response_model=List[schemas.DoctorResponse])
def list_doctors(specialization: Optional[str] = None, clinic_id: Optional[int] = None, day_of_week: Optional[str] = None, current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    query = db.query(models.Doctor).filter(models.Doctor.is_available == True)
    if specialization:
        query = query.filter(models.Doctor.specialization.ilike(f"%{specialization}%"))
    if clinic_id:
        query = query.join(models.DoctorRoster).filter(models.DoctorRoster.clinic_id == clinic_id)
        if day_of_week:
            query = query.filter(models.DoctorRoster.day_of_week == day_of_week)
    return query.all()

@router.get("/doctors/{doctor_id}/slots", response_model=List[schemas.DoctorSlotResponse])
def get_doctor_slots(doctor_id: int, date: str, current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    slots = db.query(models.DoctorSlot).filter(
        models.DoctorSlot.doctor_id == doctor_id,
        models.DoctorSlot.date == date,
        models.DoctorSlot.is_booked == False
    ).all()
    return slots

@router.post("/appointments", response_model=schemas.AppointmentResponse)
def book_appointment(req: schemas.AppointmentCreate, current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    logger.info(f"[STAGE 1: INIT] Patient {current_user.id} requested to book appointment with Doctor {req.doctor_id} on {req.appointment_date} at {req.appointment_time}")
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    doctor = db.query(models.Doctor).filter(models.Doctor.id == req.doctor_id).first()
    if not doctor:
        logger.warning(f"Doctor {req.doctor_id} not found")
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    clinic = db.query(models.Clinic).filter(models.Clinic.id == req.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    try:
        appt_date_obj = datetime.strptime(req.appointment_date, "%Y-%m-%d").date()
        appt_time_obj = datetime.strptime(req.appointment_time, "%H:%M").time()
    except ValueError:
        logger.error("Invalid date/time format submitted")
        raise HTTPException(status_code=400, detail="Invalid date/time format")
        
    logger.info("[STAGE 2: VALIDATION] Checking for doctor leaves and roster conflicts")
        
    # Check for Doctor Leave conflicts
    leave_conflict = db.query(models.DoctorLeave).filter(
        models.DoctorLeave.doctor_id == req.doctor_id,
        models.DoctorLeave.start_date <= appt_date_obj,
        models.DoctorLeave.end_date >= appt_date_obj
    ).first()
    if leave_conflict:
        logger.warning(f"Booking rejected: Doctor is on leave ({leave_conflict.reason})")
        raise HTTPException(status_code=400, detail=f"Doctor is on leave ({leave_conflict.reason}) on this date")
        
    # Check Roster / availability and LOCK it to prevent race conditions (Double Booking)
    logger.info("[STAGE 3: LOCKING] Acquiring pessimistic lock on DoctorRoster to prevent double booking")
    day_name = appt_date_obj.strftime("%A")
    roster = db.query(models.DoctorRoster).filter(
        models.DoctorRoster.doctor_id == req.doctor_id,
        models.DoctorRoster.clinic_id == req.clinic_id,
        models.DoctorRoster.day_of_week == day_name
    ).with_for_update().first()
    
    if not roster:
        raise HTTPException(status_code=400, detail=f"Doctor is not available at this clinic on {day_name}s")
        
    if appt_time_obj < roster.start_time or appt_time_obj >= roster.end_time:
        raise HTTPException(status_code=400, detail="Appointment time is outside doctor's working hours at this clinic")
        
    # Since we hold the lock on the Roster, we can safely check for double bookings
    existing_appt = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == req.doctor_id,
        models.Appointment.appointment_date == req.appointment_date,
        models.Appointment.appointment_time == req.appointment_time,
        models.Appointment.status != models.AppointmentStatus.cancelled
    ).first()
    
    if existing_appt:
        logger.warning(f"Booking rejected: Time slot {req.appointment_time} is already booked")
        raise HTTPException(status_code=400, detail="This time slot was just booked by another patient. Please choose another slot.")
        
    logger.info("[STAGE 4: TRIAGE] Calculating priority score based on symptoms")
    # Enforce 15-minute slot boundary roughly
    if appt_time_obj.minute not in [0, 15, 30, 45]:
         raise HTTPException(status_code=400, detail="Appointments must be booked in 15-minute slots (e.g., 10:00, 10:15)")

    if req.slot_id:
        slot = db.query(models.DoctorSlot).filter(models.DoctorSlot.id == req.slot_id, models.DoctorSlot.is_booked == False).first()
        if not slot:
            raise HTTPException(status_code=400, detail="Slot not available")
        slot.is_booked = True
        
    # Auto-assign token number for doctor+date+clinic
    existing_count = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == req.doctor_id,
        models.Appointment.clinic_id == req.clinic_id,
        models.Appointment.appointment_date == req.appointment_date
    ).count()
    token_number = existing_count + 1
    
    score_data = scorer.score(req.symptoms_at_booking)
    priority_score = score_data["priority_score"]
    
    # Check queue length
    queue_length = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == req.doctor_id,
        models.Appointment.clinic_id == req.clinic_id,
        models.Appointment.appointment_date == req.appointment_date,
        models.Appointment.status.in_([models.AppointmentStatus.waiting, models.AppointmentStatus.in_progress])
    ).count()
    
    # Update patient symptoms and score if new
    patient.symptoms = req.symptoms_at_booking
    patient.priority_score = priority_score
    
    # Predict wait time
    try:
        appt_datetime = datetime.strptime(f"{req.appointment_date} {req.appointment_time}", "%Y-%m-%d %H:%M")
    except:
        appt_datetime = datetime.now()
        
    predicted_wait, _ = predictor.predict(doctor.avg_consult_mins, priority_score, appt_datetime, queue_length)
    logger.info(f"[STAGE 5: PREDICTION] Generated token {token_number} with predicted wait of {predicted_wait} mins for priority score {priority_score}")
    
    appointment = models.Appointment(
        patient_id=patient.id,
        doctor_id=req.doctor_id,
        clinic_id=req.clinic_id,
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
    
    # Notification
    notif_msg = f"Your appointment is confirmed. Token #{token_number}. Estimated wait: {int(predicted_wait)} mins"
    notif = models.Notification(
        user_id=current_user.id,
        type="SMS",
        message=notif_msg,
        status=models.NotificationStatus.sent,
        sent_at=datetime.utcnow()
    )
    db.add(notif)
    logger.info(f"📱 SMS to {current_user.phone}: {notif_msg}")
    
    db.commit()
    db.refresh(appointment)
    logger.info(f"[STAGE 6: COMPLETE] Appointment {appointment.id} successfully booked!")
    return appointment

@router.get("/appointments", response_model=List[schemas.AppointmentResponse])
def get_my_appointments(current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    appts = db.query(models.Appointment).filter(models.Appointment.patient_id == patient.id).order_by(models.Appointment.created_at.desc()).all()
    return appts

@router.get("/appointments/{id}", response_model=schemas.AppointmentResponse)
def get_appointment_detail(id: int, current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    appt = db.query(models.Appointment).filter(models.Appointment.id == id, models.Appointment.patient_id == patient.id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt

@router.delete("/appointments/{id}")
def cancel_appointment(id: int, current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    appt = db.query(models.Appointment).filter(models.Appointment.id == id, models.Appointment.patient_id == patient.id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appt.status = models.AppointmentStatus.cancelled
    if appt.slot_id:
        slot = db.query(models.DoctorSlot).filter(models.DoctorSlot.id == appt.slot_id).first()
        if slot:
            slot.is_booked = False
            
    db.commit()
    return {"message": "Cancelled successfully"}

@router.get("/queue-status/{doctor_id}")
def get_queue_status(doctor_id: int, current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    my_appt = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.patient_id == patient.id,
        models.Appointment.appointment_date == today_str,
        models.Appointment.status.in_([models.AppointmentStatus.waiting, models.AppointmentStatus.scheduled])
    ).first()
    
    all_waiting = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_date == today_str,
        models.Appointment.status == models.AppointmentStatus.waiting
    ).order_by(models.Appointment.priority_score.desc(), models.Appointment.token_number.asc()).all()
    
    people_ahead = 0
    if my_appt and my_appt.status == models.AppointmentStatus.waiting:
        for a in all_waiting:
            if a.id == my_appt.id:
                break
            people_ahead += 1
            
    return {
        "my_appointment": my_appt.id if my_appt else None,
        "status": my_appt.status if my_appt else None,
        "token": my_appt.token_number if my_appt else None,
        "people_ahead": people_ahead,
        "predicted_wait": my_appt.predicted_wait_mins if my_appt else 0
    }

@router.get("/notifications", response_model=List[schemas.NotificationResponse])
def get_notifications(current_user: models.User = Depends(require_patient), db: Session = Depends(get_db)):
    notifs = db.query(models.Notification).filter(models.Notification.user_id == current_user.id).order_by(models.Notification.created_at.desc()).all()
    return notifs
