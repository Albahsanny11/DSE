import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
import base64
from googleapiclient.discovery import build
import os
from datetime import datetime

# -------------------------
# CONFIGURATION
# -------------------------
SHEET_NAME = "DSE Trends"
GMAIL_TO = "albahsanny@gmail.com"
DATE = datetime.today().strftime("%Y-%m-%d")

# -------------------------
# AUTHENTICATION
# -------------------------
creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(creds)
sheet = gc.open(SHEET_NAME).sheet1
gmail = build("gmail", "v1", credentials=creds)

# -------------------------
# GET DSE DATA
# -------------------------
url = "https://www.dse.co.tz/"
res = requests.get(url)
tables = pd.read_html(res.text)
data = tables[0]  # assumes first table is the market summary

# Clean up
data = data.dropna(subset=["Security", "Closing Price"])
data["Change (%)"] = data["Closing Price"].pct_change().fillna(0).apply(lambda x: round(x * 100, 2))
data["Trend"] = data["Change (%)"].apply(lambda x: "UP 📈" if x > 0 else "DOWN 📉" if x < 0 else "FLAT")

# -------------------------
# APPEND TO GOOGLE SHEET
# -------------------------
for _, row in data.iterrows():
    sheet.append_row([DATE, row["Security"], row["Closing Price"], row["Change (%)"], row["Trend"]])

# -------------------------
# SEND EMAIL SUMMARY
# -------------------------
summary = "\n".join([f"{row['Security']}: {row['Closing Price']} TZS ({row['Trend']})"
                     for _, row in data.iterrows()])

message = MIMEText(f"DSE Trends for {DATE}:\n\n{summary}")
message["to"] = GMAIL_TO
message["subject"] = f"DSE Market Summary - {DATE}"

create_message = {
    "raw": base64.urlsafe_b64encode(message.as_bytes()).decode()
}

gmail.users().messages().send(userId="me", body=create_message).execute()

print(f"DSE automation complete for {DATE}. Summary sent to {GMAIL_TO}.")

