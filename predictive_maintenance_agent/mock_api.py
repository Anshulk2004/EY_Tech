# In mock_api.py
from fastapi import FastAPI, Body
from datetime import date, timedelta

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Mock Automotive API is running."}

@app.get("/scheduler/get_slots")
def get_available_slots(service_date: date = None):
    """Returns available slots for a given date."""
    print(f"API LOG: Request received for available slots on {service_date}.")
    # In a real system, you'd check a database. Here, we return fixed slots.
    return {"slots": ["09:00 AM", "11:00 AM", "02:00 PM", "04:00 PM"]}

@app.post("/scheduler/book_slot")
def book_appointment(data: dict = Body(...)):
    """Books a service appointment."""
    vehicle_id = data.get('vehicle_id')
    slot = data.get('slot')
    print(f"API LOG: Booking confirmed for {vehicle_id} at {slot}.")
    return {"status": "confirmed", "booking_id": f"BK{abs(hash(vehicle_id)) % 10000}"}

# A FAKE, UNAUTHORIZED ENDPOINT FOR THE UEBA DEMO
@app.get("/customer/get_payment_history/{customer_id}")
def get_payment_data(customer_id: str):
    """
    **THIS IS AN UNAUTHORIZED ENDPOINT.**
    Agents should not be able to access this.
    """
    print(f"API LOG: UNAUTHORIZED ATTEMPT to access payment history for {customer_id}.")
    return {"error": "Unauthorized Access. This incident has been logged."}