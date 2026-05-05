import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

class WaitTimePredictor:
    def __init__(self):
        self.model = LinearRegression()
        self.is_trained = False
        self.training_size = 0
        
    def train(self, queue_logs):
        """
        Trains Linear Regression on historical queue_logs data
        Features: queue_length_at_arrival, priority_score, hour_of_day, day_of_week, doctor_avg_consult_mins
        Target: actual_wait_mins
        """
        if len(queue_logs) < 10:
            self.is_trained = False
            self.training_size = len(queue_logs)
            return False

        data = []
        for log in queue_logs:
            if log.actual_wait_mins is not None and log.appointment and log.appointment.doctor:
                arrival_time = log.arrival_time
                if arrival_time:
                    data.append({
                        "queue_length_at_arrival": log.queue_length_at_arrival,
                        "priority_score": log.priority_score,
                        "hour_of_day": arrival_time.hour,
                        "day_of_week": arrival_time.weekday(),
                        "doctor_avg_consult_mins": log.appointment.doctor.avg_consult_mins,
                        "actual_wait_mins": log.actual_wait_mins
                    })
        
        if len(data) < 10:
            self.is_trained = False
            self.training_size = len(data)
            return False
            
        df = pd.DataFrame(data)
        X = df[["queue_length_at_arrival", "priority_score", "hour_of_day", "day_of_week", "doctor_avg_consult_mins"]]
        y = df["actual_wait_mins"]
        
        self.model.fit(X, y)
        self.is_trained = True
        self.training_size = len(data)
        return True

    def predict(self, doctor_avg_consult_mins: float, priority_score: int, appointment_time: datetime, queue_length: int):
        """
        Returns predicted wait in minutes as float
        """
        if not self.is_trained:
            # Fallback formula
            wait = queue_length * doctor_avg_consult_mins * (1 + (5 - priority_score) * 0.1)
            confidence = "low"
            return float(wait), confidence
            
        hour_of_day = appointment_time.hour if appointment_time else datetime.now().hour
        day_of_week = appointment_time.weekday() if appointment_time else datetime.now().weekday()
        
        X_pred = pd.DataFrame([{
            "queue_length_at_arrival": queue_length,
            "priority_score": priority_score,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "doctor_avg_consult_mins": doctor_avg_consult_mins
        }])
        
        try:
            wait = self.model.predict(X_pred)[0]
            if wait < 0:
                wait = 0.0
        except Exception:
            wait = queue_length * doctor_avg_consult_mins * (1 + (5 - priority_score) * 0.1)
            
        if self.training_size >= 50:
            confidence = "high"
        elif self.training_size >= 10:
            confidence = "medium"
        else:
            confidence = "low"
            
        return float(wait), confidence

# Global singleton instance
predictor = WaitTimePredictor()
