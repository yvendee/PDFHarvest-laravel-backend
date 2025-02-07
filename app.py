from flask import Flask, request, Blueprint, render_template, jsonify, session, redirect, url_for, send_file
from flask_cors import CORS
from functools import wraps

import os
import shutil
import requests
import threading
import time 

import shutil
import zipfile
import uuid

# app = Flask(__name__)
app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)  # This will enable CORS for all routes
app.secret_key = 'your_secret_key'  # Needed for session management
last_upload_time = None

# Hardcoded username and password (for demo purposes)
USERNAME = "searchmaid"
PASSWORD = "maidasia"
current_ocr = "gpt4ominiOCR" # Global variable to store current OCR setting

# Global variable to store structured text setting
# current_structured_text = "gpt4omini"
current_structured_text = "gpt4omini"
maid_status_global = "None"


FRONTEND_API_URL = os.environ.get('FRONTEND_API_URL', 'http://localhost:8000')  # Default to localhost:8000 if not set
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://localhost:5000')  # Default to localhost:8000 if not set

app.config['UPLOAD_FOLDER'] = 'uploads/'  # Make sure this folder exists
app.config['OUTPUT_FOLDER'] = 'output_files/'  # Make sure this folder exists
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16 MB
query_storage = []

# query_storage = [
#     {
#         "query_label": "Query 1",
#         "query_id": "12345",
#         "status": "download",  # Status can be 'download', 'inprogress', 'waiting', or 'failed'
#         "up_time": "2 hours",
#         "num_files": "5 files",
#         "rate": "50 KB/s"
#     },
#     {
#         "query_label": "Query 2",
#         "query_id": "67890",
#         "status": "inprogress",
#         "up_time": "1 hour",
#         "num_files": "3 files",
#         "rate": "30 KB/s"
#     },
#     {
#         "query_label": "Query 3",
#         "query_id": "11223",
#         "status": "waiting",
#         "up_time": "10 minutes",
#         "num_files": "10 files",
#         "rate": "70 KB/s"
#     },
#     {
#         "query_label": "Query 4",
#         "query_id": "33445",
#         "status": "failed",
#         "up_time": "5 minutes",
#         "num_files": "2 files",
#         "rate": "20 KB/s"
#     }
# ]


# Define a decorator function to check if the user is authenticated
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Function to check if user is authenticated
def check_authenticated():
    if 'username' in session:
        return session['username'] == USERNAME
    return False

# Function to call the Laravel API every 1 second
def increment_cache(session_id):
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    while True:  # This will keep executing indefinitely until stopped
        print(f"[INFO] Increment cache task started for session: {session_id}")

        increment_url = f'{FRONTEND_API_URL}/incrementcache/{session_id}'
        try:
            # Make the request to Laravel API
            print(f"[INFO] Making request to Laravel API: {increment_url}")
            response = requests.get(increment_url)

            if response.status_code != 200:
                print(f"[ERROR] Failed to increment cache for {session_id}: {response.text}")
                if "Cannot increment" in response.text:
                    print(f"[INFO] Progress for session {session_id} has reached the limit.")
                    break  # Stop the task since current == total
                continue  # Skip the next loop until retry

            # If request is successful, parse the response JSON
            response_json = response.json()
            current = response_json.get('progress', {}).get('current', 0)
            total = response_json.get('progress', {}).get('total', 0)

            # Ensure current and total are integers for comparison
            current = int(current)  # Convert current to an integer
            total = int(total)      # Convert total to an integer

            print(f"[INFO] Processing: file {current} of {total}")

            # Stop if current >= total
            if current >= total:
                print(f"[INFO] Stopping background task for session {session_id} because progress is complete.")
                
                # Zip the files inside the session folder
                zip_file_path = os.path.join(output_folder, f"{session_id}.zip")
                zip_files(session_folder, zip_file_path)

                # Move the zip file to the output folder
                print(f"[INFO] Files zipped and saved as {zip_file_path}")

                break  # Stop the task if current >= total

        except Exception as e:
            print(f"[ERROR] Error while incrementing cache for {session_id}: {str(e)}")

        # Wait 1 second before the next request
        time.sleep(1)

    print(f"[INFO] Increment cache task completed for session: {session_id}")

def zip_files(session_folder, zip_file_path):
    """Zip all files in the session folder and save to zip_file_path."""
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(session_folder):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, session_folder))
        print(f"[INFO] Zipped {len(files)} file(s) into {zip_file_path}")

