import os
import io
import json
from flask import Flask, request, render_template_string, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# === Flask setup ===
app = Flask(__name__)

# === Google Drive Setup ===
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = '1XOzam_fvaBwW6x7ssCzQ6A_B90CRcfdC'  # Share this with your service account
FILE_NAME = 'data.json'

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)


def get_file_id():
    """Get the file ID for data.json in the specified folder"""
    query = f"'{FOLDER_ID}' in parents and name='{FILE_NAME}'"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    if not items:
        raise FileNotFoundError("data.json not found in Google Drive")
    return items[0]['id']


def read_data():
    file_id = get_file_id()
    request_drive = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_drive)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return json.load(fh)


def write_data(new_data):
    file_id = get_file_id()
    file_stream = io.BytesIO(json.dumps(new_data, indent=2).encode('utf-8'))
    media_body = MediaIoBaseUpload(file_stream, mimetype='application/json')
    drive_service.files().update(fileId=file_id, media_body=media_body).execute()

# === HTML UI ===
HTML_FORM = '''<!DOCTYPE html>
<html><head><title>Birthdays 🎉</title>
<style>body { font-family: 'Segoe UI'; background: linear-gradient(135deg, #fbc2eb, #a6c1ee);
display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0;}
.form-card { background-color: #ffffffcc; border-radius: 16px; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2); padding: 30px; width: 300px; text-align: center;}
img { width: 150px; margin-bottom: 20px; border-radius: 12px;}
input[type="number"], input[type="text"] { padding: 10px; margin: 10px 0; border: none; border-radius: 8px; width: 100%; font-size: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);}
input[type="submit"] { background-color: #7f53ac; color: white; padding: 10px 20px; margin-top: 15px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px;}
input[type="submit"]:hover { background-color: #5e3d99;}</style>
</head>
<body>
<div class="form-card">
<img src="/static/party.gif" alt="Party GIF">
<form method="POST" action="/submit">
<input type="number" name="date" placeholder="Date (1-31)" min="1" max="31" required><br>
<input type="number" name="month" placeholder="Month (1-12)" min="1" max="12" required><br>
<input type="text" name="reddit" placeholder="Reddit username" required><br>
<input type="submit" value="Submit 🎉">
</form>
</div></body></html>'''

# === Routes ===
@app.route('/')
def home():
    return render_template_string(HTML_FORM)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = read_data()
        date = request.form.get('date')
        month = request.form.get('month')
        reddit = request.form.get('reddit')
        if not (date and month and reddit):
            return "Missing data", 400
        data.append({'date': date, 'month': month, 'reddit': reddit})
        write_data(data)
        return "<h2>🎉 Saved! <a href='/'>Back</a></h2>"
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/data')
def get_data():
    try:
        data = read_data()
        return jsonify(data)
    except Exception as e:
        return f"Error: {str(e)}", 500

# Required for Vercel
handler = app
