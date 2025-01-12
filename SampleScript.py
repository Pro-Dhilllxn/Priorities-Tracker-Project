import gspread
from google.oauth2.service_account import Credentials

# Define the scope for the API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Authenticate using the service account
credentials = Credentials.from_service_account_file(
    'credentials.json', scopes=SCOPES
)

# Connect to Google Sheets
client = gspread.authorize(credentials)

# Open the Google Sheet by name
sheet_name = "Priorities_Tracker_Database_Spreadsheet" 
spreadsheet = client.open(sheet_name)

# Select the first worksheet (or create one if needed)
worksheet = spreadsheet.sheet1

# Example: Log activity
activity = {
    "Date": "2025-01-08",
    "Time": "10:30 AM",
    "Activity": "Started learning Google Sheets API"
}

# Append the activity as a row
worksheet.append_row(list(activity.values()))

print("Activity logged successfully!")
