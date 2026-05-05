import logging
import sys

# Configure logging to write to both the terminal and a file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("docsync.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, get_db
import models
from routers import auth, patients, doctors, admin, receptionist, queue, notifications, clinics
from predictor import predictor

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DocSync")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(admin.router)
app.include_router(receptionist.router)
app.include_router(queue.router)
app.include_router(notifications.router)
app.include_router(clinics.router)

@app.on_event("startup")
def startup_event():
    # Load ML model with existing queue logs
    from sqlalchemy.orm import Session
    from database import SessionLocal
    db = SessionLocal()
    try:
        logs = db.query(models.QueueLog).all()
        predictor.train(logs)
        print(f"Predictor initialized. Trained: {predictor.is_trained}, Size: {predictor.training_size}")
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "DocSync running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
