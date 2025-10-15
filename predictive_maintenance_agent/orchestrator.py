# In orchestrator.py
import os
import pandas as pd
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Annotated
import operator
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
if 'GOOGLE_API_KEY' not in os.environ:
    raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it.")

# --- 1. State Definition ---
class WorkflowState(TypedDict):
    vehicle_id: str
    customer_id: str
    anomaly_data: dict
    anomaly_details: str
    diagnosis: str
    drps_score: int
    xai_explanation: str
    customer_response: str
    customer_name: str 
    appointment_slot: str
    booking_status: str
    final_insight: str
    error_message: str

# --- 2. UEBA Security Layer ---
# Define allowed tools for each agent role
ALLOWED_TOOLS = {
    'DataAnalysisAgent': ['read_csv'],
    'DiagnosisAgent': ['read_csv', 'llm_invoke'],
    'CustomerEngagementAgent': ['llm_invoke'],
    'SchedulingAgent': ['get_service_slots', 'book_appointment'], # Note: get_payment_history is NOT here
    'FeedbackAgent': ['read_csv', 'write_csv', 'llm_invoke']
}

def ueba_security_wrapper(agent_name, tool_name, func, *args, **kwargs):
    """A simple UEBA wrapper to check if an agent can use a tool."""
    if tool_name in ALLOWED_TOOLS.get(agent_name, []):
        print(f"✅ [UEBA] ALLOWED: {agent_name} calling {tool_name}")
        return func(*args, **kwargs)
    else:
        print(f"🚨 [UEBA] DENIED: {agent_name} attempted to call unauthorized tool '{tool_name}'!")
        raise PermissionError(f"Unauthorized access attempt by {agent_name} on tool {tool_name}")

# --- 3. Tools Definition ---
# These are the functions our agents can call



def analyze_telemetry_data():
    """Reads telemetry data and finds the first vehicle with an anomaly."""
    telemetry_df = pd.read_csv('data/vehicle_telematics.csv')
    anomaly = telemetry_df[telemetry_df['brake_fluid_pressure_psi'] < 450].iloc[0]
    return anomaly.to_dict()

# In orchestrator.py

def get_diagnosis_and_drps(vehicle_id, anomaly, llm):
    """Diagnoses the issue and calculates DRPS."""
    # Load supporting data
    safety_df = pd.read_csv('data/safety_impact_scores.csv').set_index('component')
    customer_df = pd.read_csv('data/customer_profiles.csv').set_index('vehicle_id')
    
    # --- Diagnosis ---
    # GET A LIST OF VALID COMPONENTS FROM YOUR DATA
    valid_components = safety_df.index.tolist()

    # UPDATE THE PROMPT TO BE MORE RESTRICTIVE
    prompt = f"""
    Vehicle {vehicle_id} has this anomaly: {anomaly['brake_fluid_pressure_psi']:.2f} psi brake pressure and {anomaly['brake_pad_thickness_mm']:.2f}mm brake pad thickness.
    What is the likely component failure?
    Choose ONE of the following valid components: {valid_components}.
    Respond with the component name only.
    """
    predicted_component = llm.invoke(prompt).content.strip().replace("'", "").replace('"', '')

    print(f"LLM Predicted Component: '{predicted_component}'") # Add this for debugging

    # --- DRPS Calculation ---
    failure_risk_prob = 0.92  # Hardcoded for demo
    
    # Add a check to prevent errors if the LLM still misbehaves
    if predicted_component not in safety_df.index:
        print(f"WARNING: LLM returned an invalid component. Defaulting to 'Brakes'.")
        predicted_component = "Brakes"

    safety_score = safety_df.loc[predicted_component, 'safety_impact_score']
    profile = customer_df.loc[vehicle_id]
    customer_factor = 9 if profile['driving_style'] == 'Highway' else 5
    failure_risk_score = failure_risk_prob * 10
    drps = int((safety_score * 5) + (failure_risk_score * 3) + (customer_factor * 2))
    
    return predicted_component, drps

