import streamlit as st
from datetime import datetime
import gspread
import json
import os
from google.oauth2.service_account import Credentials


# If creds from File
creds = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"])


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
