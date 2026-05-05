from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/clinics", tags=["clinics"])

@router.get("/", response_model=List[schemas.ClinicResponse])
def get_all_clinics(db: Session = Depends(get_db)):
    return db.query(models.Clinic).all()

@router.post("/", response_model=schemas.ClinicResponse)
def create_clinic(req: schemas.ClinicCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can create clinics")
    
    clinic = models.Clinic(**req.model_dump())
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic

@router.delete("/{id}")
def delete_clinic(id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can delete clinics")
    
    clinic = db.query(models.Clinic).filter(models.Clinic.id == id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
        
    try:
        db.delete(clinic)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete clinic because it has associated doctors or appointments.")
        
    return {"message": "Clinic deleted successfully"}
