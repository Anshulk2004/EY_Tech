# In dashboard.py
import streamlit as st
import pandas as pd
import time

st.set_page_config(layout="wide")

st.title(" Agentic AI Fleet Monitoring Dashboard")

# --- Load Data ---
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

telemetry_df = load_data('data/vehicle_telematics.csv')
customers_df = load_data('data/customer_profiles.csv')

# --- Layout ---
col1, col2 = st.columns([2, 1])

# --- Column 1: Fleet Status and Insights ---
with col1:
    st.header("Real-Time Fleet Status")
    
    # Find the latest reading for each vehicle
    latest_readings = telemetry_df.loc[telemetry_df.groupby('vehicle_id')['timestamp'].idxmax()]
    
    # Set a threshold for alerts
    latest_readings['status'] = latest_readings['brake_fluid_pressure_psi'].apply(
        lambda x: "🔴 ALERT" if x < 450 else "🟢 Healthy"
    )
    
    st.dataframe(latest_readings[['vehicle_id', 'status', 'brake_fluid_pressure_psi', 'brake_pad_thickness_mm', 'timestamp']], height=380)

    st.header("Manufacturing Quality Insight")
    st.info("""
    **Insight Generated:** A correlation has been found between `DTC: C0204` (Brake Master Cylinder Failure) and `RCA-112`.
    - **Affected Part:** `BCM-45-A2` (Brake Master Cylinder)
    - **Root Cause:** Material impurity from supplier batch #XYZ.
    - **Recommendation:** Flag all vehicles with this part for proactive inspection. Initiate quality review with the supplier.
    """)

# --- Column 2: DRPS, UEBA, and Gamification ---
with col2:
    st.header("Dynamic Repair Priority")
    st.subheader("DRPS for VEH-007: 91/100")
    
    st.progress(91, text="🔴 CRITICAL PRIORITY")
    with st.expander("See DRPS Breakdown"):
        st.metric("Safety Impact (Brakes)", "10 / 10")
        st.metric("Failure Risk (92% Prob)", "9.2 / 10")
        st.metric("Customer Factor (Highway)", "9.0 / 10")
        
    st.header("🔒 Security Alerts (UEBA)")
    st.error("""
    **CRITICAL ALERT (12:43 PM):**
    - **Action:** Unauthorized API call **BLOCKED**.
    - **Agent:** `SchedulingAgent`
    - **Attempted Call:** `getCustomerPaymentHistory()`
    - **Reason:** Accessing customer financial data is outside the agent's defined role and permissions.
    """)

    st.header("🏆 Customer Health Score")
    customer_veh_007 = customers_df[customers_df['vehicle_id'] == 'veh_007'].iloc[0]
    st.metric(
        label=f"Score for {customer_veh_007['customer_id']}",
        value=int(customer_veh_007['health_score']),
        delta="+50 Points (Pending Service Completion)",
        delta_color="off"
    )
    st.write("Completing the recommended proactive service will boost the score and unlock rewards.")