from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import shutil

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

app.config['UPLOAD_FOLDER'] = 'uploads/'  # Make sure this folder exists
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16 MB

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
    for file in files:
        print(f"Uploading: {file.filename}")  # Log the file names
        file_path = os.path.join(session_folder, file.filename)
        file.save(file_path)
        uploaded_files.append(file.filename)

    total_files = len(uploaded_files)

    return jsonify({
        'message': 'Files uploaded successfully',
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


@app.route('/download-template')
def download_template():
    template_file = 'static/txt/custom_prompt_template.txt'
    return send_file(template_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
