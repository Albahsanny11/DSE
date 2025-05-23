import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import re
import smtplib
from email.mime.text import MIMEText
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
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(creds)

try:
    sheet = gc.open(SHEET_NAME).sheet1
except gspread.SpreadsheetNotFound:
    print(f"📄 Sheet '{SHEET_NAME}' not found. Creating a new one...")
    sh = gc.create(SHEET_NAME)
    sh.share(GMAIL_TO, perm_type='user', role='writer')
    sheet = sh.sheet1
    print(f"✅ Created and shared '{SHEET_NAME}' with {GMAIL_TO}")

# -------------------------
# GET DSE DATA
# -------------------------
url = "https://www.dse.co.tz/"
res = requests.get(url, verify=False)

tables = pd.read_html(res.text)
print(f"Found {len(tables)} tables on DSE site")

# Use the detailed market summary table (likely Table 3)
for idx, table in enumerate(tables):
    print(f"Table {idx} Columns: {list(table.columns)}")

data = tables[3]  # Based on structure from earlier logs
data = data[["Symbol", "Close", "Change"]]  # Columns we need
data.rename(columns={"Symbol": "Security", "Close": "Closing Price"}, inplace=True)

# Clean up and add trend info
data = data.dropna(subset=["Security", "Closing Price"])

def clean_percent(val):
    try:
        val = re.sub(r"[^\d.\-]+", "", str(val))
        return float(val) if val else 0.0
    except:
        return 0.0

data["Change (%)"] = data["Change"].apply(clean_percent)
data["Trend"] = data["Change (%)"].apply(lambda x: "UP 📈" if x > 0 else "DOWN 📉" if x < 0 else "FLAT")

# -------------------------
# APPEND TO GOOGLE SHEET
# -------------------------
for _, row in data.iterrows():
    sheet.append_row([DATE, row["Security"], row["Closing Price"], row["Change (%)"], row["Trend"]])

# -------------------------
# SEND EMAIL SUMMARY via SMTP
# -------------------------
summary = "\n".join([f"{row['Security']}: {row['Closing Price']} TZS ({row['Trend']})"
                     for _, row in data.iterrows()])

body = f"DSE Trends for {DATE}:\n\n{summary}"
msg = MIMEText(body)
msg["Subject"] = f"DSE Market Summary - {DATE}"
msg["From"] = GMAIL_TO
msg["To"] = GMAIL_TO

# Load Gmail App Password from environment (GitHub Secret)
app_password = os.environ.get("GMAIL_APP_PASSWORD")

# Debug: Confirm password is loading
if not app_password:
    raise Exception("❌ GMAIL_APP_PASSWORD is missing or failed to load from GitHub Secrets.")
else:
    print("✅ GMAIL_APP_PASSWORD loaded successfully.")

# Send email via Gmail SMTP
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(GMAIL_TO, app_password)
    smtp.send_message(msg)

print(f"✅ Email sent to {GMAIL_TO}")
