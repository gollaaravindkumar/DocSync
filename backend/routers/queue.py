from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas, auth
from database import get_db
from datetime import datetime
from websockets_manager import manager

router = APIRouter(prefix="/queue", tags=["queue"])

@router.websocket("/ws/{doctor_id}")
async def websocket_queue(websocket: WebSocket, doctor_id: int):
    await manager.connect(websocket, doctor_id)
    try:
        while True:
            # We don't expect the client to send much, but we need to listen
            # to keep the connection open and detect disconnects.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, doctor_id)

@router.get("/{doctor_id}")
def get_doctor_queue(doctor_id: int, db: Session = Depends(get_db)):
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    current = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_date == today_str,
        models.Appointment.status == models.AppointmentStatus.in_progress
    ).first()
    
    waiting = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_date == today_str,
        models.Appointment.status == models.AppointmentStatus.waiting
    ).order_by(models.Appointment.priority_score.desc(), models.Appointment.token_number.asc()).all()
    
    waiting_list = []
    for w in waiting:
        waiting_list.append({
            "token": w.token_number,
            "priority": w.priority_score,
            "wait_time": w.predicted_wait_mins
        })
        
    return {
        "current_token": current.token_number if current else None,
        "waiting": waiting_list
    }