@app.route('/api/upload/<session_id>', methods=['POST'])
def upload_file(session_id):
    print(f"Session ID: {session_id}")  # Log the session ID

    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)  # Create session-specific folder

    if 'files[]' not in request.files:
        print("No file part")
        return jsonify({'error': 'No file part', 'session_id': session_id}), 400

    files = request.files.getlist('files[]')
    if not files or all(file.filename == '' for file in files):
        print("No selected files")
        return jsonify({'error': 'No selected files', 'session_id': session_id}), 400

    uploaded_files = []
    total_files = len(files)  # Total files to be uploaded

    # For each file uploaded, save it and then notify Laravel app asynchronously
    for index, file in enumerate(files):
        print(f"Uploading: {file.filename}")  # Log the file names
        file_path = os.path.join(session_folder, file.filename)
        file.save(file_path)
        uploaded_files.append(file.filename)

    # After all files are uploaded, trigger the cache increment task in a separate thread
    threading.Thread(target=increment_cache, args=(session_id,)).start()

    return jsonify({
        'message': 'Files uploaded successfully and cache increment triggered',
        'session_id': session_id,
        'uploaded_files': uploaded_files,
        'total_files': total_files
    }), 200


@app.route('/api/file-upload/<session_id>', methods=['POST'])
def upload_files(session_id):
    print(f"Session ID: {session_id}")  # Log the session ID

    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)  # Create session-specific folder

    if 'files[]' not in request.files:
        print("No file part")
        return jsonify({'error': 'No file part', 'session_id': session_id}), 400

    files = request.files.getlist('files[]')
    if not files or all(file.filename == '' for file in files):
        print("No selected files")
        return jsonify({'error': 'No selected files', 'session_id': session_id}), 400

    uploaded_files = []
    total_files = len(files)  # Total files to be uploaded

    # For each file uploaded, save it and then notify Laravel app asynchronously
    for index, file in enumerate(files):
        print(f"Uploading: {file.filename}")  # Log the file names
        file_path = os.path.join(session_folder, file.filename)
        file.save(file_path)
        uploaded_files.append(file.filename)

    return jsonify({
        'message': 'Files uploaded successfully and cache increment triggered',
        'session_id': session_id,
        'uploaded_files': uploaded_files,
        'total_files': total_files
    }), 200


