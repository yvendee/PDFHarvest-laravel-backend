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

import sys
import re
import random
from datetime import datetime

# import os
import io
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
# from flask_cors import CORS
from openai_api.utils.utils import ( get_summary_from_image, get_summary_from_text, get_summary_from_text_gpt4o, get_summary_from_text_test, get_summary_from_text_gpt4omini, get_summary_from_image_gpt4omini)
from anthropic_api.utils.utils import ( get_summary_from_image_using_claude )

from custom_prompt.utils.utils import read_custom_prompt
from csv_functions.utils.utils import save_csv
from log_functions.utils.utils import save_log
from tesseract.utils.utils import extract_text_from_image
import subprocess


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

GENERATE_CSV_FOLDER = 'output_csv'
DOWNLOAD_OCR_FILE_PATH = 'uploads/OCR.txt'

app.config['GENERATE_CSV_FOLDER'] = 'output_csv'

app.config['UPLOAD_FOLDER'] = 'uploads/'  # Make sure this folder exists
app.config['OUTPUT_FOLDER'] = 'output_files/'  # Make sure this folder exists
app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'] = 'output_extracted_profile_image/'
app.config['EXTRACTED_PAGE_IMAGES_FOLDER'] = 'output_extracted_page_image/'
app.config['GENERATE_CSV_FOLDER'] = 'output_csv'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATE_CSV_FOLDER'], exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16 MB

query_storage = []
progress = {}

# query_storage = [
#     {
#         "query_label": "Query1",
#         "query_id": "12345",
#         "status": "waiting",  # Status can be 'download', 'inprogress', 'waiting', or 'failed'
#         "up_time": "2 hours",
#         "num_files": "5 files",
#         "rate": "50 KB/s"
#     },
#     {
#         "query_label": "Query2",
#         "query_id": "67890",
#         "status": "waiting",
#         "up_time": "1 hour",
#         "num_files": "3 files",
#         "rate": "30 KB/s"
#     },
#     {
#         "query_label": "Query3",
#         "query_id": "11223",
#         "status": "waiting",
#         "up_time": "10 minutes",
#         "num_files": "10 files",
#         "rate": "70 KB/s"
#     },
#     {
#         "query_label": "Query4",
#         "query_id": "33445",
#         "status": "waiting",
#         "up_time": "5 minutes",
#         "num_files": "2 files",
#         "rate": "20 KB/s"
#     }
# ]

# Load the pre-trained face detection classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

image_fullpath_with_face_list = []
uploaded_pdf_file_list = []
uploaded_file_list = []
new_uploaded_pdf_file_path_list = []


def format_duration(duration):
    if duration >= 86400:  # More than or equal to 1 day (86400 seconds)
        days = duration // 86400
        return f"{days} day{'s' if days > 1 else ''}"
    elif duration >= 3600:  # More than or equal to 1 hour (3600 seconds)
        hours = duration // 3600
        return f"{hours} hour{'s' if hours > 1 else ''}"
    elif duration >= 60:  # More than or equal to 1 minute (60 seconds)
        minutes = duration // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:  # Less than 1 minute
        return f"{int(duration)} second{'s' if duration > 1 else ''}"

