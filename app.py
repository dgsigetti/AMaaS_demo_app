from flask import Flask, session, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
import os
import json
from pymongo import MongoClient
import secrets

UPLOAD_FOLDER = '/app/uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = secrets.token_hex(32)

# MongoDB connection setup
MONGO_HOST = "ec2-3-145-115-146.us-east-2.compute.amazonaws.com"
MONGO_PORT = 27017
MONGO_USER = "backupUser"
MONGO_PASSWORD = "Capecod12!"
DATABASE_NAME = "v1fs_db"
AUTH_DB = "admin"

# Construct MongoDB connection URI with authentication
uri = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{DATABASE_NAME}?authSource={AUTH_DB}"

client = MongoClient(uri)
db = client[DATABASE_NAME]
collection = db['scan_results']

#define the allowed_file function to allow all file types
def allowed_file(filename):
    return True  # Allow all file types

#function to scan uploaded file
def scan_uploaded_file(file_path, handle):
    # Your scan logic here
    return "Scan result"  # Replace this with your actual scan result

@app.route('/', methods=['GET'])
def root():
    #redirect to the login page when accessing the root URL
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('upload_file'))
    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            #save the uploaded file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            scan_result = scan_uploaded_file(file_path, handle)

            # Write scan result to MongoDB
            result_entry = {
                'filename': filename,
                'scan_result': scan_result
            }
            collection.insert_one(result_entry)

            return render_template('scan_results.html', scan_message="File uploaded successfully.", scan_result_code=0)

    return render_template('upload.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
