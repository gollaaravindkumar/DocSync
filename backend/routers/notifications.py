from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth
from database import get_db
from datetime import datetime
import os
from twilio.rest import Client

router = APIRouter(prefix="/notify", tags=["notify"])

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@router.post("/send", response_model=schemas.NotificationResponse)
def send_notification(req: schemas.NotificationBase, user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    notif = models.Notification(
        user_id=user_id,
        type=req.type,
        message=req.message,
        status=models.NotificationStatus.sent,
        sent_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    
    # Try sending via Twilio WhatsApp
    if twilio_client and user.phone:
        # Format phone to E.164 if not already (assuming India +91 for example if not specified)
        phone = user.phone
        if not phone.startswith("+"):
            phone = "+91" + phone # Defaulting to +91 as seen in the screenshots
            
        try:
            message = twilio_client.messages.create(
                body=req.message,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=f"whatsapp:{phone}"
            )
            print(f"✅ Twilio WhatsApp sent to {phone}: SID {message.sid}")
        except Exception as e:
            print(f"❌ Twilio Error: {e}")
    else:
        print(f"📱 (Simulated) {req.type} to {user.phone or user.email}: {req.message}")
        
    return notif

@router.get("/{user_id}", response_model=List[schemas.NotificationResponse])
def get_user_notifications(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Notification).filter(models.Notification.user_id == user_id).order_by(models.Notification.created_at.desc()).all()

@router.put("/{id}/read")
def mark_read(id: int, db: Session = Depends(get_db)):
    notif = db.query(models.Notification).filter(models.Notification.id == id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Not found")
    notif.status = models.NotificationStatus.sent
    db.commit()
    return {"message": "Marked"}
