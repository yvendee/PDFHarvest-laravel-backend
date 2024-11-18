from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import shutil
import requests
import threading
import time 

import shutil
import zipfile

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

LARAVEL_API_URL = os.environ.get('LARAVEL_API_URL', 'http://localhost:8000')  # Default to localhost:8000 if not set
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Make sure this folder exists
app.config['OUTPUT_FOLDER'] = 'output_files/'  # Make sure this folder exists
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16 MB


# Function to call the Laravel API every 1 second
def increment_cache(session_id):
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    while True:  # This will keep executing indefinitely until stopped
        print(f"[INFO] Increment cache task started for session: {session_id}")

        increment_url = f'{LARAVEL_API_URL}/incrementcache/{session_id}'
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

@app.route('/upload/<session_id>', methods=['POST'])
def upload_file(session_id):
    print(f"Session ID: {session_id}")  # Log the session ID

    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)  # Create session-specific folder

    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part', 'session_id': session_id}), 400

    files = request.files.getlist('files[]')
    if not files or all(file.filename == '' for file in files):
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


@app.route('/clear/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)

    if os.path.exists(session_folder):
        shutil.rmtree(session_folder)  # Remove the folder and its contents
        return jsonify({'message': 'Session cleared successfully', 'session_id': session_id}), 200
    else:
        return jsonify({'error': 'Session not found', 'session_id': session_id}), 404


@app.route('/custom-prompt', methods=['GET'])
def text_editor():
    custom_prompt_file = 'dynamic/txt/custom_prompt.txt'
    default_content = ''
    
    # Read the content of custom_prompt.txt if it exists
    if os.path.exists(custom_prompt_file):
        with open(custom_prompt_file, 'r', encoding='utf-8') as f:
            default_content = f.read()
    
    # Return the content as a JSON response
    return jsonify({'content': default_content})


# Route to update the content of custom_prompt.txt
@app.route('/custom-prompt', methods=['POST'])
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



@app.route('/download/<session_id>', methods=['GET'])
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

@app.route('/clear-output-files', methods=['GET'])
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

@app.route('/clear-upload-files', methods=['GET'])
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



@app.route('/download-template')
def download_template():
    template_file = 'static/txt/custom_prompt_template.txt'
    return send_file(template_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