def copy_file(file_path, extracted_page_images_folder):
    
    """
    Copies a file from the given file path to the output folder.

    :param file_path: Full path of the file to copy.
    :param extracted_page_images_folder: Path to the destination folder.
    """
    # Extract the filename from the file path
    filename = os.path.basename(file_path)
    
    # Construct the destination file path
    destination_file = os.path.join(extracted_page_images_folder, filename)
    
    try:
        # Ensure the destination directory exists
        os.makedirs(extracted_page_images_folder, exist_ok=True)
        
        # Copy the file
        shutil.copy(file_path, destination_file)
        print(f"File '{filename}' copied successfully from '{file_path}' to '{extracted_page_images_folder}'.")
        return destination_file
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
    
    except PermissionError:
        print(f"Error: Permission denied while copying the file '{file_path}'.")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def copy_file2(filename, upload_folder, extracted_page_images_folder):
    """
    Copies a file from the upload folder to the output folder.

    :param filename: Name of the file to copy.
    :param upload_folder: Path to the source folder.
    :param extracted_page_images_folder: Path to the destination folder.
    """
    # Construct full file paths
    source_file = os.path.join(upload_folder, filename)
    destination_file = os.path.join(extracted_page_images_folder, filename)
    
    try:
        # Ensure the destination directory exists
        os.makedirs(extracted_page_images_folder, exist_ok=True)
        
        # Copy the file
        shutil.copy(source_file, destination_file)
        print(f"File '{filename}' copied successfully from '{upload_folder}' to '{extracted_page_images_folder}'.")
    
    except FileNotFoundError:
        print(f"Error: The file '{filename}' does not exist in the source directory '{upload_folder}'.")
    
    except PermissionError:
        print(f"Error: Permission denied while copying the file '{filename}'.")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def replace_extension_with_pdf(folder_path, filename):
    """
    Replace the extension of the given file with '.pdf' in the specified folder and return the new file path.

    :param folder_path: str, the folder where the file is located.
    :param filename: str, the name of the file whose extension needs to be replaced.
    :return: str, the new file path with '.pdf' extension.
    """
    try:
        # Construct the full path of the original file
        original_file_path = os.path.join(folder_path, filename)
        
        # Check if the file exists
        if not os.path.isfile(original_file_path):
            print(f"Error: File '{filename}' does not exist in '{folder_path}'.")
            return None
        
        # Split the file path into base name and extension
        base_name, _ = os.path.splitext(filename)
        
        # Construct the new file path with '.pdf' extension
        new_filename = f"{base_name}.pdf"
        new_file_path = os.path.join(folder_path, new_filename)
        
        # Rename the file to the new path
        os.rename(original_file_path, new_file_path)
        
        print(f"File renamed to: {new_file_path}")
        return new_file_path
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def convert_doctypes_to_pdf(doc_file, pdf_dir, session_id):
    global EXTRACTED_PAGE_IMAGES_FOLDER
    try:
        # Use the subprocess module to run the soffice command for conversion
        process = subprocess.Popen(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', pdf_dir, doc_file])
        
        
        # save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"PDF Conversion started!")
        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        save_log(os.path.join(session_folder, "logs.txt"),f"PDF Conversion started!")


        # Wait for the conversion to complete
        while process.poll() is None:
            time.sleep(1)  # Sleep for 1 second


        pdf_path = os.path.join(pdf_dir, f"{os.path.splitext(os.path.basename(doc_file))[0]}.pdf")

        # Check if the conversion was successful
        if process.returncode == 0:

            print(f"Conversion complete. PDF saved to {pdf_path}")

            # save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"Conversion complete. PDF saved to {pdf_path}")
            session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
            save_log(os.path.join(session_folder, "logs.txt"), f"Conversion complete. PDF saved to {pdf_path}")

            return pdf_path
        else:
            
            # save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"PDF Conversion failed.")
            session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
            save_log(os.path.join(session_folder, "logs.txt"), f"PDF Conversion failed. {pdf_path}")

            print(f"Conversion failed. {pdf_path}")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")

        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        save_log(os.path.join(session_folder, "logs.txt"),f"Error during PDF conversion start: {str(e)} {pdf_path}")
        return None

# Function to extract filenames and content from the input text
def extract_data_from_text(text):
    # Regular expression to match the pattern
    pattern = r'\[start\](.*?)\[/start\](.*?)\[end\]\1\[/end\]'
    
    # Find all matches in the input text
    matches = re.findall(pattern, text, re.DOTALL)
    
    # Organize matches into a list of lists
    result = [[filename.strip(), content.strip()] for filename, content in matches]
    
    return result

def copy_files_to_directory(file_paths, target_directory):
    """
    Copies files specified by file_paths to the target_directory.
    
    Args:
    - file_paths (list): List of full file paths to be copied.
    - target_directory (str): Directory where files will be copied.
    
    Returns:
    - None
    """
    # Create the target directory if it doesn't exist
    os.makedirs(target_directory, exist_ok=True)
    
    # Iterate through the list of file paths and copy each file to the target directory
    for file_path in file_paths:
        # Extract the filename from the full path
        file_name = os.path.basename(file_path)
        
        # Construct the full target path
        target_path = os.path.join(target_directory, file_name)
        
        # Copy the file to the target directory
        shutil.copy(file_path, target_path)
        print(f"Copied {file_path} to {target_path}")
        new_uploaded_pdf_file_path_list.append(target_path)

def count_words(input_string):
    # Split the input string by whitespace and count the number of elements
    words = input_string.split()
    return len(words)

# Function to process each data item
def uppercase_the_first_letter(item):
    # Split the item into words, lowercase each word, capitalize the first letter
    words = item.split()
    processed_words = [word.lower().capitalize() for word in words]
    return ' '.join(processed_words)

def rename_files(image_fullpath_with_face_list, maid_refcode_list): ## rename extracted images with maid ref code
    
    try:
        # Iterate through both lists simultaneously
        for i in range(len(image_fullpath_with_face_list)):

            if(image_fullpath_with_face_list[i] == "no-picture-found"):
                print("no picture found!")
            else:
            #     print("with picture found!")
            
                original_path = image_fullpath_with_face_list[i]
                maidrefcode = maid_refcode_list[i]

                # Extract filename and extension
                filename, extension = os.path.splitext(original_path)

                # Check if maidrefcode is not empty
                if maidrefcode:
                    # Form new filename with maidrefcode and original extension
                    new_filename = f"{maidrefcode}{extension}"

                    # Construct new full path
                    new_fullpath = os.path.join(os.path.dirname(original_path), new_filename)

                    try:
                        # Rename the file
                        os.rename(original_path, new_fullpath)

                        # Update image_fullpath_with_face_list with new path
                        image_fullpath_with_face_list[i] = new_fullpath

                    except OSError as e:
                        print(f"Error renaming {original_path} to {new_fullpath}: {e}")
    except:
        pass

    # Return the updated image_fullpath_with_face_list
    return image_fullpath_with_face_list

def rename_files2(pdf_file_list, maid_refcode_list):  ## rename input pdf's with maid ref code
    # Iterate through both lists simultaneously
    for i in range(len(pdf_file_list)):
        original_path = pdf_file_list[i]
        maidrefcode = maid_refcode_list[i]

        # Extract filename and extension
        filename, extension = os.path.splitext(original_path)

        # Check if maidrefcode is not empty
        if maidrefcode:
            # Form new filename with maidrefcode and original extension
            new_filename = f"{maidrefcode}{extension}"

            # Construct new full path
            new_fullpath = os.path.join(os.path.dirname(original_path), new_filename)

            try:
                # Rename the file
                os.rename(original_path, new_fullpath)

                # Update pdf_file_list with new path
                pdf_file_list[i] = new_fullpath

            except OSError as e:
                print(f"Error renaming {original_path} to {new_fullpath}: {e}")

    # Return the updated pdf_file_list
    return pdf_file_list

def summary_generation(total_summary, output_folder, base_name, session_id):

    results_from_ocr = total_summary
    maid_ref_code_value = ""

    # Call the function to read and print the content of custom_prompt.txt
    custom_prompt = read_custom_prompt("dynamic/txt/custom_prompt.txt")

    pattern = r'\[(.*?)\]'
    matches_list = re.findall(pattern, custom_prompt)
    # print(matches_list)

    # Filter out "y1" and "y2" from matches_list
    matches_list = [match for match in matches_list if match not in ["y1", "y2"]]   

    # Initialize summary_dict based on matches_list
    # summary_dict = {match: "" for match in matches_list}

    # Initialize summary_dict with lowercase keys based on matches_list
    summary_dict = {match.lower(): "Null" for match in matches_list}

    # print(summary_dict)
    
    summary_text = ""

    if custom_prompt not in ["Not Found", "Read Error"]:

        total_summary += custom_prompt + "\n"

        if current_structured_text == 'gpt35':

            # Count words in the input string
            word_count = count_words(total_summary)

            print(f"word count: {word_count}")

            # save_log(os.path.join(output_folder, "logs.txt"),f"word count: {word_count} , gpt3.5 words limit is 3000")

            session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
            save_log(os.path.join(session_folder, "logs.txt"),f"word count: {word_count} , gpt3.5 words limit is 3000")

            
            # Check word count and print appropriate message
            if word_count <= 2900:
                print("Sending text to OpenAI  GPT3.5...")
                # save_log(os.path.join(output_folder, "logs.txt"),"Sending text to OpenAI GPT3.5...")
                session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                save_log(os.path.join(session_folder, "logs.txt"),"Sending text to OpenAI GPT3.5...")
                summary_text = get_summary_from_text(total_summary, session_id) ## summary text from gpt3.5
            else:
                # save_log(os.path.join(output_folder, "logs.txt"),"Words limit exceeds..switching to GPT4o")
                # save_log(os.path.join(output_folder, "logs.txt"),"Sending text to OpenAI GPT4o...")

                session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                save_log(os.path.join(session_folder, "logs.txt"),"Words limit exceeds..switching to GPT4o")
                save_log(os.path.join(session_folder, "logs.txt"),"Sending text to OpenAI GPT4o...")

                summary_text = get_summary_from_text_gpt4o(total_summary, session_id) ## summary text from gpt4o
        else:  ## gpt4omini

            # Count words in the input string
            word_count = count_words(total_summary)

            print("Sending text to OpenAI  GPT4omini...")
            # save_log(os.path.join(output_folder, "logs.txt"),"Sending text to OpenAI GPT4omini...")
            session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
            save_log(os.path.join(session_folder, "logs.txt"),"Sending text to OpenAI GPT4omini...")
            summary_text = get_summary_from_text_gpt4omini(total_summary, session_id) ## summary text from gpt4omini

        ## test
        # summary_text = get_summary_from_text_test(total_summary, session_id)

        # Extracting values and updating summary_dict
        pattern = r'\[(.*?)\]:\s*(.*)'
        matches = re.findall(pattern, summary_text)

        for key, value in matches:
            if key in summary_dict:
                # Check if value is empty, then set to "Null"
                if not value.strip():
                    value = "Null"
                summary_dict[key] = value.strip()

        ##=========== Special Case Here For Initial Setting of Key Values ================##

        try:
            maid_name_value = summary_dict.get("maid name", "")

            # Define a regular expression pattern to match unwanted characters
            pattern = re.compile(r'[^a-zA-Z ]')

            # Replace unwanted characters with an empty string
            maid_name_value_cleaned = re.sub(pattern, '', maid_name_value)
            maid_name_value_cleaned = maid_name_value_cleaned.replace('"',"")
            maid_name_value_cleaned = maid_name_value_cleaned.strip()
            summary_dict["maid name"] = maid_name_value_cleaned

        except Exception as e:
            print(f"Error occurred: {e}")
            

        Is_incorrect_birth_date = "no"

        try:

            # Get the maid ref code and birth date value from the dictionary
            maid_ref_code_value = summary_dict.get("maid ref code", "")
            birth_date_value = summary_dict.get("date of birth", "")

            # List of unwanted values
            unwanted = [
                "not provided", "n/a", "n.a", "null", "not found", "not-found",
                "not specified", "not applicable", "none", "not mentioned",
                "not-mentioned", "not evaluated"
            ]

            # Define the pattern to check for both alphabets and numbers
            pattern = r'(?=.*[A-Za-z])(?=.*\d)'

            # Single maid_ref_code_value to check
            maid_ref_code_value_cleaned = maid_ref_code_value.strip().lower()

            # if maid_ref_code_value_cleaned in unwanted:
            if maid_ref_code_value_cleaned in unwanted or not re.search(pattern, maid_ref_code_value_cleaned):

                # Get the maid name value or an empty string if the key is not present
                maid_name_value = summary_dict.get("maid name", "")

                # Get the first two letters, convert them to uppercase, and handle cases where the name might be shorter
                first_two_letters = maid_name_value[:2].upper()

                # print(first_two_letters)

                birthdate_value = summary_dict.get("date of birth", "")  # assuming format is 'DD/MM/YYYY'
                birthdate_value = birthdate_value.strip()
                # # Remove unwanted characters 
                # birthdate_pattern = r'[^0-9/]'  # Matches any character that is NOT a digit or "/"
                # # Replace all characters not matching the pattern with whitespace
                # birthdate_value = re.sub(birthdate_pattern, ' ', birthdate_value)

                # Remove unwanted characters (keep only 0-9, '/', and ignore whitespace and ',')
                pattern = r'[^\d/]'  # This pattern matches any character that is NOT a digit (0-9) or '/'

                # Replace all characters not matching the pattern with an empty string
                birthdate_value = re.sub(pattern, '', birthdate_value)

                # print(f"birth_date:  {birthdate_value}")

                # Check if birthdate_value is empty or incorrectly formatted
                formatted_birthdate = ""
                if birthdate_value:
                    if len(birthdate_value) != 10 or birthdate_value[2] != '/' or birthdate_value[5] != '/':
                        print("incorrect birth date format")
                        formatted_birthdate = ""
                        Is_incorrect_birth_date = "yes"
                    else:
                        try:
                            day, month, year = birthdate_value.split('/')
                            
                            # Format the maid ref "YYMMDD"
                            formatted_birthdate = f"{year[-2:]}{month.zfill(2)}{day.zfill(2)}"
                            print("correct birth date format")

                        except ValueError:
                            print("incorrect birth date format")
                            formatted_birthdate = ""
                            Is_incorrect_birth_date = "yes"
                else:
                    print("incorrect birth date format")
                    formatted_birthdate = ""
                    Is_incorrect_birth_date = "yes"

                # Append formatted_birthdate to first_two_letters
                maid_ref_code_value = first_two_letters + formatted_birthdate

                if(Is_incorrect_birth_date == "no"):
                    # Remove unwanted characters 
                    pattern = r'[^0-9A-Z]' # acceptable character are 0 to 9 and all capital letters
            
                    # Replace all characters not matching the pattern with whitespace
                    maid_ref_code_value = re.sub(pattern, '', maid_ref_code_value)

                    # Remove all whitespace from the cleaned string
                    maid_ref_code_value = ''.join(maid_ref_code_value.split())

                    # Remove unnecessary leading and trailing spaces
                    maid_ref_code_value = maid_ref_code_value.strip()

                    maid_ref_code_value = maid_ref_code_value.replace(' ',"")

                    # maidrefcode_list.append(maid_ref_code_value)
                    summary_dict["maid ref code"] = maid_ref_code_value

                else:
                    # Generate a 6-digit random number
                    random_number = random.randint(100000, 999999)

                    # Append the random number to maid_ref_code_value
                    maid_ref_code_value = first_two_letters + str(random_number)
                    ## append to maidrefcode_list for renaming of extracted inage with  face

                    # Remove unwanted characters 
                    pattern = r'[^0-9A-Z]' # acceptable character are 0 to 9 and all capital letters
            
                    # Replace all characters not matching the pattern with whitespace
                    maid_ref_code_value = re.sub(pattern, '', maid_ref_code_value)
                    
                    # Remove all whitespace from the cleaned string
                    maid_ref_code_value = ''.join(maid_ref_code_value.split())

                    # Remove unnecessary leading and trailing spaces
                    maid_ref_code_value = maid_ref_code_value.strip()

                    maid_ref_code_value = maid_ref_code_value.replace(' ',"")

                    # maidrefcode_list.append(maid_ref_code_value)
                    summary_dict["maid ref code"] = maid_ref_code_value
                    
            else:

                # Remove unwanted characters 
                pattern = r'[^0-9A-Z]' # acceptable character are 0 to 9 and all capital letters
        
                # Replace all characters not matching the pattern with whitespace
                maid_ref_code_value = re.sub(pattern, '', maid_ref_code_value)

                # Format the birth date by removing slashes
                formatted_birth_date = birth_date_value.replace("/", "")

                # Concatenate the maid ref code and the formatted birth date
                # result = maid_ref_code_value + formatted_birth_date
                result = maid_ref_code_value

                result = result.replace("-","")

                # print(result)  # Output should be "JS1234071699"

                # Remove unnecessary leading and trailing spaces
                result = result.strip()

                result = result.replace(' ',"")

                summary_dict["maid ref code"] = result
                maid_ref_code_value = result
                # maidrefcode_list.append(result)

        except Exception as e:
            print(f"Error occurred: {e}")

            # Generate a 6-digit random number
            random_number = random.randint(100000, 999999)

            # Append the random number to maid_ref_code_value
            maid_ref_code_value += str(random_number)
            ## append to maidrefcode_list for renaming of extracted inage with  face

            # Remove unwanted characters 
            pattern = r'[^0-9A-Z]' # acceptable character are 0 to 9 and all capital letters
    
            # Replace all characters not matching the pattern with whitespace
            maid_ref_code_value = re.sub(pattern, '', maid_ref_code_value)
            
            # Remove all whitespace from the cleaned string
            maid_ref_code_value = ''.join(maid_ref_code_value.split())

            # Remove unnecessary leading and trailing spaces
            maid_ref_code_value = maid_ref_code_value.strip()

            # maidrefcode_list.append(maid_ref_code_value)
            summary_dict["maid ref code"] = maid_ref_code_value


        if maid_status_global == "None":

            try:
                # Getting the value corresponding to the key "maid type"" then stored
                maid_type_option_id_value = summary_dict.get("maid type", "")
                maid_type_option_id_value = maid_type_option_id_value.strip().lower()
                if maid_type_option_id_value in ["ex maid", "transfer maid", "ex-sg maid"]:
                    if maid_type_option_id_value == "ex-sg maid":
                        summary_dict["maid type"] = "Ex-SG Maid"
                    else:
                        summary_dict["maid type"] = maid_type_option_id_value
                else:
                    summary_dict["maid type"] = "New Maid"
            except Exception as e:
                print(f"Error occurred: {e}")
        else:

            try:
                summary_dict["maid type"] = maid_status_global
            except Exception as e:
                print(f"Error occurred: {e}")


        try:
            education_id_value = summary_dict.get("education", "")
            # - Others
            # - Diploma/Degree (>=13 yrs)
            # - High School (11-12 yrs)
            # - Secondary Level (7-10 yrs)
            # - Primary Level (1-6 yrs)
            if education_id_value.strip().lower() in ["diploma/degree (>=13 yrs)", "high school (11-12 yrs)", "secondary level (7-10 yrs)", "primary level (1-6 yrs)"]:
                summary_dict["education"] = education_id_value.strip().lower()
            else:
                summary_dict["education"] = "Others"
        except Exception as e:
            print(f"Error occurred: {e}")


        try:
            religion_id_value = summary_dict.get("religion", "")
            #Buddhist|Catholic|Christian|Free Thinker|Hindu|Muslim|Sikh|Others
            if religion_id_value.strip().lower() in ["buddhist", "catholic", "christian", "free thinker","hindu", "muslim", "sikh"]:
                summary_dict["religion"] = religion_id_value.strip().lower()
            else:
                summary_dict["religion id"] = "Others"
        except Exception as e:
            print(f"Error occurred: {e}")

        try:
            maid_preferred_rest_day_id_value = summary_dict.get("maid preferred rest day", "")
            if "all sun" in maid_preferred_rest_day_id_value.strip().lower():
                summary_dict["maid preferred rest day"] = "4 rest days per month"
            elif maid_preferred_rest_day_id_value.strip().lower() in ["1 rest days per month", "2 rest days per month", "3 rest days per month", "4 rest days per month"]:
                summary_dict["maid preferred rest day"] = maid_preferred_rest_day_id_value.strip().lower()
            else:
                summary_dict["maid preferred rest day"] = "1 rest days per month"
        except Exception as e:
            print(f"Error occurred: {e}")

        try:
            # Define the marker strings before and after maid introduction
            start_marker = '[public maid introduction]:'
            end_marker = '\n['

            # Find the start and end positions of the maid introduction section
            start_pos = summary_text.find(start_marker)
            end_pos = summary_text.find(end_marker, start_pos)

            # Extract the maid introduction section
            if start_pos != -1 and end_pos != -1:
                maid_introduction = summary_text[start_pos + len(start_marker):end_pos].strip()
                # print(maid_introduction)
                summary_dict["public maid introduction"] = maid_introduction
            else:
                print("No public maid introduction found in the input.")
        except Exception as e:
            print(f"Error occurred: {e}")

        try:
            # Getting the value corresponding to the key "marital status" then stored
            marital_status_option_id_value = summary_dict.get("marital status", "")
            # Single|Married|Widowed|Divorced|Separated
            if marital_status_option_id_value.strip().lower() in ["single", "married", "widowed", "divorced", "separated"]:
                summary_dict["marital status"] = marital_status_option_id_value.strip().lower()
            else:
                summary_dict["marital status"] = "single"
        except Exception as e:
            print(f"Error occurred: {e}")


        ##================================================================================##

        # Creating values_array based on summary_dict
        values_array = []
        for key in summary_dict:
            if summary_dict[key] == '':
                values_array.append(' ')
            else:
                values_array.append(summary_dict[key])

        # Print the updated summary_dict and values_array
        # print(summary_dict)
        # print(values_array)

        # save_log(os.path.join(output_folder, "logs.txt"),f"Appending data to output.csv")
        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        save_log(os.path.join(session_folder, "logs.txt"), f"Appending data to output.csv")

        session_csv_folder = os.path.join(app.config['GENERATE_CSV_FOLDER'] , session_id)
        # csv_path = f'output_csv/{session_id}.csv'
        save_csv(os.path.join(session_csv_folder, f"{session_id}.csv"), matches_list, values_array)

    with open(os.path.join(output_folder, f'{session_id}-summary.txt'), "a", encoding="utf-8") as text_file:
        text_file.write(f"[start]{base_name}[/start]\n")
        text_file.write(str(summary_dict))
        text_file.write("\n")
        text_file.write(summary_text)
        text_file.write(f"\n[end]{base_name}[/end]\n")
    
    return results_from_ocr, maid_ref_code_value

####### PDF to Images Extraction ################
def pdf_to_jpg(pdf_file, output_folder, session_id, zoom=2):
    global last_upload_time, maid_status_global

    # Get the base name of the PDF file to create a subfolder
    base_name = os.path.splitext(os.path.basename(pdf_file))[0]
    base_name = base_name.replace(" ","_")
    subfolder = os.path.join(output_folder, base_name)
    
    # Ensure the output subfolder exists
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)
    
    # Open the PDF file
    pdf_document = fitz.open(pdf_file)

    # save_log(os.path.join(output_folder, "logs.txt"),f"Opening pdf file: {pdf_file}")

    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),f"Opening pdf file: {pdf_file}")

    
    # List to store the filenames of the images for each page
    page_images = []

    # String to store the summary for each page
    total_summary = ""
    results_from_ocr = ""
    
    # Iterate through each page of the PDF
    for page_num in range(len(pdf_document)):
        # Set the datetime
        last_upload_time = datetime.now()

        # Get the page
        page = pdf_document.load_page(page_num)
        
        # Set the zoom factor for higher resolution
        mat = fitz.Matrix(zoom, zoom)
        
        # Convert page to image
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save image as JPEG
        image_filename = os.path.join(subfolder, f"page_{page_num + 1}.jpg")
        img.save(image_filename, "JPEG")
        page_images.append(image_filename)
        # print(f"Page {page_num + 1} of {pdf_file} saved as {image_filename}")
        # print(image_filename)

        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        save_log(os.path.join(session_folder, "logs.txt"),f"Page {page_num + 1} of {pdf_file} extracted")
        save_log(os.path.join(session_folder, "logs.txt"),f"Current OCR used is {current_ocr}")

        if current_ocr == 'gpt4oOCR':
            summary = get_summary_from_image(image_filename, session_id) ## summary text from gpt4o OCR
        elif current_ocr == 'tesseractOCR':
            summary = extract_text_from_image(image_filename, session_id) ## extracted text from local tesseract OCR
        elif current_ocr == 'claudeOCR':
            summary = get_summary_from_image_using_claude(image_filename, session_id) ## summary text from claude Haiku OCR
        elif current_ocr == 'gpt4ominiOCR':
            summary = get_summary_from_image_gpt4omini(image_filename, session_id) ## summary text from gpt4omini OCR
        else:
            summary = get_summary_from_image_gpt4omini(image_filename, session_id) ## summary text from gpt4omini OCR

        ## this is a test code
        # summary = "summary_from_page"
        # random_number = random.randint(1000, 9999)
        # summary = summary + str(random_number)

        total_summary += summary + "\n"  # Add newline between summaries
    
    # Close the PDF file
    pdf_document.close()

    results_from_ocr, maid_ref_code = summary_generation(total_summary, output_folder, base_name, session_id)
    
    # ## this is a test
    # random_number = random.randint(1000, 9999)
    # maid_ref_code = "maid_ref_code_test" + str(random_number)
    # # results_from_ocr = "test"

    # Print the list of page image filenames
    # print(f"List of page images for {pdf_file}: {page_images}")

    ## Write total_summary
    # session_folder = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
    # with open(os.path.join(session_folder, f"OCR-{session_id}.txt"), "a", encoding="utf-8") as text_file:
    with open(os.path.join(output_folder, f'{session_id}-OCR.txt'), "a", encoding="utf-8") as text_file:
        text_file.write(f"[start]{base_name}[/start]\n")
        text_file.write(results_from_ocr)
        text_file.write(f"\n[end]{base_name}[/end]\n")

    # save_log(os.path.join(output_folder, "logs.txt"),"hello")
    print(f"maid-ref-code is {maid_ref_code} for {base_name}.pdf" )
    return page_images, maid_ref_code

