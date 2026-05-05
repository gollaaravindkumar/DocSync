from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List
from datetime import datetime, date, time
from models import UserRole, AppointmentStatus, NotificationStatus

# Base schemas
class UserBase(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ClinicBase(BaseModel):
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)

class ClinicCreate(ClinicBase):
    pass

class ClinicResponse(ClinicBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PatientBase(BaseModel):
    date_of_birth: Optional[str] = None
    blood_group: Optional[str] = None
    medical_history: Optional[str] = None
    symptoms: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    user_id: int
    priority_score: int
    created_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True

class DoctorBase(BaseModel):
    specialization: str = Field(..., min_length=1)
    qualification: str = Field(..., min_length=1)
    experience_years: int = Field(..., ge=0)
    avg_consult_mins: float = 15.0
    is_available: bool = True

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int
    user_id: int
    created_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True

class DoctorLeaveBase(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=1)

    @model_validator(mode='after')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValueError('start_date must be before or equal to end_date')
        return self

class DoctorLeaveCreate(DoctorLeaveBase):
    pass

class DoctorLeaveResponse(DoctorLeaveBase):
    id: int
    doctor_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DoctorRosterBase(BaseModel):
    clinic_id: int
    day_of_week: str # e.g., 'Monday', 'Tuesday'
    start_time: time
    end_time: time

    @model_validator(mode='after')
    def check_times(self):
        if self.start_time >= self.end_time:
            raise ValueError('start_time must be before end_time')
        return self

class DoctorRosterCreate(DoctorRosterBase):
    pass

class DoctorRosterResponse(DoctorRosterBase):
    id: int
    doctor_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DoctorSlotBase(BaseModel):
    date: str
    start_time: str
    end_time: str

class DoctorSlotCreate(DoctorSlotBase):
    pass

class DoctorSlotResponse(DoctorSlotBase):
    id: int
    doctor_id: int
    is_booked: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AdminAddDoctorRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)
    specialization: str
    experience_years: int
    clinic_id: int
    days_of_week: List[str]

class AppointmentBase(BaseModel):
    appointment_date: str
    appointment_time: str
    symptoms_at_booking: str = Field(..., min_length=1)
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    doctor_id: int
    clinic_id: int
    slot_id: Optional[int] = None

class AppointmentResponse(AppointmentBase):
    id: int
    patient_id: int
    doctor_id: int
    clinic_id: Optional[int] = None
    slot_id: Optional[int]
    booking_time: datetime
    token_number: int
    predicted_wait_mins: float
    actual_wait_mins: Optional[float]
    priority_score: int
    status: AppointmentStatus
    created_at: datetime

    class Config:
        from_attributes = True

class QueueLogBase(BaseModel):
    pass

class QueueLogResponse(BaseModel):
    id: int
    appointment_id: int
    doctor_id: int
    arrival_time: datetime
    consultation_start: Optional[datetime]
    consultation_end: Optional[datetime]
    actual_wait_mins: Optional[float]
    actual_consult_mins: Optional[float]
    queue_length_at_arrival: int
    priority_score: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationBase(BaseModel):
    type: str
    message: str

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    status: NotificationStatus
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
