# In generate_data.py
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# --- 1. Vehicle Telematics Data ---
print("Generating: vehicle_telematics.csv")
data = []
vehicles = 10
for i in range(1, vehicles + 1):
    vehicle_id = f'veh_{i:03d}'
    base_time = datetime.now()
    # Generate 100 data points (minutes) for each vehicle
    for j in range(100):
        ts = base_time - timedelta(minutes=j)
        pressure = 550
        thickness = 12.0

        # Simulate a clear, progressive anomaly for vehicle 7 (Brake issue)
        if i == 7 and j < 30:
            pressure = 450 - (30 - j) * 5  # Pressure drops sharply over 30 mins
            thickness = 8.0 - (30 - j) * 0.2 # Brake pads wear down

        data.append({
            'vehicle_id': vehicle_id,
            'timestamp': ts,
            'odometer_km': 45000 + i*1000 + j*2,
            'brake_fluid_pressure_psi': round(pressure + random.uniform(-2, 2), 2),
            'brake_pad_thickness_mm': round(thickness - random.uniform(0, 0.1), 2),
            'dtc_code': 'C0204' if pressure < 400 else None
        })
pd.DataFrame(data).to_csv('data/vehicle_telematics.csv', index=False)

# --- 2. Maintenance Logs ---
print("Generating: maintenance_logs.csv")
logs = [
    {'record_id': 1, 'vehicle_id': 'veh_003', 'service_date': '2025-05-10', 'description': 'Annual Service', 'dtc_code_at_service': None},
    {'record_id': 2, 'vehicle_id': 'veh_007', 'service_date': '2025-01-20', 'description': 'Tire rotation', 'dtc_code_at_service': None},
    {'record_id': 3, 'vehicle_id': 'veh_009', 'service_date': '2025-07-30', 'description': 'Replaced brake master cylinder', 'dtc_code_at_service': 'C0204'},
]
pd.DataFrame(logs).to_csv('data/maintenance_logs.csv', index=False)

# --- 3. RCA Records ---
print("Generating: rca_records.csv")
rca = [
    {'rca_id': 'RCA-112', 'part_number': 'BCM-45-A2', 'part_name': 'Brake Master Cylinder', 'failure_mode': 'Internal Seal Degradation', 'root_cause': 'Material impurity from supplier batch #XYZ', 'corrective_action_plan': 'Recall batch #XYZ'}
]
pd.DataFrame(rca).to_csv('data/rca_records.csv', index=False)

# --- 4. Customer Profiles (with Health Score) ---
print("Generating: customer_profiles.csv")
profiles = []
styles = ['City', 'Highway', 'Mixed']
names = ["Priya", "Rohan", "Anjali", "Vikram", "Sonia", "Amit", "Neha", "Karan", "Meera", "Arjun"]
for i in range(1, vehicles + 1):
    profiles.append({
        'vehicle_id': f'veh_{i:03d}',
        'customer_id': f'cust_{100+i}',
        'customer_name': names[i-1], # <-- ADD THIS LINE
        'driving_style': random.choice(styles),
        'avg_daily_km': random.randint(30, 150),
        'health_score': random.randint(750, 950)
    })
pd.DataFrame(profiles).to_csv('data/customer_profiles.csv', index=False)

# --- 5. Safety Impact Scores ---
print("Generating: safety_impact_scores.csv")
safety_scores = [
    {'component': 'Brakes', 'safety_impact_score': 10},
    {'component': 'Engine', 'safety_impact_score': 9},
    {'component': 'Transmission', 'safety_impact_score': 8},
    {'component': 'Steering', 'safety_impact_score': 9},
    {'component': 'Suspension', 'safety_impact_score': 7},
    {'component': 'Tires', 'safety_impact_score': 8},
    {'component': 'AC System', 'safety_impact_score': 3},
    {'component': 'Infotainment', 'safety_impact_score': 1}
]
pd.DataFrame(safety_scores).to_csv('data/safety_impact_scores.csv', index=False)

print("\n✅ All data files generated successfully in the /data folder!")