from functools import wraps
from flask import Flask, request, Blueprint, render_template, jsonify, session, redirect, url_for, send_file

import sys
import os
import time
from threading import Thread
import zipfile
import shutil
import re
import random
from datetime import datetime

# import os
import io
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
from flask_cors import CORS
from openai_api.utils.utils import ( get_summary_from_image, get_summary_from_text, get_summary_from_text_gpt4o, get_summary_from_text_test, get_summary_from_text_gpt4omini, get_summary_from_image_gpt4omini)
from anthropic_api.utils.utils import ( get_summary_from_image_using_claude )

from custom_prompt.utils.utils import read_custom_prompt
from csv_functions.utils.utils import save_csv
from log_functions.utils.utils import save_log
from tesseract.utils.utils import extract_text_from_image
import subprocess

# Build app
app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)
# CORS(app, supports_credentials=True)  # Enable CORS for all routes
app.secret_key = 'your_secret_key'  # Needed for session management

last_upload_time = None

# Hardcoded username and password (for demo purposes)
USERNAME = "searchmaid"
PASSWORD = "maidasia"

# Global variable to store current OCR setting
current_ocr = "gpt4ominiOCR"

# Global variable to store structured text setting
# current_structured_text = "gpt4omini"
current_structured_text = "gpt4omini"
maid_status_global = "None"

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

