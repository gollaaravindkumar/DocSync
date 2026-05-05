import os
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from auth import hash_password
from datetime import datetime, timedelta, date, time
import random

def seed_data():
    # Because the schema has fundamentally changed, we will drop and recreate
    # This is safe because it's just the seed script for local dev.
    print("Recreating database schema to match new Multi-Clinic Models...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Seeding database...")
        
        # 1. Admin
        admin_user = models.User(
            name="System Admin", email="admin@smartqueue.com", phone="1111111111",
            password_hash=hash_password("admin123"), role=models.UserRole.admin
        )
        db.add(admin_user)
        
        # 2. Receptionist
        receptionist_user = models.User(
            name="Front Desk", email="reception@smartqueue.com", phone="2222222222",
            password_hash=hash_password("reception123"), role=models.UserRole.receptionist
        )
        db.add(receptionist_user)
        db.commit()

        # 3. Clinics
        clinics_data = [
            ("City Central Clinic", "123 Main St, Downtown"),
            ("Northside Pediatrics & Gen", "456 North Blvd"),
            ("WestEnd Specialist Center", "789 West Ave")
        ]
        db_clinics = []
        for name, address in clinics_data:
            clinic = models.Clinic(name=name, address=address)
            db.add(clinic)
            db.commit()
            db.refresh(clinic)
            db_clinics.append(clinic)

        # 4. Doctors
        doctors_data = [
            ("Dr. Priya Sharma", "priya@smartqueue.com", "Cardiology", 15, 15.0),
            ("Dr. Arjun Mehta", "arjun@smartqueue.com", "Neurology", 10, 15.0),
            ("Dr. Kavitha Nair", "kavitha@smartqueue.com", "General Medicine", 8, 15.0),
            ("Dr. Ravi Kumar", "ravi@smartqueue.com", "Orthopedics", 12, 15.0),
            ("Dr. Ananya Krishnan", "ananya@smartqueue.com", "Pediatrics", 6, 15.0),
            ("Dr. Suresh Patel", "suresh@smartqueue.com", "Gynecology", 20, 15.0), # Added Gynecology per prompt
        ]
        db_doctors = []
        for name, email, spec, exp, consult_time in doctors_data:
            doc_user = models.User(
                name=name, email=email, phone="3334445555",
                password_hash=hash_password("doctor123"), role=models.UserRole.doctor
            )
            db.add(doc_user)
            db.commit()
            db.refresh(doc_user)
            doc_profile = models.Doctor(
                user_id=doc_user.id, specialization=spec,
                qualification="MD", experience_years=exp, avg_consult_mins=consult_time
            )
            db.add(doc_profile)
            db.commit()
            db.refresh(doc_profile)
            db_doctors.append(doc_profile)

        # 5. Doctor Rosters (Availability in clinics)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for doc in db_doctors:
            # Assign each doctor to 1-2 clinics on different days
            assigned_clinics = random.sample(db_clinics, k=random.randint(1, 2))
            for i, clinic in enumerate(assigned_clinics):
                for day in days[i*3:(i+1)*3]: # 3 days per clinic
                    roster = models.DoctorRoster(
                        doctor_id=doc.id, clinic_id=clinic.id,
                        day_of_week=day, start_time=time(9, 0), end_time=time(17, 0)
                    )
                    db.add(roster)
        db.commit()

        # 6. Doctor Leaves
        today = date.today()
        # Give Dr. Priya a leave next week
        leave = models.DoctorLeave(
            doctor_id=db_doctors[0].id,
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=10),
            reason="Conference"
        )
        db.add(leave)
        db.commit()

        # 7. Patients
        patients_symptoms = [
            ("chest pain and shortness of breath", 5),
            ("severe bleeding from deep cut", 4),
            ("high fever and difficulty breathing", 4),
            ("persistent cough and fever", 3),
            ("moderate pain in knee", 3),
            ("mild headache and fatigue", 2),
            ("sore throat and cold", 2),
            ("routine checkup", 1),
            ("prescription refill", 1),
            ("follow-up consultation", 1)
        ]
        db_patients = []
        for i, (sym, score) in enumerate(patients_symptoms):
            pat_user = models.User(
                name=f"Patient {i+1}", email=f"patient{i+1}@example.com", phone=f"99988877{i:02d}",
                password_hash=hash_password("patient123"), role=models.UserRole.patient
            )
            db.add(pat_user)
            db.commit()
            db.refresh(pat_user)
            pat_profile = models.Patient(
                user_id=pat_user.id, date_of_birth="1990-01-01",
                symptoms=sym, priority_score=score
            )
            db.add(pat_profile)
            db.commit()
            db.refresh(pat_profile)
            db_patients.append(pat_profile)

        # 8. Appointments & Queue Logs
        today_dt = datetime.now()
        yesterday_dt = today_dt - timedelta(days=1)
        
        for i in range(30):
            doc = random.choice(db_doctors)
            pat = random.choice(db_patients)
            # Find a clinic this doctor works at
            roster = db.query(models.DoctorRoster).filter(models.DoctorRoster.doctor_id == doc.id).first()
            clinic_id = roster.clinic_id if roster else db_clinics[0].id

            appt_date = yesterday_dt.strftime("%Y-%m-%d") if i < 15 else today_dt.strftime("%Y-%m-%d")
            status = models.AppointmentStatus.completed if i < 20 else models.AppointmentStatus.waiting
            
            appt = models.Appointment(
                patient_id=pat.id,
                doctor_id=doc.id,
                clinic_id=clinic_id,
                appointment_date=appt_date,
                appointment_time=f"{9 + (i%8):02d}:00",
                token_number=(i%10)+1,
                predicted_wait_mins=15.0,
                symptoms_at_booking=pat.symptoms,
                priority_score=pat.priority_score,
                status=status
            )
            db.add(appt)
            db.commit()
            db.refresh(appt)
            
            # Queue log
            queue_len = random.randint(0, 5)
            actual_wait = None
            actual_consult = None
            if status == models.AppointmentStatus.completed:
                actual_wait = float(queue_len * doc.avg_consult_mins * random.uniform(0.8, 1.2))
                actual_consult = float(doc.avg_consult_mins * random.uniform(0.8, 1.2))
                
            q_log = models.QueueLog(
                appointment_id=appt.id,
                doctor_id=doc.id,
                arrival_time=today_dt - timedelta(hours=random.randint(1,4)),
                queue_length_at_arrival=queue_len,
                priority_score=pat.priority_score,
                actual_wait_mins=actual_wait,
                actual_consult_mins=actual_consult
            )
            db.add(q_log)
            db.commit()
            
        print("Database seeding completed successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