def generate_xai_customer_message(customer_name, drps_score, anomaly_data, diagnosis, llm):
    """Generates a more persuasive, human-like message for the customer."""
    
    # Determine the tone based on urgency
    urgency_level = "It's important we look at this soon to ensure your safety and prevent a breakdown."
    if drps_score < 75:
        urgency_level = "This is a non-urgent recommendation to keep your car in top shape."

    prompt = f"""
    You are a friendly and professional AI assistant for an automotive service center. Your name is 'AutoMate'.
    Your goal is to call a customer, explain a potential vehicle issue clearly and calmly, and convince them to book a free inspection.

    **Customer Name:** {customer_name}
    **Diagnosis:** A potential issue with the vehicle's **{diagnosis}**.
    **Key Evidence:**
    - Brake pressure has dropped to {anomaly_data['brake_fluid_pressure_psi']:.2f} psi (Normal is > 550 psi).
    - Brake pad thickness is low at {anomaly_data['brake_pad_thickness_mm']:.2f}mm.

    Generate a natural, human-like voice script for the call. It should:
    1. Greet the customer by name.
    2. Introduce yourself (AutoMate).
    3. State the reason for the call in a non-alarming way.
    4. Provide the simple, clear evidence (the "why").
    5. State the benefit of acting now (the urgency level).
    6. Make a clear, easy call to action: offer to schedule a complimentary inspection.
    7. End by asking a direct question, like "Would you like me to find a time that works for you?"
    """
    return llm.invoke(prompt).content

def get_service_slots():
    """Calls the mock API to get available appointment slots."""
    response = requests.get("http://127.0.0.1:8000/scheduler/get_slots")
    return response.json()['slots']

def book_appointment(vehicle_id, slot):
    """Calls the mock API to book an appointment."""
    payload = {"vehicle_id": vehicle_id, "slot": slot}
    response = requests.post("http://127.0.0.1:8000/scheduler/book_slot", json=payload)
    return response.json()

def perform_rca_and_update_score(vehicle_id, llm):
    """Performs Root Cause Analysis, tracks recurrence, and updates customer health score."""
    
    # --- Load all necessary data ---
    rca_df = pd.read_csv('data/rca_records.csv')
    maintenance_df = pd.read_csv('data/maintenance_logs.csv')
    customers_df = pd.read_csv('data/customer_profiles.csv')

    # --- NEW LOGIC for tracking recurring defects ---
    # Count how many times this specific failure code has previously occurred across the fleet
    recurrence_count = maintenance_df[maintenance_df['dtc_code_at_service'] == 'C0204'].shape[0]

    # --- ENHANCED INSIGHT based on recurrence ---
    # The "+ 1" includes the current failure we are processing
    insight = f"Failure linked to {rca_df['rca_id'].iloc[0]}. This is the **{recurrence_count + 1}th instance** of this defect recorded across the fleet. Recommend escalating for quality review."
    
    # --- Update customer health score ---
    current_score = customers_df.loc[customers_df['vehicle_id'] == vehicle_id, 'health_score'].iloc[0]
    new_score = current_score + 50
    customers_df.loc[customers_df['vehicle_id'] == vehicle_id, 'health_score'] = new_score
    customers_df.to_csv('data/customer_profiles.csv', index=False)
    
    return insight, new_score

# --- 4. Agent Nodes ---
llm = ChatGoogleGenerativeAI(model="gemini-pro-latest")

# In orchestrator.py, inside data_analysis_node
def data_analysis_node(state: WorkflowState):
    print("--- 🕵️‍♂️ DATA ANALYSIS AGENT ---")
    anomaly_dict = ueba_security_wrapper('DataAnalysisAgent', 'read_csv', analyze_telemetry_data)
    
    # --- FIX THE ORDER HERE ---
    # 1. First, load the customer data from the CSV file.
    customer_df = pd.read_csv('data/customer_profiles.csv')

    # 2. Now that customer_df exists, you can safely use it.
    state['vehicle_id'] = anomaly_dict['vehicle_id']
    state['customer_id'] = customer_df[customer_df['vehicle_id'] == state['vehicle_id']]['customer_id'].iloc[0]
    state['customer_name'] = customer_df[customer_df['vehicle_id'] == state['vehicle_id']]['customer_name'].iloc[0]
    
    # Store the other details
    state['anomaly_data'] = anomaly_dict
    state['anomaly_details'] = f"Low pressure ({anomaly_dict['brake_fluid_pressure_psi']:.2f} psi) & thickness ({anomaly_dict['brake_pad_thickness_mm']:.2f}mm)"
    
    print(f"Anomaly detected for {state['vehicle_id']}: {state['anomaly_details']}")
    return state



# In orchestrator.py, inside diagnosis_node
def diagnosis_node(state: WorkflowState):
    print("--- 🩺 DIAGNOSIS AGENT ---")
    # Pass the dictionary, NOT the string
    diagnosis, drps = ueba_security_wrapper('DiagnosisAgent', 'llm_invoke', get_diagnosis_and_drps, state['vehicle_id'], state['anomaly_data'], llm)
    state['diagnosis'] = diagnosis
    state['drps_score'] = drps
    print(f"Diagnosis: {diagnosis} | DRPS Score: {drps}")
    return state