# Ensure the 'uploads' directory exists
UPLOAD_FOLDER = 'uploads'
EXTRACTED_PROFILE_PICTURE_FOLDER = 'extracted_images'
EXTRACTED_PAGE_IMAGES_FOLDER = 'output_pdf2images'
GENERATE_CSV_FOLDER = 'output_csv'
DOWNLOAD_OCR_FILE_PATH = 'uploads/OCR.txt'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_PROFILE_PICTURE_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_PAGE_IMAGES_FOLDER, exist_ok=True)
os.makedirs(GENERATE_CSV_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'] = EXTRACTED_PROFILE_PICTURE_FOLDER
app.config['EXTRACTED_PAGE_IMAGES_FOLDER'] = EXTRACTED_PAGE_IMAGES_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
# Set maximum file size to 50 MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Define the path to the directory where the file is located
FILE_DIRECTORY = os.path.dirname(__file__)

progress = {}
image_fullpath_with_face_list = []
uploaded_pdf_file_list = []
uploaded_file_list = []
new_uploaded_pdf_file_path_list = []


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

def convert_doctypes_to_pdf(doc_file, pdf_dir):
    global EXTRACTED_PAGE_IMAGES_FOLDER
    try:
        # Use the subprocess module to run the soffice command for conversion
        process = subprocess.Popen(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', pdf_dir, doc_file])
        save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"PDF Conversion started!")

        # Wait for the conversion to complete
        while process.poll() is None:
            time.sleep(1)  # Sleep for 1 second
        
        # Check if the conversion was successful
        if process.returncode == 0:
            pdf_path = os.path.join(pdf_dir, f"{os.path.splitext(os.path.basename(doc_file))[0]}.pdf")
            print(f"Conversion complete. PDF saved to {pdf_path}")
            save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"Conversion complete. PDF saved to {pdf_path}")
            return pdf_path
        else:
            save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"PDF Conversion failed.")
            print("Conversion failed.")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"Error during PDF conversion start: {str(e)}")
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
            save_log(os.path.join(output_folder, "logs.txt"),f"word count: {word_count} , gpt3.5 words limit is 3000")
            
            # Check word count and print appropriate message
            if word_count <= 2900:
                print("Sending text to OpenAI  GPT3.5...")
                save_log(os.path.join(output_folder, "logs.txt"),"Sending text to OpenAI GPT3.5...")
                summary_text = get_summary_from_text(total_summary) ## summary text from gpt3.5
            else:
                save_log(os.path.join(output_folder, "logs.txt"),"Words limit exceeds..switching to GPT4o")
                save_log(os.path.join(output_folder, "logs.txt"),"Sending text to OpenAI GPT4o...")
                summary_text = get_summary_from_text_gpt4o(total_summary) ## summary text from gpt4o
        else:  ## gpt4omini

            # Count words in the input string
            word_count = count_words(total_summary)

            print("Sending text to OpenAI  GPT4omini...")
            save_log(os.path.join(output_folder, "logs.txt"),"Sending text to OpenAI GPT4omini...")
            summary_text = get_summary_from_text_gpt4omini(total_summary) ## summary text from gpt4omini

        ## test
        # summary_text = get_summary_from_text_test(total_summary)

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

        save_log(os.path.join(output_folder, "logs.txt"),f"Appending data to output.csv")
        csv_path = f'output_csv/output-{session_id}.csv'
        save_csv(csv_path, matches_list, values_array)

    with open(os.path.join(output_folder, "summary_text_from_gpt.txt"), "a", encoding="utf-8") as text_file:
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

    save_log(os.path.join(output_folder, "logs.txt"),f"Opening pdf file: {pdf_file}")
    
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

        save_log(os.path.join(output_folder, "logs.txt"),f"Page {page_num + 1} of {pdf_file} extracted")

        save_log(os.path.join(output_folder, "logs.txt"),f"Current OCR used is {current_ocr}")

        if current_ocr == 'gpt4oOCR':
            summary = get_summary_from_image(image_filename) ## summary text from gpt4o OCR
        elif current_ocr == 'tesseractOCR':
            summary = extract_text_from_image(image_filename) ## extracted text from local tesseract OCR
        elif current_ocr == 'claudeOCR':
            summary = get_summary_from_image_using_claude(image_filename) ## summary text from claude Haiku OCR
        elif current_ocr == 'gpt4ominiOCR':
            summary = get_summary_from_image_gpt4omini(image_filename) ## summary text from gpt4omini OCR
        else:
            summary = get_summary_from_image_gpt4omini(image_filename) ## summary text from gpt4omini OCR

        # summary = "test"
        total_summary += summary + "\n"  # Add newline between summaries
    
    # Close the PDF file
    pdf_document.close()

    results_from_ocr, maid_ref_code = summary_generation(total_summary, output_folder, base_name, session_id)
    # maid_ref_code = "maid_ref_code_test"
    # results_from_ocr = "test"

    # Print the list of page image filenames
    # print(f"List of page images for {pdf_file}: {page_images}")

    ## Write total_summary
    with open(os.path.join(output_folder, f"OCR-{session_id}.txt"), "a", encoding="utf-8") as text_file:
    # with open(os.path.join(output_folder, f"OCR.txt"), "a", encoding="utf-8") as text_file:
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
def extract_images_with_faces(pdf_path):
    global image_fullpath_with_face_list, face_cascade
    # Get the base name of the PDF file
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    # Create the main folder if it doesn't exist
    main_folder = "extracted_images"
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

# Load the pre-trained face detection classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Function to process a specific PDF file in the "uploads" folder
def process_pdf_extract_image(filename):
    global EXTRACTED_PAGE_IMAGES_FOLDER

    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(pdf_path) and pdf_path.endswith(".pdf"):
        extracted_images = extract_images_with_faces(pdf_path)
        # print(f"Processed {pdf_path}: {len(extracted_images)} images extracted with faces")
        # save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"Processed {pdf_path}: {len(extracted_images)} images extracted with faces")

    else:
        print(f"File '{filename}' not found or is not a PDF.")
        save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"File '{filename}' not found or is not a PDF.")

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

@app.route('/')
def index():

    # global last_upload_time
    # if last_upload_time:
    #     current_time = datetime.now()
    #     time_difference = current_time - last_upload_time
    #     minutes_difference = int(time_difference.total_seconds() / 60)

    #     if minutes_difference < 60:
    #         time_label = f"{minutes_difference} minutes ago"
    #     elif minutes_difference < 1440:
    #         hours_difference = int(minutes_difference / 60)
    #         time_label = f"{hours_difference} hour ago" if hours_difference == 1 else f"{hours_difference} hours ago"
    #     else:
    #         days_difference = int(minutes_difference / 1440)
    #         time_label = f"{days_difference} day ago" if days_difference == 1 else f"{days_difference} days ago"
    # else:
    #     time_label = "-"

    # return jsonify({"time_label": time_label, "status": "server is running"})

     return jsonify({"status": "server is running", "version": "0.1"})

