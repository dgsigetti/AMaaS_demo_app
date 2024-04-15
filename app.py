from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
import os
import json
from pymongo import MongoClient
import argparse
import amaas.grpc
import sys
import secrets

UPLOAD_FOLDER = '/app/uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = secrets.token_hex(32)

# MongoDB connection setup
MONGO_HOST = "YOUR MONGO HOST"
MONGO_PORT = 27017
MONGO_USER = "YOUR DB USER"
MONGO_PASSWORD = "YOUR DB PW"
DATABASE_NAME = "YOUR DB NAME"
AUTH_DB = "admin"

# Construct MongoDB connection URI with authentication
uri = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{DATABASE_NAME}?authSource={AUTH_DB}"

client = MongoClient(uri)
db = client[DATABASE_NAME]
collection = db['scan_results']

# Define the allowed_file function to allow all file types
def allowed_file(filename):
    return True  # Allow all file types

# Function to scan uploaded file
def scan_uploaded_file(file_path, handle):
    try:
        result = amaas.grpc.scan_file(file_path, handle)
        return result
    except Exception as e:
        print("Error during scanning:", e)
        return None

@app.route('/', methods=['GET'])
def root():
    # Redirect to the login page when accessing the root URL
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

            # Save the uploaded file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Initialize args with default values
            args = argparse.Namespace(
                addr=os.environ.get('C1_ADDRESS'),
                api_key=os.environ.get('C1_API_KEY'),
                region=os.environ.get('C1_REGION')
            )

            # Initiate the AMaaS connection
            handle = amaas.grpc.init(args.addr, args.api_key, args.region)

            scan_result = scan_uploaded_file(file_path, handle)

            if scan_result is not None:
                scan_result_dict = json.loads(scan_result)
                scan_result_code = scan_result_dict.get('scanResult', -1)

                if scan_result_code == 1:
                    amaas.grpc.quit(handle)
                    return render_template('scan_results.html', scan_result_code=1, scan_results=scan_result_dict)
                print("Scan result:", scan_result)
                sys.stdout.flush()  # Flush the stdout buffer
            amaas.grpc.quit(handle)

            # Write scan result to MongoDB
            result_entry = {
                'filename': filename,
                'scan_result': scan_result
            }

            if scan_result is not None:
                scan_result_dict = json.loads(scan_result)
                scan_result_code = scan_result_dict.get('scanResult', -1)
                result_entry['scan_result_code'] = scan_result_code
            else:
                # If scan result is None, indicate "Clean File"
                result_entry['scan_result_code'] = "Clean File"

            collection.insert_one(result_entry)

            return render_template('scan_results.html', scan_message="File uploaded successfully.", scan_result_code=0)

    return render_template('upload.html')
