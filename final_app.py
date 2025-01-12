import streamlit as st
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

def get_gsheet_credentials():
    """Create credentials object from Streamlit secrets"""
    credentials = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
        "universe_domain": st.secrets["gcp_service_account"]["universe_domain"]
    }
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_info(credentials, scopes=scopes)
    return creds

# Initialize Google Sheets client
creds = get_gsheet_credentials()
client = gspread.authorize(creds)
sheet = client.open("Priorities_Tracker_Database_Spreadsheet").sheet1

# Streamlit app
st.title("Activity Logger")

# Input fields
priority = st.selectbox("Priority", ["Career", "Music", "Fitness", "Relationship", "Philosophy", "Finance"])
activity = st.text_input("Activity Description")
duration = st.number_input("Duration (in hours)", min_value=0.0, step=0.25)
remarks = st.text_area("Remarks (Optional)")

# Submit button
if st.button("Log Activity"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, priority, activity, duration, remarks])
    st.success("Activity logged successfully!")
