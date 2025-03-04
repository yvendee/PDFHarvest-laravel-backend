from flask import Flask
import cv2
import pytesseract
import os
from log_functions.utils.utils import save_log


app = Flask(__name__)
app.config['EXTRACTED_PAGE_IMAGES_FOLDER'] = 'output_extracted_page_image/'


# Uncomment and modify the following line if you're running on Windows
# pytesseract.pytesseract.tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(filepath):
    try:
        img = cv2.imread(filepath)
        
        if img is None:
            raise Exception("Error: Could not read the image.")

        img = cv2.resize(img, (1050, 1680))
        
        text = pytesseract.image_to_string(img)

        img = cv2.resize(img, (1366, 1366))
        
        text2 = pytesseract.image_to_string(img)

        text = text2 + '\n'

        # Remove trailing and unwanted characters, allow whitespace and newlines
        # text = text.strip()  # Remove leading and trailing whitespace
        # text = text.replace("\n", " ")  # Replace newline characters with a space
        
        # Get the basename of the file
        filename = os.path.basename(filepath)
        
        # Log success with filename included
        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        save_log(os.path.join(session_folder, "logs.txt"),f"[Success] Extract Text from {filename}")
        
        return text
    
    except Exception as e:
        print(f"Error: {e}")
        session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
        save_log(os.path.join(session_folder, "logs.txt"),f"Error during tesseract image read: {e}")
        
        return None


