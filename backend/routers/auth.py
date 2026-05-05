from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", response_model=schemas.Token)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = auth.hash_password(user.password)
    new_user = models.User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        password_hash=hashed_password,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create profile based on role
    if user.role == models.UserRole.patient:
        patient = models.Patient(user_id=new_user.id)
        db.add(patient)
    elif user.role == models.UserRole.doctor:
        doctor = models.Doctor(user_id=new_user.id)
        db.add(doctor)
        
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not auth.verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = auth.create_access_token(data={"sub": user.email})
    
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role
    }
    
    return {"access_token": access_token, "token_type": "bearer", "user": user_data}

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

class UpdateMeRequest(BaseModel):
    name: str
    phone: str

@router.put("/me", response_model=schemas.UserResponse)
def update_user_me(req: UpdateMeRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    current_user.name = req.name
    current_user.phone = req.phone
    db.commit()
    db.refresh(current_user)
    return current_user