@app.route('/api/clear/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)

    if os.path.exists(session_folder):
        shutil.rmtree(session_folder)  # Remove the folder and its contents
        return jsonify({'message': 'Session cleared successfully', 'session_id': session_id}), 200
    else:
        return jsonify({'error': 'Session not found', 'session_id': session_id}), 404


@app.route('/api/custom-prompt', methods=['GET'])
def custom_prompt():
    custom_prompt_file = 'dynamic/txt/custom_prompt.txt'
    default_content = ''
    
    # Read the content of custom_prompt.txt if it exists
    if os.path.exists(custom_prompt_file):
        with open(custom_prompt_file, 'r', encoding='utf-8') as f:
            default_content = f.read()
    
    # Return the content as a JSON response
    return jsonify({'content': default_content})


# Route to update the content of custom_prompt.txt
@app.route('/api/custom-prompt', methods=['POST'])
def update_custom_prompt():
    custom_prompt_file = 'dynamic/txt/custom_prompt.txt'
    
    # Get the new content from the request
    new_content = request.json.get('content', '')

    # Write the new content to the file
    try:
        with open(custom_prompt_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return jsonify({'message': 'Content updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<session_id>', methods=['GET'])
def download_file(session_id):
    try:
        # Construct the zip file name and path using OUTPUT_FOLDER
        zip_filename = f"{session_id}.zip"
        zip_filepath = os.path.join(app.config['OUTPUT_FOLDER'], session_id, zip_filename)

        # Check if the zip file exists
        if not os.path.exists(zip_filepath):
            return jsonify({'error': 'File not found'}), 404

        # Send the file for download using send_file
        return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)

    except Exception as e:
        print(f"Error during download_file: {e}")
        return jsonify({'error': 'An error occurred while trying to download the file.'}), 500

@app.route('/api/clear-output-files', methods=['GET'])
def clear_output_files():
    try:
        # Check if the OUTPUT_FOLDER exists
        output_folder = app.config['OUTPUT_FOLDER']
        if not os.path.exists(output_folder):
            return jsonify({'error': 'Output folder not found'}), 404

        # Walk through the output folder and delete everything
        for root, dirs, files in os.walk(output_folder, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                os.remove(file_path)  # Remove the file
            for name in dirs:
                dir_path = os.path.join(root, name)
                shutil.rmtree(dir_path)  # Remove the directory

        # After clearing, confirm the folder is empty
        if not os.listdir(output_folder):
            return jsonify({'message': 'All files and folders cleared successfully'}), 200
        else:
            return jsonify({'error': 'Failed to clear some files/folders'}), 500

    except Exception as e:
        print(f"Error while clearing output files: {e}")
        return jsonify({'error': 'An error occurred while clearing the output folder.'}), 500

@app.route('/api/clear-upload-files', methods=['GET'])
def clear_upload_files():
    try:
        # Check if the UPLOADS_FOLDER exists
        uploads_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(uploads_folder):
            return jsonify({'error': 'Uploads folder not found'}), 404

        # Walk through the uploads folder and delete everything
        for root, dirs, files in os.walk(uploads_folder, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                os.remove(file_path)  # Remove the file
            for name in dirs:
                dir_path = os.path.join(root, name)
                shutil.rmtree(dir_path)  # Remove the directory

        # After clearing, confirm the folder is empty
        if not os.listdir(uploads_folder):
            return jsonify({'message': 'All upload files and folders cleared successfully'}), 200
        else:
            return jsonify({'error': 'Failed to clear some files/folders'}), 500

    except Exception as e:
        print(f"Error while clearing upload files: {e}")
        return jsonify({'error': 'An error occurred while clearing the uploads folder.'}), 500

@app.route('/api/delete-upload-files', methods=['GET'])
def delete_upload_files():
    try:
        # Get the sessionId from the query parameter
        session_id = request.args.get('sessionId')

        if not session_id:
            return jsonify({'error': 'sessionId parameter is required'}), 400

        # Define the path to the session's folder
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)

        # Check if the session folder exists
        if not os.path.exists(session_folder):
            return jsonify({'error': f'Folder for session {session_id} not found'}), 404

        # Walk through the session folder and delete everything
        for root, dirs, files in os.walk(session_folder, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                os.remove(file_path)  # Remove the file
            for name in dirs:
                dir_path = os.path.join(root, name)
                shutil.rmtree(dir_path)  # Remove the directory

        # After clearing, remove the session folder itself
        shutil.rmtree(session_folder)

        # Confirm deletion
        if not os.path.exists(session_folder):
            return jsonify({'message': f'All files and folder for session {session_id} deleted successfully'}), 200
        else:
            return jsonify({'error': f'Failed to delete some files/folders for session {session_id}'}), 500

    except Exception as e:
        print(f"Error while deleting upload files for session {session_id}: {e}")
        return jsonify({'error': 'An error occurred while deleting the upload files.'}), 500

@app.route('/api/delete-output-files', methods=['GET'])
def delete_output_files():
    try:
        # Get the sessionId from the query parameter
        session_id = request.args.get('sessionId')

        if not session_id:
            return jsonify({'error': 'sessionId parameter is required'}), 400

        # Define the path to the session's folder
        session_folder = os.path.join(app.config['OUTPUT_FOLDER'], session_id)

        # Check if the session folder exists
        if not os.path.exists(session_folder):
            return jsonify({'error': f'Folder for session {session_id} not found'}), 404

        # Walk through the session folder and delete everything
        for root, dirs, files in os.walk(session_folder, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                os.remove(file_path)  # Remove the file
            for name in dirs:
                dir_path = os.path.join(root, name)
                shutil.rmtree(dir_path)  # Remove the directory

        # After clearing, remove the session folder itself
        shutil.rmtree(session_folder)

        # Confirm deletion
        if not os.path.exists(session_folder):
            return jsonify({'message': f'All files and folder for session {session_id} deleted successfully'}), 200
        else:
            return jsonify({'error': f'Failed to delete some files/folders for session {session_id}'}), 500

    except Exception as e:
        print(f"Error while deleting upload files for session {session_id}: {e}")
        return jsonify({'error': 'An error occurred while deleting the upload files.'}), 500

@app.route('/api/delete-all-files', methods=['GET'])
def delete_all_files():
    try:
        # Get the sessionId (query_id) from the query parameter
        session_id = request.args.get('sessionId')

        if not session_id:
            return jsonify({'error': 'sessionId parameter is required'}), 400

        # Define the path to the session's upload folder and output folder
        upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session_id)

        # Check if the upload folder exists, if not, return an error indicating that files have already been deleted
        if not os.path.exists(upload_folder) and not os.path.exists(output_folder):
            return jsonify({'error': f'Files for session {session_id} have already been deleted'}), 404

        # Delete upload files if the folder exists
        if os.path.exists(upload_folder):
            for root, dirs, files in os.walk(upload_folder, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)  # Remove the file
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    shutil.rmtree(dir_path)  # Remove the directory
            shutil.rmtree(upload_folder)  # Remove the session folder

        # Delete output files if the folder exists
        if os.path.exists(output_folder):
            for root, dirs, files in os.walk(output_folder, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)  # Remove the file
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    shutil.rmtree(dir_path)  # Remove the directory
            shutil.rmtree(output_folder)  # Remove the session folder

        # Remove the corresponding item from query_storage using session_id (query_id)
        global query_storage
        query_storage = [item for item in query_storage if item["query_id"] != session_id]

        # Confirm deletion of files and removal from query_storage
        return jsonify({
            'message': f'All upload and output files for session {session_id} deleted successfully and query removed from storage.'
        }), 200

    except Exception as e:
        print(f"Error while deleting files for session {session_id}: {e}")
        return jsonify({'error': 'An error occurred while deleting the files.'}), 500

@app.route('/api/download-template')
def download_template():
    template_file = 'static/txt/custom_prompt_template.txt'
    return send_file(template_file, as_attachment=True)

@app.route('/api/edit-default-options-value', methods=['POST'])
def edit_default_options_value():
    global maid_status_global
    maid_status_global = request.form.get('maid_status', 'None')
    print(f"maid type selected: {maid_status_global}")
    
    # Return JSON response
    return jsonify(success=True)

@app.route('/api/save-content', methods=['POST'])
@login_required
def save_content():
    content = request.form.get('content')

    if content.strip():  # Check if content is not empty or whitespace
        custom_prompt_file = 'dynamic/txt/custom_prompt.txt'
        with open(custom_prompt_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'message': 'Saved Successfully'}), 200
    else:
        return jsonify({'error': 'Content is empty'}), 400


@app.route('/api/query_storage', methods=['GET'])
@login_required
def get_query_storage():
    return jsonify(query_storage)

@app.route('/api/add-query-to-query-storage', methods=['GET'])
def add_query_to_query_storage():
    # Get query parameters from the URL
    query_label = request.args.get('query')  # Get 'query' parameter
    query_id = request.args.get('sessionId')  # Get 'sessionId' parameter
    
    if query_label and query_id:
        # Check if query_label or query_id already exists in query_storage
        for query in query_storage:
            if query['query_label'] == query_label or query['query_id'] == query_id:
                return jsonify({"error": "Query with the same label or ID already exists"}), 400
        
        # Create a new query item with the parameters
        new_query = {
            'query_label': query_label,
            'query_id': query_id,
            'status': 'waiting',  # Set status as 'inprogress'
            'up_time': '0 seconds',  # Placeholder for up_time, can be updated later
            'num_files': '0 files',  # Placeholder for num_files, can be updated later
            'rate': '0'  # Placeholder for rate, can be updated later
        }
        
        # Add the new query to query_storage
        query_storage.append(new_query)
        
        return jsonify({"message": "Query added successfully", "data": new_query}), 200
    else:
        return jsonify({"error": "Missing required parameters (sessionId, query)"}), 400


# @app.route('/')
# def home():
#     return "server is running"

#### --- FRONTEND -----

# Home route (secured)
@app.route('/')
@login_required
def index():
    global last_upload_time
    if last_upload_time:
        current_time = datetime.now()
        time_difference = current_time - last_upload_time
        minutes_difference = int(time_difference.total_seconds() / 60)

        if minutes_difference < 60:
            time_label = f"{minutes_difference} minutes ago"
        elif minutes_difference < 1440:
            hours_difference = int(minutes_difference / 60)
            time_label = f"{hours_difference} hour ago" if hours_difference == 1 else f"{hours_difference} hours ago"
        else:
            days_difference = int(minutes_difference / 1440)
            time_label = f"{days_difference} day ago" if days_difference == 1 else f"{days_difference} days ago"
    else:
        time_label = "-"

    return render_template('start/start-page.html', time_label=time_label, backendurl=BACKEND_API_URL)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login/login.html', error='Invalid credentials')
    return render_template('login/login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home_page():
    global image_fullpath_with_face_list, new_uploaded_pdf_file_path_list

    image_fullpath_with_face_list = []
    new_uploaded_pdf_file_path_list = []
    # uploaded_pdf_file_path_list = []

    if not check_authenticated():
        return redirect(url_for('login'))

    # Generate a unique session ID if not already created
    sessionID = str(uuid.uuid4()) 

    return render_template('home/home-page.html', backendurl=BACKEND_API_URL, sessionId=sessionID)

@app.route('/custom-prompt-editor', methods=['GET', 'POST'])
@login_required
def text_editor():
    if request.method == 'POST':
        # Handle form submission if needed
        pass

    # Fetch the custom prompt content from the /api/custom-prompt endpoint
    try:
        response = requests.get(f'{BACKEND_API_URL}/api/custom-prompt')
        response.raise_for_status()  # Raises an HTTPError if the response status is 4xx/5xx
        default_content = response.json().get('content', '')
    except requests.exceptions.RequestException as e:
        # In case of an error, fall back to an empty string or handle it accordingly
        default_content = ''

    return render_template('custom/custom-prompt-page.html', default_content=default_content, backendurl=BACKEND_API_URL)

@app.route('/default-options')
def edit_default_options():
    return render_template('default/default-options-page.html', maid_status_global=maid_status_global, backendurl=BACKEND_API_URL)

## add query page
@app.route('/add-query', methods=['GET', 'POST'])
def addquery():
    return render_template('add_query/add-query-page.html', backendurl=BACKEND_API_URL)

# @app.route('/create-query')
# @login_required
# def create_query():

#     session_id = request.args.get('sessionId')
#     query_id = request.args.get('query')

#     if not session_id:
#         # Handle case where sessionId is not provided
#         print(f"create query: error")
#         return "Session ID is missing", 400

#     if not check_authenticated():
#         return redirect(url_for('login'))

#     print(f"create query: {session_id}")
#     return jsonify({"message": "success", "sessionId": session_id, "queryId": query_id})

## new query page
@app.route('/new-query', methods=['GET', 'POST'])
def newquery():
    return render_template('new_query/new-query-page.html', backendurl=BACKEND_API_URL)

## running job page
@app.route('/running-jobs', methods=['GET', 'POST'])
def runningjobs():
    return render_template('running_jobs/running-jobs-page.html', backendurl=BACKEND_API_URL)

## processing status page
@app.route('/process/<session_id>')
@login_required
def processing_page(session_id):
    # Get the session_id from the query string
    # session_id = request.args.get('sessionId')

    if not session_id:
        # Handle case where sessionId is not provided
        return "Session ID is missing", 400

    if not check_authenticated():
        return redirect(url_for('login'))

    return render_template('process/process-page.html', session_id=session_id, backendurl=BACKEND_API_URL)

# Download files page
@app.route('/download-files')
@login_required
def download_files():
    # Get the session_id from the query string
    session_id = request.args.get('sessionId')

    if not session_id:
        # Handle case where sessionId is not provided
        return jsonify({"message": "Session ID is missing"}), 400

    if not check_authenticated():
        return redirect(url_for('login'))

    # Return a JSON response with the sessionId and a message
    return jsonify({"message": "Request successful", "sessionId": session_id})

# Route for handling the failed jobs page
@app.route('/failed-jobs')
@login_required
def failed_jobs():
    # Get the session_id from the query string
    session_id = request.args.get('sessionId')

    if not session_id:
        # Handle case where sessionId is not provided
        return jsonify({"message": "Session ID is missing"}), 400

    if not check_authenticated():
        return redirect(url_for('login'))

    # Return a JSON response with the sessionId and a message
    return jsonify({"message": "Redirecting to failed jobs", "sessionId": session_id})

# @app.route('/status')
# @login_required
# def status_page():
#     if not check_authenticated():
#         return redirect(url_for('login'))
#     return render_template('status/status-page.html')

if __name__ == '__main__':
    app.run(debug=True)
