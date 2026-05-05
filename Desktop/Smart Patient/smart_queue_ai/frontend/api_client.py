import requests
import streamlit as st

class APIClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url
        self.token = token

    def _headers(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def register(self, name, email, phone, password, role):
        url = f"{self.base_url}/auth/register"
        data = {"name": name, "email": email, "phone": phone, "password": password, "role": role}
        res = requests.post(url, json=data)
        if res.status_code == 200:
            return res.json()
        st.error(f"Error: {res.text}")
        return None

    def login(self, email, password):
        url = f"{self.base_url}/auth/login"
        data = {"email": email, "password": password}
        res = requests.post(url, json=data)
        if res.status_code == 200:
            return res.json()
        st.error("Login failed. Check credentials.")
        return None

    def get_doctors(self, specialization=None, clinic_id=None, day_of_week=None):
        url = f"{self.base_url}/patient/doctors"
        params = {}
        if specialization:
            params["specialization"] = specialization
        if clinic_id:
            params["clinic_id"] = clinic_id
        if day_of_week:
            params["day_of_week"] = day_of_week
        res = requests.get(url, headers=self._headers(), params=params)
        return res.json() if res.status_code == 200 else []

    def get_slots(self, doctor_id, date):
        url = f"{self.base_url}/patient/doctors/{doctor_id}/slots"
        res = requests.get(url, headers=self._headers(), params={"date": date})
        return res.json() if res.status_code == 200 else []

    def book_appointment(self, doctor_id, clinic_id, date, time, symptoms, slot_id=None):
        url = f"{self.base_url}/patient/appointments"
        data = {
            "doctor_id": doctor_id,
            "clinic_id": clinic_id,
            "appointment_date": date,
            "appointment_time": time,
            "symptoms_at_booking": symptoms,
            "slot_id": slot_id
        }
        res = requests.post(url, headers=self._headers(), json=data)
        if res.status_code == 200:
            return res.json()
        st.error(f"Booking Error: {res.text}")
        return None

    def get_appointments(self, role):
        if role == "patient":
            url = f"{self.base_url}/patient/appointments"
        elif role == "doctor":
            url = f"{self.base_url}/doctor/appointments"
        elif role == "receptionist":
            url = f"{self.base_url}/receptionist/appointments"
        elif role == "admin":
            url = f"{self.base_url}/admin/appointments"
        else:
            return []
            
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else []

    def get_queue(self, doctor_id):
        url = f"{self.base_url}/queue/{doctor_id}"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else {"current_token": None, "waiting": []}

    def checkin(self, appointment_id):
        url = f"{self.base_url}/receptionist/checkin/{appointment_id}"
        res = requests.post(url, headers=self._headers())
        if res.status_code == 200:
            return res.json()
        st.error(f"Error: {res.text}")
        return None

    def call_next(self, appointment_id):
        url = f"{self.base_url}/doctor/queue/{appointment_id}/next"
        res = requests.put(url, headers=self._headers())
        if res.status_code == 200:
            return res.json()
        st.error(f"Error: {res.text}")
        return None

    def get_admin_stats(self):
        url = f"{self.base_url}/admin/stats"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else {}

    def get_notifications(self):
        url = f"{self.base_url}/patient/notifications"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else []

    def update_patient_profile(self, symptoms):
        url = f"{self.base_url}/patient/profile"
        res = requests.put(url, headers=self._headers(), json={"symptoms": symptoms})
        if res.status_code == 200:
            return res.json()
        st.error(f"Error: {res.text}")
        return None
        
    def get_patient_profile(self):
        url = f"{self.base_url}/patient/profile"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else {}

    def get_clinics(self):
        url = f"{self.base_url}/clinics/"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else []

    def search_doctor_availability(self, specialization=None, doctor_name=None):
        url = f"{self.base_url}/doctor/search_availability"
        params = {}
        if specialization:
            params["speciality"] = specialization
        if doctor_name:
            params["doctor_name"] = doctor_name
        res = requests.get(url, headers=self._headers(), params=params)
        return res.json() if res.status_code == 200 else []

    def get_doctor_utilization(self, clinic_id):
        url = f"{self.base_url}/doctor/utilization"
        params = {"clinic_id": clinic_id}
        res = requests.get(url, headers=self._headers(), params=params)
        return res.json() if res.status_code == 200 else {}
        
    def add_doctor_leave(self, start_date, end_date, reason):
        url = f"{self.base_url}/doctor/leaves"
        data = {"start_date": start_date, "end_date": end_date, "reason": reason}
        res = requests.post(url, headers=self._headers(), json=data)
        if res.status_code == 200:
            return res.json()
        st.error(f"Error: {res.text}")
        return None

    def add_doctor_to_clinic(self, name, email, password, specialization, exp, clinic_id, days):
        url = f"{self.base_url}/admin/add_doctor_to_clinic"
        data = {
            "name": name, "email": email, "password": password,
            "specialization": specialization, "experience_years": exp,
            "clinic_id": clinic_id, "days_of_week": days
        }
        res = requests.post(url, headers=self._headers(), json=data)
        if res.status_code == 200:
            return res.json()
        st.error(f"Error: {res.text}")
        return None

    def get_admin_doctors(self):
        url = f"{self.base_url}/admin/doctors"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else []
        
    def add_clinic(self, name, address):
        url = f"{self.base_url}/clinics/"
        data = {"name": name, "address": address}
        res = requests.post(url, headers=self._headers(), json=data)
        if res.status_code == 200:
            return res.json()
        st.error(f"Error: {res.text}")
        return None

    def delete_clinic(self, clinic_id):
        url = f"{self.base_url}/clinics/{clinic_id}"
        res = requests.delete(url, headers=self._headers())
        if res.status_code == 200:
            return True
        st.error(f"Error: {res.text}")
        return False