def customer_engagement_node(state: WorkflowState):
    print("--- 💬 CUSTOMER ENGAGEMENT AGENT ---")
    
    # --- THIS IS THE LINE TO FIX ---
    # We need to pass the raw data dictionary 'anomaly_data' for the XAI explanation.
    xai_message = ueba_security_wrapper(
        'CustomerEngagementAgent', 
        'llm_invoke', 
        generate_xai_customer_message, 
        state['customer_name'], # Pass the name
        state['drps_score'],    # Pass the score for urgency
        state['anomaly_data'],
        state['diagnosis'],  
        llm
    )

    state['xai_explanation'] = xai_message
    print(f"Generated XAI message for customer:\n{xai_message}")
    # For the demo, we assume the customer agrees
    state['customer_response'] = 'yes'
    return state

def scheduling_node(state: WorkflowState):
    print("--- 🗓️ SCHEDULING AGENT ---")
    try:
        # --- DEMO THE UEBA BLOCK ---
        print("Attempting an UNAUTHORIZED API call for demo purposes...")
        ueba_security_wrapper('SchedulingAgent', 'get_payment_history', lambda: "this should fail")
    except PermissionError as e:
        print(f"Caught expected exception: {e}")
        state['error_message'] = str(e)

    # --- Proceed with authorized calls ---
    slots = ueba_security_wrapper('SchedulingAgent', 'get_service_slots', get_service_slots)
    chosen_slot = slots[1] # Agent picks the second available slot
    state['appointment_slot'] = chosen_slot
    print(f"Available slots: {slots}. Agent chose: {chosen_slot}")
    
    booking = ueba_security_wrapper('SchedulingAgent', 'book_appointment', book_appointment, state['vehicle_id'], chosen_slot)
    state['booking_status'] = booking['status']
    print(f"Booking status: {state['booking_status']}")
    return state

def handle_declined_node(state: WorkflowState):
    print("--- 😔 CUSTOMER DECLINED ---")
    print("Action: Logging interaction. Will schedule a follow-up reminder in 3 days.")
    # In a real system, you'd add this to a separate reminder queue.
    state['booking_status'] = 'Declined - Follow-up Scheduled'
    return state

# 2. Add a conditional function to decide the next step
def should_schedule(state: WorkflowState):
    """Determines whether to schedule an appointment or handle a decline."""
    print("--- 🤔 DECISION POINT ---")
    # Simulate customer response based on urgency for the demo
    # A high DRPS means the customer is more likely to agree
    if state['drps_score'] > 80:
        print("Customer agreed to schedule.")
        state['customer_response'] = 'yes'
        return "continue_to_scheduling"
    else:
        print("Customer declined scheduling for now.")
        state['customer_response'] = 'no'
        return "handle_decline"

def feedback_and_insight_node(state: WorkflowState):
    print("--- 📈 FEEDBACK & INSIGHT AGENT ---")
    insight, new_score = ueba_security_wrapper('FeedbackAgent', 'read_csv', perform_rca_and_update_score, state['vehicle_id'], llm)
    state['final_insight'] = insight
    print(f"Generated Manufacturing Insight: {insight}")
    print(f"Updated Vehicle Health Score for {state['vehicle_id']} to {new_score}")
    return state

# --- 5. Graph Definition ---
workflow = StateGraph(WorkflowState)

workflow.add_node("data_analysis", data_analysis_node)
workflow.add_node("diagnosis", diagnosis_node)
workflow.add_node("customer_engagement", customer_engagement_node)
workflow.add_node("scheduling", scheduling_node)
workflow.add_node("handle_decline", handle_declined_node)
workflow.add_node("feedback_and_insight", feedback_and_insight_node)

# --- 6. Graph Edges ---
workflow.set_entry_point("data_analysis")
workflow.add_edge("data_analysis", "diagnosis")
workflow.add_edge("diagnosis", "customer_engagement")
workflow.add_conditional_edges(
    "customer_engagement",
    should_schedule,
    {
        "continue_to_scheduling": "scheduling",
        "handle_decline": "handle_decline"
    }
)
workflow.add_edge("scheduling", "feedback_and_insight")
workflow.add_edge("feedback_and_insight", END)
workflow.add_edge("handle_decline", END)

# --- 7. Compile and Run ---
app = workflow.compile()
print("\n🚀🚀🚀 --- STARTING AGENTIC WORKFLOW --- 🚀🚀🚀\n")
inputs = {}
final_state = app.invoke(inputs)

print("\n✅✅✅ --- WORKFLOW COMPLETED --- ✅✅✅\n")
print("Final State:")
print(final_state)