@app.route('/home')
@login_required
def home_page():
    global image_fullpath_with_face_list, new_uploaded_pdf_file_path_list

    image_fullpath_with_face_list = []
    new_uploaded_pdf_file_path_list = []
    # uploaded_pdf_file_path_list = []

    if not check_authenticated():
        return redirect(url_for('login'))
    # Check if the 'uploads' folder exists before attempting to delete files
    if os.path.exists(UPLOAD_FOLDER):
        # Delete all files inside the 'uploads' folder
        for file_name in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        # Delete all files inside the 'extracted_images' folder
        for file_name in os.listdir(EXTRACTED_PROFILE_PICTURE_FOLDER):
            file_path = os.path.join(EXTRACTED_PROFILE_PICTURE_FOLDER, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        # Delete all files inside the 'output_pdf2images' folder
        for file_name in os.listdir(EXTRACTED_PAGE_IMAGES_FOLDER):
            file_path = os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        # Delete all files inside the 'output_csv' folder
        for file_name in os.listdir(GENERATE_CSV_FOLDER):
            file_path = os.path.join(GENERATE_CSV_FOLDER, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        return render_template('home/home-page.html')
    else:
        return render_template('home/home-page.html')  # Or redirect to another page if the folder doesn't exist


@app.route('/upload/<session_id>', methods=['POST'])
def upload_files(session_id):
    global last_upload_time, uploaded_pdf_file_list, uploaded_file_list, new_uploaded_pdf_file_path_list

    if 'files' not in request.files:
        return jsonify({'error': 'No files part in the request'}), 400
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected for uploading'}), 400


    uploaded_files = []
    uploaded_pdf_file_list = []
    uploaded_file_list = []
    new_uploaded_pdf_file_path_list = []


    for file in files:
        if file and file.filename:

            filename = file.filename
            # print(filename)
            file_ext = os.path.splitext(filename)[1].lower()
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save the original file
            file.save(file_path)
            uploaded_files.append(filename)
            uploaded_file_list.append(file_path)

    response = {
        'message': 'Files successfully uploaded',
        'status': 'success',
        'files': 'uploaded_files',
        'session_id': session_id
    }
    return jsonify(response), 200

@app.route('/upload2', methods=['POST'])
@login_required
def upload_ocrfile():

    session_id = str(os.urandom(16).hex())
    progress[session_id] = {'current': 0, 'total': 1}  # Initialize progress

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file.'}), 400

    if file and file.filename.endswith('.txt'):
        filename = file.filename
        file_path = os.path.join('uploads', filename)
        file.save(file_path)
        response = {
            'success': True,
            'message': 'File successfully uploaded.',
            'session_id': session_id
        }
        return jsonify(response), 200  
    else:
        return jsonify({'success': False, 'message': 'Invalid file type. Only .txt files are allowed.'}), 400


@app.route('/process/<session_id>', methods=['POST'])
@login_required
def process_files(session_id):
    global image_fullpath_with_face_list, uploaded_pdf_file_list, uploaded_file_list, new_uploaded_pdf_file_path_list

    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    def mock_processing():
        new_pdf_list = []
        maidrefcode_list = []
        try:

            print("uploading process started")
            uploaded_files = os.listdir(UPLOAD_FOLDER)
            # print(uploaded_files)
            total_files = len(uploaded_files)
            progress[session_id]['total'] = total_files
            print(f"total files in the uploads is {total_files}")

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
                        converted_pdf_path = convert_doctypes_to_pdf(file_path, app.config['UPLOAD_FOLDER'])
                        if converted_pdf_path:
                            print (f"Success converting a file")
                            filename = os.path.basename(converted_pdf_path)
                            new_file_path = copy_file(converted_pdf_path, EXTRACTED_PROFILE_PICTURE_FOLDER)
                            new_pdf_list.append(new_file_path)
                            
                        else:
                            print (f"Error converting a file")
                    else:
                        # For PDF files or unsupported formats, use the original path
                        new_file_path = copy_file(file_path, EXTRACTED_PROFILE_PICTURE_FOLDER)
                        new_pdf_list.append(new_file_path)
  
                except Exception as e:
                    print (f"Error has occurred during documents to pdf conversion {e}")

                # Simulate processing of each file
                # time.sleep(3)  # Simulate processing delay

                process_pdf_extract_image(filename)
                pdf_path = os.path.join(UPLOAD_FOLDER, filename)
                page_images, maid_ref_code = pdf_to_jpg(pdf_path, EXTRACTED_PAGE_IMAGES_FOLDER, session_id, zoom=2) ## ocr and analyzing
                index += 1
                progress[session_id]['current'] = index
                maidrefcode_list.append(maid_ref_code)
                
            try:
                # maidrefcode_list = ['SRANML240075','CML','AA']
                # maidrefcode_list = ['CP760722', 'EI990522', 'aaa']
                print(f"maid-ref-code-list: {maidrefcode_list}")
                print(f"image-path-with-face-path: {image_fullpath_with_face_list}")
                print(f"new-pdf-list-path: {new_pdf_list}")

                rename_files(image_fullpath_with_face_list, maidrefcode_list) ## renaming extracted images
                rename_files2(new_pdf_list, maidrefcode_list) ## renaming input pdf
                save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"Processed Completed. Ready to download!")
            
            except Exception as e:
                print(f"An error occured: {e}")
                save_log(os.path.join(EXTRACTED_PAGE_IMAGES_FOLDER, "logs.txt"),f"An error occured during renaming process: {e}")
            
            print("uploading process finished")
        except Exception as e:
            print(f"Error during upload processing: {e}")

    if session_id not in progress:
        return jsonify({'error': 'Invalid session ID'}), 400
    
    try:
        # Start the mock processing in a separate thread
        thread = Thread(target=mock_processing)
        thread.start()
    except Exception as e:
        print(f"Error during thread start: {e}")

    
    return jsonify({'message': 'Processing started'}), 200


@app.route('/extracting/<session_id>', methods=['POST'])
@login_required
def extract_ocrfile(session_id):
    global last_upload_time, maid_status_global

    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    def mock_processing():
        try:
            print("documents extraction process started")
            total_detected_documents = 0
            extracted_content = []

            try:
                # Construct the full file path
                # full_path = os.path.join(os.getcwd(), DOWNLOAD_OCR_FILE_PATH)
                # print(full_path)

                files = os.listdir(UPLOAD_FOLDER)
                # Filter out files that end with '.txt'
                txt_files = [f for f in files if f.endswith('.txt')]

                # Check if there are any .txt files
                if not txt_files:
                    print(f"No .txt files found in the {UPLOAD_FOLDER} directory.")
                    return jsonify({'message': 'No .txt files found in the directory.'}), 200
                
                # Sort files (optional: you can customize sorting if needed)
                txt_files.sort()
                
                # Take the first file
                first_txt_file = txt_files[0]
                full_path = os.path.join(UPLOAD_FOLDER, first_txt_file)

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

                summary_generation(extracted_content[i][1], EXTRACTED_PAGE_IMAGES_FOLDER, extracted_content[i][0], session_id) ## summary_generation(total_summary, output_folder, base_name)

                index += 1
                progress[session_id]['current'] = index
                
            print("documents extraction process finished")
        except Exception as e:
            print(f"Error during upload processing: {e}")

    if session_id not in progress:
        return jsonify({'error': 'Invalid session ID'}), 400
    
    try:
        # Start the mock processing in a separate thread
        thread = Thread(target=mock_processing)
        thread.start()
    except Exception as e:
        print(f"Error during thread start: {e}")

    return jsonify({'message': 'Processing started'}), 200


@app.route('/status')
@login_required
def status_page():
    if not check_authenticated():
        return redirect(url_for('login'))
    return render_template('status/status-page.html')

@app.route('/extract')
@login_required
def extract_page():
    if not check_authenticated():
        return redirect(url_for('login'))
    return render_template('extract/extract-page.html')

processing_threads = {}  # Initialize an empty dictionary to keep track of processing threads

@app.route('/progress/<session_id>')
def progress_status(session_id):
    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    if session_id in progress:
        return jsonify(progress[session_id]), 200
    else:
        return jsonify({'error': 'Invalid session ID'}), 400

@app.route('/extracting/<session_id>')
def extracting_status(session_id):
    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    if session_id in progress:
        return jsonify(progress[session_id]), 200
    else:
        return jsonify({'error': 'Invalid session ID'}), 400

@app.route('/cancel/<session_id>', methods=['POST'])
@login_required
def cancel_processing(session_id):
    try:
        if session_id in processing_threads:
            del processing_threads[session_id]  # Stop the processing
            print("process cancelled")
            # Additional cleanup if necessary
            return jsonify({'message': 'Processing cancelled'})
        return jsonify({'error': 'Invalid session ID'}), 400
    except Exception as e:
        print(f"Error during cancel processing: {e}")

@app.route('/cancel2/<session_id>', methods=['POST'])
@login_required
def cancel2_processing(session_id):
    try:
        if session_id in processing_threads:
            del processing_threads[session_id]  # Stop the processing
            print("process cancelled")
            # Additional cleanup if necessary
            return jsonify({'message': 'Processing cancelled'})
        return jsonify({'error': 'Invalid session ID'}), 400
    except Exception as e:
        print(f"Error during cancel processing: {e}")

@app.route('/download/<session_id>')
@login_required
def download_files(session_id):
    try:
        if not check_authenticated():
            return jsonify({'error': 'Unauthorized access'}), 401
        if session_id not in progress or progress[session_id]['current'] < progress[session_id]['total']:
            return jsonify({'error': 'Files are still being processed or invalid session ID'}), 400

        zip_filename = f"outputfiles_{session_id}.zip"
        zip_filepath = os.path.join(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'], zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, dirs, files in os.walk(app.config['EXTRACTED_PROFILE_PICTURE_FOLDER']):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Exclude the zip file itself from being added
                    if file_path != zip_filepath:
                        arcname = os.path.relpath(file_path, app.config['EXTRACTED_PROFILE_PICTURE_FOLDER'])
                        zipf.write(file_path, arcname)

        return send_file(zip_filepath, as_attachment=True)
    except Exception as e:
        print(f"Error during download_files: {e}")

@app.route('/download-csv/<session_id>')
@login_required
def download_csv(session_id):
    if not check_authenticated():
        return jsonify({'error': 'Unauthorized access'}), 401
    csv_filepath = f'output_csv/output-{session_id}.csv'

    if os.path.exists(csv_filepath):
        return send_file(csv_filepath, as_attachment=True)
    else:
        return jsonify({'error': 'output.csv not found'}), 404

@app.route('/custom-prompt', methods=['GET', 'POST'])
@login_required
def text_editor():
    if request.method == 'POST':
        # Handle form submission if needed
        pass

    custom_prompt_file = 'dynamic/txt/custom_prompt.txt'
    default_content = ''
    
    # Read the content of custom_prompt.txt if it exists
    if os.path.exists(custom_prompt_file):
        with open(custom_prompt_file, 'r', encoding='utf-8') as f:
            default_content = f.read()
    
    return render_template('custom/custom-prompt-page.html', default_content=default_content)


@app.route('/save-content', methods=['POST'])
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

@app.route('/download-template')
@login_required
def download_template():
    template_file = 'static/txt/custom_prompt_template.txt'
    return send_file(template_file, as_attachment=True)

@app.route('/settings')
@login_required  # Ensure only authenticated users can access settings
def settings_page():
    if not check_authenticated():
        return redirect(url_for('login'))
    return render_template('settings/settings-page.html')

# Endpoint to handle toggle OCR settings
@app.route('/toggle-ocr/<setting>', methods=['POST'])
@login_required
def toggle_ocr_setting(setting):
    global current_ocr  # Access the global variable
    
    if setting in ['gpt4omini','gpt4o', 'tesseract', 'claude']:
        # Set the current OCR setting based on the URL parameter
        if setting == 'gpt4omini':
            current_ocr = "gpt4ominiOCR"
        if setting == 'gpt4o':
            current_ocr = "gpt4oOCR"
        elif setting == 'tesseract':
            current_ocr = "tesseractOCR"
        elif setting == 'claude':
            current_ocr = "claudeOCR"
        
        # Print the current value of current_ocr
        print(f"Current OCR setting: {current_ocr}")

        return jsonify({'message': f'Successfully set {setting} OCR setting'}), 200
    else:
        return jsonify({'error': 'Invalid OCR setting'}), 400

# Route to retrieve current OCR setting
@app.route('/current-ocr', methods=['GET'])
def get_current_ocr():
    global current_ocr
    return jsonify({'current_ocr': current_ocr})

# Endpoint to handle toggle Structured Text settings
@app.route('/toggle-st/<setting>', methods=['POST'])
@login_required
def toggle_st_setting(setting):
    global current_structured_text  # Access the global variable
    
    if setting in ['gpt4omini', 'gpt35']:
        # Set the current Structured Text setting based on the URL parameter
        if setting == 'gpt4omini':
            current_structured_text = "gpt4omini"
        elif setting == 'gpt35':
            current_structured_text = "gpt35"
        
        # Print the current value of current_structured_text
        print(f"Current Structured Text setting: {current_structured_text}")

        return jsonify({'message': f'Successfully set {setting} Structured Text setting'}), 200
    else:
        return jsonify({'error': 'Invalid Structured Text setting'}), 400

# Route to retrieve current structured text setting
@app.route('/current-st', methods=['GET'])
def get_current_st():
    global current_structured_text
    return jsonify({'current_structured_text': current_structured_text})


@app.route('/download-gpt/<session_id>')
def download_gpt(session_id):
    # Replace with actual path to summary_text_from_gpt.txt
    filepath = 'output_pdf2images/summary_text_from_gpt.txt'
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'})

@app.route('/download-ocr/<session_id>')
def download_ocr(session_id):
    # Replace with actual path to ocr_results.txt
    filepath = f'output_pdf2images/OCR-{session_id}.txt'
    # filepath = f'output_pdf2images/OCR.txt'
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'})

# Route to fetch logs content
@app.route('/fetch-logs/<session_id>')
def fetch_logs(session_id):
    # Logic to read and return logs.txt content
    try:
        with open('output_pdf2images/logs.txt', 'r') as file:
            logs_content = file.read()
        return logs_content
    except Exception as e:
        # return str(e), 500  # Return error message and HTTP status code 500 for server error
        return "Waiting for the log file to be available", 500  # Return error message and HTTP status code 500 for server error


@app.route('/save-csv')
@login_required
def save_outputcsv():
    
    save_csv(csv_path,"hello word")
    return "success"

@app.route('/edit-default-options-value', methods=['POST'])
def edit_default_options_value():
    global maid_status_global
    maid_status_global = request.form.get('maid_status', 'None')
    print(f"maid type selected: {maid_status_global}")
    
    # Return JSON response
    return jsonify(success=True)


@app.route('/default-options')
def edit_default_options():
    return render_template('default/default-options-page.html', maid_status_global=maid_status_global)

@app.route('/download-logs')
def download_logs():
    # Define the path to the file to be downloaded
    filepath = os.path.join(os.path.dirname(__file__), 'ph.logs')

    # Check if the file exists
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        # Return a JSON response if the file is not found
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
    app.run(host='0.0.0.0', port=3000)
