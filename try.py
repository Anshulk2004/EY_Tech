import google.generativeai as genai
import os

# --- PASTE YOUR KEY HERE ---
# Use the same key you created from Google AI Studio.
# It should start with "AIzaSy..."
GOOGLE_API_KEY="AIzaSyBcPMZbqAYkAMo5Ytdo8R2B9yi1BcslW04"

# Configure the library with your API key
try:
    genai.configure(api_key=GOOGLE_API_KEY)

    print("✅ Successfully configured. Checking for available models...")
    print("---------------------------------------------------------")

    model_found = False
    for m in genai.list_models():
      # Check if the model supports the 'generateContent' method
      if 'generateContent' in m.supported_generation_methods:
        print(m.name)
        model_found = True
    
    if not model_found:
        print("No models that support 'generateContent' were found.")
        print("Please ensure the Vertex AI API is enabled and your project is linked to a billing account.")

except Exception as e:
    print(f"An error occurred during configuration: {e}")
    print("Please double-check that your API key is correct.")