####### PDF to profile Picture Extraction #######

# Function to resize an image proportionately if either dimension is above 250 px
def resize_image_if_needed(image_pil):
    width, height = image_pil.size

    if width > 250 or height > 250:
        if width > height:
            scaling_factor = 250 / width
        else:
            scaling_factor = 250 / height

        new_width = int(width * scaling_factor)
        new_height = int(height * scaling_factor)

        # Resize image
        return image_pil.resize((new_width, new_height), Image.LANCZOS)
    return image_pil

# Function to extract images with faces from a specific PDF file
def extract_images_with_faces(pdf_path, session_id):
    global image_fullpath_with_face_list, face_cascade
    # Get the base name of the PDF file
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    # Create the main folder if it doesn't exist
    main_folder = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
    if not os.path.exists(main_folder):
        os.makedirs(main_folder)

    extracted_images = []
    pdf_document = fitz.open(pdf_path)
    try:
        # Extract images from the first page only
        page_number = 0
        page = pdf_document[page_number]
        image_list = page.get_images(full=True)
        face_found = False  # Flag to track if a face has been found on the first page
        page_width = page.rect.width
        page_height = page.rect.height
        # print(f"page-width: {page_width} page-height: {page_height}")
        # print(f"image list: {len(image_list)} for {pdf_basename}")

        for img in image_list:
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_pil0 = Image.open(io.BytesIO(image_bytes))
            image_cv2 = cv2.cvtColor(np.array(image_pil0), cv2.COLOR_RGB2BGR)

            img_width, img_height = image_pil0.size
            print(f"img-width: {img_width} img-height: {img_height}")

            if page_width > img_width and page_height > img_height:
                print("Page size is larger than the extracted image size.")
            if img_width > 3 * page_width and img_height > 3 * page_height:
                print("The image size is more than triple the size of the page size.")

                box_width_percentage = 150
                box_height_percentage = 150

                faces = face_cascade.detectMultiScale(image_cv2, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                if len(faces) > 0 and not face_found:
                    face_found = True
                    for (x, y, w, h) in faces:
                        center_x = x + w // 2
                        center_y = y + h // 2

                        box_width = int(w * (box_width_percentage / 100))
                        box_height = int(h * (box_height_percentage / 100))

                        top_left_x = max(0, center_x - box_width // 2)
                        top_left_y = max(0, center_y - box_height // 2)
                        bottom_right_x = min(image_cv2.shape[1], center_x + box_width // 2)
                        bottom_right_y = min(image_cv2.shape[0], center_y + box_height // 2)

                        # Crop the image to the bounding box
                        cropped_face = image_cv2[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
                        cropped_face_pil = Image.fromarray(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB))
                        
                        # Save the cropped face image
                        cropped_face_filename = f"{pdf_basename}_cropped_face.jpg"  # Naming based on PDF base name
                        cropped_face_fullpath = os.path.join(main_folder, cropped_face_filename)
                        cropped_face_pil.save(cropped_face_fullpath, "JPEG")
                        extracted_images.append(cropped_face_pil)
                        image_fullpath_with_face_list.append(cropped_face_fullpath)  
                        break
            else:
                # Convert to grayscale for face detection
                gray_image = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                # print(f"Number of faces detected: {len(faces)}")

                # Resize the image if needed
                image_pil = resize_image_if_needed(image_pil0)

                if len(faces) > 0 and not face_found:
                    # If a face is detected and no face has been found yet on the first page
                    face_found = True
                    
                    image_with_face_filename = f"{pdf_basename}_with_face.jpg"  # Naming based on PDF base name
                    image_with_face_fullpath = os.path.join(main_folder, image_with_face_filename)

                    # Save the image 
                    image_pil.save(image_with_face_fullpath, "JPEG")
                    extracted_images.append(image_pil)
                    image_fullpath_with_face_list.append(image_with_face_fullpath)  

                    break  # Stop processing further images on the first page once a face is found

        print(f"Processed {pdf_path}: {len(extracted_images)} images extracted with faces")

        if not face_found:
            image_fullpath_with_face_list.append("no-picture-found")

    except Exception as e:
        print(f"Error has occurred during face detection: {e}")

    pdf_document.close()
    
    return image_fullpath_with_face_list

# Function to process a specific PDF file in the "uploads" folder
def process_pdf_extract_image(filename, session_id):

    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    pdf_path = os.path.join(session_folder, filename)
    if os.path.exists(pdf_path) and pdf_path.endswith(".pdf"):
        extracted_images = extract_images_with_faces(pdf_path, session_id)
        # print(f"Processed {pdf_path}: {len(extracted_images)} images extracted with faces")
        # save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"Processed {pdf_path}: {len(extracted_images)} images extracted with faces")
        return extracted_images

    else:
        print(f"File '{filename}' not found or is not a PDF.")
        save_log(os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], "logs.txt"),f"File '{filename}' not found or is not a PDF.")



def check_queries():

    # Flag to indicate if we found and changed a "waiting" item
    found_waiting = False

    while True:
        if not found_waiting:
            # Loop over each item in the query_storage
            for index, item in enumerate(query_storage):
                if item["status"] == "waiting":
                    # Change status to "inprogress"
                    item["status"] = "inprogress"
                    found_waiting = True
                    print(f"INFO: [EXECUTE] {item['query_label']} ({item['query_id']}) ")

                    # Trigger the URL using test client
                    session_id = item["query_id"]
                    try:
                        run_process_files(session_id)  # Call the function to simulate the request
                    except Exception as e:
                        print(f"Error occurred while triggering process for session {session_id}: {e}")
                    

                    # print(f"Changing status for {item['query_label']} ({item['query_id']}) to 'inprogress'")
                    break  # Stop checking after changing the first "waiting" item

         # Loop over each item in the query_storage
        for index, item in enumerate(query_storage):
            if item["status"] == "inprogress":
                # print(f"{item['query_label']} ({item['query_id']}) --> 'inprogress'")
                break  # Stop checking after changing the first "waiting" item

            if item["status"] == "waiting":
                found_waiting = False
                break
        time.sleep(5)

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


def get_maid_status(query_id):
    # Search for the item with the given query_id
    for query in query_storage:
        if query.get('query_id') == query_id:
            return query.get("maid_status_id")  # Return the maid_status_id if found

    return None  # Return None if no matching query_id is found

# Update query storage status function
def update_query_storage_status(session_id, new_status):
    for query in query_storage:
        if query['query_id'] == session_id:  # Assuming session_id matches query_id in query_storage
            query['status'] = new_status
            print(f"Status updated for session {session_id}: {new_status}")
            break

# Update query storage time function
def update_query_storage_uptime(session_id, new_time):
    for query in query_storage:
        if query['query_id'] == session_id: 
            query['up_time'] = new_time
            print(f"Uptime updated for session {session_id}: {new_time}")
            break

# Update query storage num_files function
def update_query_storage_num_files(session_id, num_files):
    for query in query_storage:
        if query['query_id'] == session_id: 
            query['num_files'] = num_files
            print(f"Number of Files updated for session {session_id}: {num_files}")
            break

# Update query storage rate function
def update_query_storage_rate(session_id, new_rate):
    for query in query_storage:
        if query['query_id'] == session_id: 
            query['rate'] = new_rate
            print(f"Rate updated for session {session_id}: {new_rate}")
            break

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

# @app.route('/api/process', methods=['GET'])
@app.route('/api/process/<session_id>', methods=['GET'])
@login_required
def process_files(session_id):
    # session_id = request.args.get('sessionId')

    # global image_fullpath_with_face_list, uploaded_pdf_file_list, uploaded_file_list, new_uploaded_pdf_file_path_list
    global uploaded_pdf_file_list, uploaded_file_list, new_uploaded_pdf_file_path_list, maid_status_global

    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401

    if session_id not in progress:
        return jsonify({'error': 'Invalid session ID'}), 400

    def mock_processing(session_id):
        maid_status_id_value = get_maid_status(session_id)
        maid_status_global = maid_status_id_value
        print(f"maid status set value: {maid_status_id_value}")
        start_time = time.time()  # Record the start time
        total_files = ""
        with app.app_context(): ## By pushing the application context manually, you ensure that Flask has the necessary context to handle things like query_storage without running into the "Working outside of application context" error.
            print(f"INFO: Processing started for session: {session_id}")
            new_pdf_list = []
            maidrefcode_list = []
            try:
                session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                uploaded_files = os.listdir(session_folder)
                # print(uploaded_files)
                total_files = len(uploaded_files)
                update_query_storage_num_files(session_id, f"{total_files} files")
                progress[session_id]['total'] = total_files
                print(f"Total files in the uploads is {total_files} with session ID {session_id}")


                session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                save_log(os.path.join(session_folder, "logs.txt"),f"Uploaded file list: {str(uploaded_file_list)}")
                

                # for index, filename in enumerate(uploaded_files):
                index = 0
                for i in range (len(uploaded_file_list)):
                    file_path = uploaded_file_list[i]
                    filename = os.path.basename(file_path)
                    file_ext = os.path.splitext(filename)[1].lower()

                    ### pdf conversion
                    try:

                        # Check the file extension and convert if necessary
                        if file_ext in ['.doc', '.docx']:
                            # pdf_path = replace_extension_with_pdf(app.config['UPLOAD_FOLDER'], filename)
                            session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                            converted_pdf_path = convert_doctypes_to_pdf(file_path, session_folder, session_id)
                            if converted_pdf_path:
                                print (f"Success converting a file")
                                filename = os.path.basename(converted_pdf_path)
                                session_folder = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
                                new_file_path = copy_file(converted_pdf_path, session_folder)
                                new_pdf_list.append(new_file_path)
                                
                            else:
                                print (f"Error converting a file")
                        else:
                            # For PDF files or unsupported formats, use the original path
                            session_folder = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
                            new_file_path = copy_file(file_path, session_folder)
                            new_pdf_list.append(new_file_path)
    
                    except Exception as e:
                        print (f"Error has occurred during documents to pdf conversion {e}")

                    # Simulate processing of each file
                    # time.sleep(1)  # Simulate processing delay
                    # time.sleep(2)  # Simulate processing delay

                    image_with_face_list = process_pdf_extract_image(filename, session_id) ## extract the profile picture and
                    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                    pdf_path = os.path.join(session_folder, filename)
                    extracted_image_session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                    page_images, maid_ref_code = pdf_to_jpg(pdf_path, extracted_image_session_folder, session_id, zoom=2) ## ocr and analyzing
                    index += 1
                    progress[session_id]['current'] = index
                    maidrefcode_list.append(maid_ref_code)
                    
                try:
                    # maidrefcode_list = ['SRANML240075','CML','AA']
                    # maidrefcode_list = ['CP760722', 'EI990522', 'aaa','bbb']
                    print(f"maid-ref-code-list: {maidrefcode_list}")
                    print(f"image-path-with-face-path: {image_with_face_list}")
                    print(f"new-pdf-list-path: {new_pdf_list}")

                #     # rename_files(image_fullpath_with_face_list, maidrefcode_list) ## renaming extracted images
                    rename_files(image_with_face_list, maidrefcode_list) ## renaming extracted images
                    rename_files2(new_pdf_list, maidrefcode_list) ## renaming input pdf
                    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                    save_log(os.path.join(session_folder, "logs.txt"),f"Processed Completed. Ready to download!")
                
                except Exception as e:
                    print(f"An error occured: {e}")
                    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                    save_log(os.path.join(session_folder, "logs.txt"),f"An error occured during renaming process: {e}")
                
                print(f"Processing document finished with session ID {session_id}")
                update_query_storage_status(session_id,"download")
                
            except Exception as e:
                print(f"Error during upload processing: {e}")
                session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                save_log(os.path.join(session_folder, "logs.txt"),f"An error occured during renaming process: {e}")
                update_query_storage_status(session_id,"failed")

        # Print this when the background task is done
        print(f"Process exited for session ID: {session_id}")

        end_time = time.time()  # Record the end time
        duration = end_time - start_time  # Calculate the duration

        formatted_duration = format_duration(duration)
        print(f"Processing duration for session ID {session_id}: {formatted_duration}")
        update_query_storage_uptime(session_id, formatted_duration)
        rate = round(duration / total_files, 2) if total_files > 0 else 0
        update_query_storage_rate(session_id, str(rate))

    try:
        # Start the mock processing in a separate thread
        thread = threading.Thread(target=mock_processing, args=(session_id,))
        thread.daemon = True  # Ensure thread exits when the main program exits
        thread.start()

        # Wait for the thread to finish and print "process exited" once it does
        # thread.join()
        print(f"Process exited for session ID: {session_id}")
        # update_query_storage_status(session_id,"download")
        
    except Exception as e:
        print(f"Error during thread start: {e}")
        update_query_storage_status(session_id,"failed")

    return jsonify({'message': 'Processing started'}), 200


def run_process_files(session_id):
    # session_id = request.args.get('sessionId')

    # global image_fullpath_with_face_list, uploaded_pdf_file_list, uploaded_file_list, new_uploaded_pdf_file_path_list
    global uploaded_pdf_file_list, uploaded_file_list, new_uploaded_pdf_file_path_list, maid_status_global


    def mock_processing(session_id):
        maid_status_id_value = get_maid_status(session_id)
        maid_status_global = maid_status_id_value
        print(f"maid status set value: {maid_status_id_value}")

        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        save_log(os.path.join(session_folder, "logs.txt"),f"maid status set value: {maid_status_id_value}")
        

        start_time = time.time()  # Record the start time
        total_files = ""
        with app.app_context(): ## By pushing the application context manually, you ensure that Flask has the necessary context to handle things like query_storage without running into the "Working outside of application context" error.
            print(f"INFO: Processing started for session: {session_id}")
            new_pdf_list = []
            maidrefcode_list = []
            try:
                session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                uploaded_files = os.listdir(session_folder)
                # print(uploaded_files)
                total_files = len(uploaded_files)
                update_query_storage_num_files(session_id, f"{total_files} files")
                progress[session_id]['total'] = total_files
                print(f"Total files in the uploads is {total_files} with session ID {session_id}")


                session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                save_log(os.path.join(session_folder, "logs.txt"),f"Uploaded file list: {str(uploaded_file_list)}")
                

                # for index, filename in enumerate(uploaded_files):
                index = 0
                for i in range (len(uploaded_file_list)):
                    file_path = uploaded_file_list[i]
                    filename = os.path.basename(file_path)
                    file_ext = os.path.splitext(filename)[1].lower()

                    ### pdf conversion
                    try:

                        # Check the file extension and convert if necessary
                        if file_ext in ['.doc', '.docx']:
                            # pdf_path = replace_extension_with_pdf(app.config['UPLOAD_FOLDER'], filename)
                            session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                            converted_pdf_path = convert_doctypes_to_pdf(file_path, session_folder, session_id)
                            if converted_pdf_path:
                                print (f"Success converting a file")
                                filename = os.path.basename(converted_pdf_path)
                                session_folder = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
                                new_file_path = copy_file(converted_pdf_path, session_folder)
                                new_pdf_list.append(new_file_path)
                                
                            else:
                                print (f"Error converting a file")
                        else:
                            # For PDF files or unsupported formats, use the original path
                            session_folder = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
                            new_file_path = copy_file(file_path, session_folder)
                            new_pdf_list.append(new_file_path)
    
                    except Exception as e:
                        print (f"Error has occurred during documents to pdf conversion {e}")

                    # Simulate processing of each file
                    # time.sleep(1)  # Simulate processing delay
                    # time.sleep(30)  # Simulate processing delay

                    image_with_face_list = process_pdf_extract_image(filename, session_id) ## extract the profile picture and
                    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                    pdf_path = os.path.join(session_folder, filename)
                    extracted_image_session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                    page_images, maid_ref_code = pdf_to_jpg(pdf_path, extracted_image_session_folder, session_id, zoom=2) ## ocr and analyzing
                    index += 1
                    progress[session_id]['current'] = index
                    maidrefcode_list.append(maid_ref_code)
                    
                try:
                    # maidrefcode_list = ['SRANML240075','CML','AA']
                    # maidrefcode_list = ['CP760722', 'EI990522', 'aaa','bbb']
                    print(f"maid-ref-code-list: {maidrefcode_list}")
                    print(f"image-path-with-face-path: {image_with_face_list}")
                    print(f"new-pdf-list-path: {new_pdf_list}")

                #     # rename_files(image_fullpath_with_face_list, maidrefcode_list) ## renaming extracted images
                    rename_files(image_with_face_list, maidrefcode_list) ## renaming extracted images
                    rename_files2(new_pdf_list, maidrefcode_list) ## renaming input pdf
                    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                    save_log(os.path.join(session_folder, "logs.txt"),f"Processed Completed. Ready to download!")
                
                except Exception as e:
                    print(f"An error occured: {e}")
                    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                    save_log(os.path.join(session_folder, "logs.txt"),f"An error occured during renaming process: {e}")
                
                print(f"Processing document finished with session ID {session_id}")
                update_query_storage_status(session_id,"download")
                
            except Exception as e:
                print(f"Error during upload processing: {e}")
                session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
                save_log(os.path.join(session_folder, "logs.txt"),f"An error occured during renaming process: {e}")
                update_query_storage_status(session_id,"failed")

        # Print this when the background task is done
        print(f"Process exited for session ID: {session_id}")

        end_time = time.time()  # Record the end time
        duration = end_time - start_time  # Calculate the duration

        formatted_duration = format_duration(duration)
        print(f"Processing duration for session ID {session_id}: {formatted_duration}")
        update_query_storage_uptime(session_id, formatted_duration)
        rate = round(duration / total_files, 2) if total_files > 0 else 0
        update_query_storage_rate(session_id, str(rate))

    try:
        # Start the mock processing in a separate thread
        thread = threading.Thread(target=mock_processing, args=(session_id,))
        thread.daemon = True  # Ensure thread exits when the main program exits
        thread.start()

        # Wait for the thread to finish and print "process exited" once it does
        # thread.join()
        print(f"Process exited for session ID: {session_id}")
        # update_query_storage_status(session_id,"download")
        
    except Exception as e:
        print(f"Error during thread start: {e}")
        update_query_storage_status(session_id,"failed")


@app.route('/api/ocr-file-upload/<session_id>', methods=['POST'])
@login_required
def upload_ocrfile(session_id):

    progress[session_id] = {'current': 0, 'total': 1}  # Initialize progress

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file.'}), 400

    filename = file.filename
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    file_path = os.path.join(session_folder, filename)

    # Normalize the file path (this ensures that it works on both Windows and Linux)
    filepath = os.path.normpath(file_path)
    
    # Get the directory from the file path
    directory = os.path.dirname(filepath)
    
    # Create the directory and any necessary subdirectories if they don't exist
    if not os.path.exists(directory):
        os.makedirs(directory)

    if file and file.filename.endswith('.txt'):
        file.save(file_path)
        response = {
            'success': True,
            'message': 'File successfully uploaded.',
            'session_id': session_id
        }
        return jsonify(response), 200  
    else:
        return jsonify({'success': False, 'message': 'Invalid file type. Only .txt files are allowed.'}), 400



@app.route('/api/progress/<session_id>')
def progress_status(session_id):
    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    if session_id in progress:
        return jsonify(progress[session_id]), 200
    else:
        return jsonify({'error': 'Invalid session ID'}), 400

@app.route('/api/file-upload/<session_id>', methods=['POST'])
def upload_files(session_id):

    global last_upload_time, uploaded_pdf_file_list, uploaded_file_list, new_uploaded_pdf_file_path_list

    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401

    print(f"Session ID: {session_id}")  # Log the session ID
    # progress[session_id] = {'current': 0, 'total': len(files)}  # Initialize progres

    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)  # Create session-specific folder

    if 'files[]' not in request.files:
        print("No file part")
        return jsonify({'error': 'No file part', 'session_id': session_id}), 400

    files = request.files.getlist('files[]')
    if not files or all(file.filename == '' for file in files):
        print("No selected files")
        return jsonify({'error': 'No selected files', 'session_id': session_id}), 400

   
    total_files = len(files)  # Total files to be uploaded

    last_upload_time = datetime.now()
    uploaded_files = []
    uploaded_file_list = []
    uploaded_pdf_file_list = []
    new_uploaded_pdf_file_path_list = []

    progress[session_id] = {'current': 0, 'total': len(files)}  # Initialize progress

    # For each file uploaded, save it and then notify Laravel app asynchronously
    for index, file in enumerate(files):
        print(f"Uploading: {file.filename}")  # Log the file names
        file_path = os.path.join(session_folder, file.filename)
        file.save(file_path)
        uploaded_files.append(file.filename)
        uploaded_file_list.append(file_path)

    
    return jsonify({
        'message': 'Files uploaded successfully',
        'session_id': session_id,
        'uploaded_files': uploaded_files,
        'total_files': total_files
    }), 200

# curl -X DELETE http://localhost:5000/api/delete_progress/dc44d630-7fa4-41d8-a156-24243d250bba
# curl -X DELETE http://localhost:5000/api/delete_progress/

@app.route('/api/delete_progress/<session_id>', methods=['DELETE'])
def delete_progress(session_id):
    # Check if the session_id exists directly in the progress dictionary
    if session_id in progress:
        # Delete the entry for the session_id
        del progress[session_id]
        return jsonify({"message": f"Progress for session {session_id} deleted successfully"}), 200
    else:
        return jsonify({"error": f"Session {session_id} not found"}), 404


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


# @app.route('/api/download/<session_id>', methods=['GET'])
# def download_file(session_id):
#     try:
#         # Construct the zip file name and path using OUTPUT_FOLDER
#         zip_filename = f"{session_id}.zip"
#         zip_filepath = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id, zip_filename)
#         print(zip_filepath)
#         # Check if the zip file exists
#         if not os.path.exists(zip_filepath):
#             return jsonify({'error': 'File not found'}), 404

#         # Send the file for download using send_file
#         return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)

#     except Exception as e:
#         print(f"Error during download_file: {e}")
#         return jsonify({'error': 'An error occurred while trying to download the file.'}), 500


@app.route('/api/download/<session_id>')
@login_required
def download_zip_files(session_id):
    try:
        if not check_authenticated():
            return jsonify({'error': 'Unauthorized access'}), 401
        if session_id not in progress or progress[session_id]['current'] < progress[session_id]['total']:
            return jsonify({'error': 'Files are still being processed or invalid session ID'}), 400


        zip_filename = f"{session_id}.zip"
        session_folder = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
        zip_filepath = os.path.join(session_folder, zip_filename)
        print(f"zip path: {zip_filepath}")

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, dirs, files in os.walk(session_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Exclude the zip file itself from being added
                    if file_path != zip_filepath:
                        arcname = os.path.relpath(file_path, session_folder)
                        zipf.write(file_path, arcname)

        return send_file(zip_filepath, as_attachment=True)
    except Exception as e:
        print(f"Error during download_files: {e}")

@app.route('/api/download-csv/<session_id>')
@login_required
def download_output_csv(session_id):
    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    
    session_folder = os.path.join(app.config['GENERATE_CSV_FOLDER'], session_id)
    csv_filepath = os.path.join(session_folder, f'{session_id}.csv')

    if os.path.exists(csv_filepath):
        return send_file(csv_filepath, as_attachment=True)
    else:
        return jsonify({'error': 'output.csv not found'}), 404


@app.route('/api/download-gpt/<session_id>')
def download_gpt(session_id):
    # Replace with actual path to summary_text_from_gpt.txt
    # filepath = 'output_pdf2images/summary_text_from_gpt.txt'
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    filepath = os.path.join(session_folder, f'{session_id}-summary.txt')
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'})

@app.route('/api/download-ocr/<session_id>')
def download_ocr(session_id):
    # Replace with actual path to ocr_results.txt
    # filepath = f'output_pdf2images/OCR-{session_id}.txt'

    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    filepath = os.path.join(session_folder, f'{session_id}-OCR.txt')

    # filepath = f'output_pdf2images/OCR.txt'
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'})


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


@app.route('/api/clear-multiple-folders', methods=['GET'])
def clear_multiple_folders():
    folders_to_clear = [
        'output_csv',
        'output_extracted_page_image',
        'output_extracted_profile_image',
        'uploads'
    ]

    try:
        for folder in folders_to_clear:
            # Ensure the folder exists
            if not os.path.exists(folder):
                return jsonify({'error': f'Folder {folder} not found', 'timestamp': datetime.utcnow().isoformat()}), 404

            # Walk through the folder and delete all files and subdirectories
            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)  # Remove the file
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    shutil.rmtree(dir_path)  # Remove the directory

            # # Optionally, remove the folder itself if it is empty
            # if not os.listdir(folder):
            #     os.rmdir(folder)  # Remove the folder if it's empty

        return jsonify({
            'message': 'All specified folders and their contents cleared successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        print(f"Error while clearing multiple folders: {e}")
        return jsonify({
            'error': 'An error occurred while clearing the specified folders.',
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# Route to fetch logs content
@app.route('/api/fetch-logs/<session_id>')
def fetch_logs(session_id):
    # Logic to read and return logs.txt content
    try:
        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        log_file_path = f'{session_folder}/logs.txt'  # Use f-string for proper interpolation
        
        with open(log_file_path, 'r') as file:
            logs_content = file.read()
        
        return logs_content
    except Exception as e:
        # Return error message and HTTP status code 500 for server error
        return "Waiting for the log file to be available", 500


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

        delete_progress(session_id)

        if not session_id:
            return jsonify({'error': 'sessionId parameter is required'}), 400

        # Define the path to the session's upload folder and output folder
        upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        output_folder = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        output_extracted_page_image = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        output_extracted_profile_image = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], session_id)
        output_csv = os.path.join(app.config['GENERATE_CSV_FOLDER'], session_id)

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

        # Delete output_extracted_page_image files if the folder exists
        if os.path.exists(output_extracted_page_image):
            for root, dirs, files in os.walk(output_extracted_page_image, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)  # Remove the file
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    shutil.rmtree(dir_path)  # Remove the directory
            shutil.rmtree(output_extracted_page_image)  # Remove the session folder

        # Delete output_extracted_profile_image files if the folder exists
        if os.path.exists(output_extracted_profile_image):
            for root, dirs, files in os.walk(output_extracted_profile_image, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)  # Remove the file
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    shutil.rmtree(dir_path)  # Remove the directory
            shutil.rmtree(output_extracted_profile_image)  # Remove the session folder

        # Delete output_csv files if the folder exists
        if os.path.exists(output_csv):
            for root, dirs, files in os.walk(output_csv, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    os.remove(file_path)  # Remove the file
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    shutil.rmtree(dir_path)  # Remove the directory
            shutil.rmtree(output_csv)  # Remove the session folder

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

@app.route('/api/query-storage', methods=['GET'])
@login_required
def get_query_storage():
    return jsonify(query_storage)

@app.route('/api/add-query-to-query-storage', methods=['GET'])
def add_query_to_query_storage():
    # Get query parameters from the URL
    query_label = request.args.get('query')  # Get 'query' parameter
    query_id = request.args.get('sessionId')  # Get 'sessionId' parameter
    maid_status_id = request.args.get('maidStatus')  # Get 'maidStatus' parameter
    
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
            'rate': '0',  # Placeholder for rate, can be updated later
            'maid_status_id': maid_status_id
        }
        
        # Add the new query to query_storage
        query_storage.append(new_query)
        
        return jsonify({"message": "Query added successfully", "data": new_query}), 200
    else:
        return jsonify({"error": "Missing required parameters (sessionId, query)"}), 400


# http://127.0.0.1:5000/api/update_status?query_id=12345&status=inprogress
# http://127.0.0.1:5000/api/update_status?query_id=12345&status=inprogress
@app.route('/api/update_status', methods=['GET'])
def update_status():
    query_id = request.args.get('query_id')
    new_status = request.args.get('status')

    # Validate status input
    if new_status not in ['waiting', 'download', 'inprogress', 'failed']:
        return jsonify({"error": "Invalid status value"}), 400

    # Find the query by query_id and update its status
    for query in query_storage:
        if query['query_id'] == query_id:
            query['status'] = new_status
            return jsonify({"message": "Status updated successfully", "query": query}), 200

    # If query_id not found
    return jsonify({"error": "Query ID not found"}), 404


@app.route('/api/report-logs')
@login_required
def report_logs():
    # Get the session_id from the query string
    session_id = request.args.get('sessionId')

    if not session_id:
        # Handle case where sessionId is not provided
        return jsonify({"message": "Session ID is missing"}), 400

    if not check_authenticated():
        return redirect(url_for('login'))

    # Fetch the logs from the corresponding session folder
    try:
        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        log_file_path = f'{session_folder}/logs.txt'
        
        if not os.path.exists(log_file_path):
            return jsonify({"message": "Logs file not found"}), 404

        with open(log_file_path, 'r') as file:
            logs_content = file.read()

        return jsonify({
            "message": "Logs fetched successfully",
            "sessionId": session_id,
            "logs": logs_content
        }), 200

    except Exception as e:
        return jsonify({"error": "Error while fetching logs", "details": str(e)}), 500
        

# http://127.0.0.1:5000/add_query?query_label=Query%205&query_id=55555&status=waiting&up_time=15%20minutes&num_files=8%20files&rate=60%20KB/s
# http://127.0.0.1:5000/add_query?query_label=Query5&query_id=55555&status=waiting&up_time=15%20minutes&num_files=8%20files&rate=60%20KB/s

@app.route('/api/test-add-query', methods=['GET'])
def test_add_query():
    query_label = request.args.get('query_label')
    query_id = request.args.get('query_id')
    status = request.args.get('status')
    up_time = request.args.get('up_time')
    num_files = request.args.get('num_files')
    rate = request.args.get('rate')

    # Check if all required parameters are present
    if not all([query_label, query_id, status, up_time, num_files, rate]):
        return jsonify({"error": "Missing required parameters"}), 400

    # Create new query item and add it to the storage
    new_query = {
        "query_label": query_label,
        "query_id": query_id,
        "status": status,
        "up_time": up_time,
        "num_files": num_files,
        "rate": rate
    }
    query_storage.append(new_query)

    return jsonify({"message": "Query added successfully", "new_query": new_query}), 200

# http://127.0.0.1:5000/api/test_update_status?query_label=Query%202&query_id=67890&status=download
# http://127.0.0.1:5000/api/test_update_status?query_label=Query2&query_id=67890&status=download

@app.route('/api/test-update-status', methods=['GET'])
def test_update_status():
    query_label = request.args.get('query_label')
    query_id = request.args.get('query_id')
    new_status = request.args.get('status')

    # Validate input parameters
    if not all([query_label, query_id, new_status]):
        return jsonify({"error": "Missing required parameters"}), 400

    # Find the query based on query_label and query_id
    for item in query_storage:
        if item["query_label"] == query_label and item["query_id"] == query_id:
            # Update the status
            item["status"] = new_status
            return jsonify({"message": f"Status updated for {query_label} ({query_id})", "updated_query": item}), 200

    # If no matching query is found
    return jsonify({"error": "Query not found"}), 404

# http://127.0.0.1:5000/api/test_get_queries

@app.route('/api/test-get-queries', methods=['GET'])
def test_get_queries():
    return jsonify({"query_storage": query_storage}), 200


@app.route('/api/test-get-progress', methods=['GET'])
def test_get_progress():
    # return jsonify({"progress": progress}), 200
    return progress
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

# ## processing status page
# @app.route('/process/<session_id>')
# @login_required
# def processing_page(session_id):
#     # Get the session_id from the query string
#     # session_id = request.args.get('sessionId')

#     if not session_id:
#         # Handle case where sessionId is not provided
#         return "Session ID is missing", 400

#     if not check_authenticated():
#         return redirect(url_for('login'))

#     return render_template('process/process-page.html', session_id=session_id, backendurl=BACKEND_API_URL)


@login_required
@app.route('/report')
def failed_page():
    # Extract sessionId from URL query parameters
    session_id = request.args.get('sessionId')

    # Check if sessionId is provided
    if not session_id:
        return "Session ID is required!", 400
    
    return render_template('report/report-page.html', session_id=session_id, backendurl=BACKEND_API_URL)



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


@app.route('/extract')
@login_required
def extract_page():
    session_id = request.args.get('sessionId') 
    if not check_authenticated():
        return redirect(url_for('login'))
    return render_template('extract/extract-page.html', session_id=session_id, backendurl=BACKEND_API_URL)


@app.route('/api/extracting/<session_id>', methods=['POST'])
def extracting_status(session_id):
    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    if session_id in progress:
        return jsonify(progress[session_id]), 200
    else:
        return jsonify({'error': 'Invalid session ID'}), 400


@app.route('/api/extraction/<session_id>', methods=['POST'])
@login_required
def extract_ocrfile(session_id):
    global last_upload_time, maid_status_global

    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401

    def mock_ocr_processing(session_id):
        try:
            print("documents extraction process started")
            total_detected_documents = 0
            extracted_content = []

            try:
                # Construct the full file path
                # full_path = os.path.join(os.getcwd(), DOWNLOAD_OCR_FILE_PATH)
                # print(full_path)

                session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                os.makedirs(session_folder, exist_ok=True)  # Create session-specific folder

                files = os.listdir(session_folder)
                # Filter out files that end with '.txt'
                txt_files = [f for f in files if f.endswith('.txt')]

                # Check if there are any .txt files
                if not txt_files:
                    print(f"No .txt files found in the {app.config['UPLOAD_FOLDER']} directory.")
                    return jsonify({'message': 'No .txt files found in the directory.'}), 200
                
                # Sort files (optional: you can customize sorting if needed)
                txt_files.sort()
                
                # Take the first file
                first_txt_file = txt_files[0]
                session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
                full_path = os.path.join(session_folder, first_txt_file)

                # Check if file exists
                if not os.path.isfile(full_path):
                    print("Download OCR.txt is not found")

                else:
                    # Open and read the file
                    try:
                        with open(full_path, 'r', encoding='utf-8') as file:
                            file_content = file.read()
                    except UnicodeDecodeError:
                        # If utf-8 fails, try a different encoding
                        with open(full_path, 'r', encoding='latin-1') as file:
                            file_content = file.read()

                    # Extract data from the file content
                    extracted_data = extract_data_from_text(file_content)

                    # Print the result
                    for item in extracted_data:
                        # print(item)
                        extracted_content.append(item)

                    total_detected_documents = len(extracted_content)
                    print(f"documents found: {total_detected_documents}")
                  
            except Exception as e:
                print(f"Error during download OCR read: {e}")

              
            progress[session_id]['total'] = total_detected_documents

            # for index, filename in enumerate(uploaded_files):
            index = 0
            for i in range (total_detected_documents):
  
                # Simulate processing of each file
                # time.sleep(3)  # Simulate processing delay

                # Update the last_upload_time
                last_upload_time = datetime.now()

                # print(extracted_content[i][1])
                session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)

                summary_generation(extracted_content[i][1], session_folder, extracted_content[i][0], session_id) ## summary_generation(total_summary, output_folder, base_name)

                index += 1
                progress[session_id]['current'] = index
                
            print("documents extraction process finished")
        except Exception as e:
            print(f"Error during upload processing: {e}")

    if session_id not in progress:
        return jsonify({'error': 'Invalid session ID'}), 400
    
    try:
        # Start the mock processing in a separate thread
        thread = threading.Thread(target=mock_ocr_processing, args=(session_id,))
        thread.daemon = True  # Ensure thread exits when the main program exits
        thread.start()
    except Exception as e:
        print(f"Error during thread start: {e}")

    return jsonify({'message': 'Processing started'}), 200

@app.route('/api/status')
@login_required
def status_page():
    session_id = request.args.get('sessionId')
    print(f"status page: {session_id}")
    if not check_authenticated():
        return redirect(url_for('login'))
    return render_template('process/process-page.html', session_id=session_id, backendurl=BACKEND_API_URL)

# Run the checking in a separate thread when the Flask app starts
# @app.before_first_request
if __name__ == '__main__':
    thread = threading.Thread(target=check_queries)
    thread.daemon = True  # Ensure thread exits when the main program exits
    thread.start()
    app.run(debug=True)
