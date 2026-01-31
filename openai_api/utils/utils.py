from flask import Flask
from openai import OpenAI
import base64
import json
import cv2
import numpy as np
import re
import os
from log_functions.utils.utils import save_log


app = Flask(__name__)
app.config['EXTRACTED_PAGE_IMAGES_FOLDER'] = 'output_extracted_page_image/'

def detect_face_gpt5nano(image_path):
    try:
        # Read and base64-encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Prepare the OpenAI payload
        image_payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }

        client = OpenAI()

        # Ask GPT5 Nano to answer yes/no only
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "text",
                            "text": "Answer strictly with 'yes' or 'no'."
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Is the image showing a human face? Respond only with 'yes' or 'no'."
                        },
                        image_payload
                    ]
                }
            ],
            max_tokens=3,
            temperature=0,
            response_format={
                "type": "text"
            }
        )

        answer = response.choices[0].message.content.strip().lower()

        if answer.startswith("y"):
            return "yes"
        else:
            return "no"

    except Exception as e:
        return f"Error: {e}"


def detect_face_gpt4omini(image_path):

    try:
        # Read and base64-encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Prepare the OpenAI payload
        image_payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }

        client = OpenAI()

        # Ask GPT only to answer yes/no
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Answer strictly with 'yes' or 'no'."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Is the image showing a human face? Respond only with 'yes' or 'no'."
                        },
                        image_payload
                    ]
                }
            ],
            max_tokens=3,
            temperature=0
        )

        # Extract the yes/no answer
        answer = response.choices[0].message.content.strip().lower()

        # Normalize the output
        if answer.startswith("y"):
            return "yes"
        else:
            return "no"

    except Exception as e:
        return f"Error: {e}"


def get_summary_from_text_test(summarized_string, session_id):
  # global LOGPATH
  try:

    summary = """
    [maid name]: ISABELLE ANGELES
    [maid ref code]: BNPH - 478
    [maid type]: Transfer Maid
    [maid expected salary]: 700
    [availability status]: Other
    [youtube link]: null
    [evalsg lang english stars]: 5
    [evalsg lang mandarin stars]: null
    [evalsg lang malay stars]: null
    [evalsg lang tamil stars]: null
    [evalsg lang hindi stars]: null
    [public maid introduction]: null
    [date of birth]: 16/09/1988
    [place of birth]: CATANAUN QUEZON
    [height cm]: 160
    [weight kg]: 63
    [nationality]: FILIPINO
    [sub nationality]: null
    [home address]: SAN ISIDRO CATANAUN QUEZON
    [home airport repatriate]: NAIA
    [home contact number]: 63
    [religion]: CATHOLIC
    [education]: High School (11-12 yrs)
    [siblings count]: 1
    [marital status]: Single
    [children count]: 2
    [children ages]: 15 AND 4 YEARS OLD
    [allergies]: SEAFOODS W SHELLS (SHE CAN EAT FISH)
    [illness mental]: No
    [illness epilepsy]: No
    [illness asthma]: No
    [illness diabetes]: No
    [illness hypertension]: No
    [illness tubercolosis]: No
    [illness heart disease]: No
    [illness malaria]: No
    [illness operations]: Yes
    [illness others]: N/A
    [physical disabilities]: NONE
    [dietary restrictions]: NONE
    [handle pork]: Yes
    [handle beef]: Yes
    [handle pets]: Yes
    [handle others]: SHE HAVE OPERATION IN HER HAND
    [maid preferred rest day]: EVERY SUNDAY rest day(s) per month.
    [maid other remarks]: WILLING TO ACCEPT PAID RESTDAY
    [eval no agency no trainingctr]: null
    [eval_agency]: Singapore EA
    [eval_agency_telephone]: null
    [eval_agency_videoconference]: Yes
    [eval_agency_in_person]: No
    [eval_agency_in_person_observation]: No
    [eval agency age range infant child]: null
    [eval agency willing infant child]: Yes
    [eval agency years infant child]: null
    [eval agency stars infant child]: 5
    [eval agency comments infant child]: SHE HAS EXPERIENCE IN LOOKING AFTER NEWBORN BABY IN SINGAPORE.
    [eval agency willing elderly]: Yes
    [eval agency years elderly]: null
    [eval agency stars elderly]: null
    [eval agency comments elderly]: NO EXPERIENCE
    [eval agency willing disabled]: Yes
    [eval agency years disabled]: null
    [eval agency stars disabled]: null
    [eval agency comments disabled]: null
    [eval agency willing housework]: Yes
    [eval agency years housework]: null
    [eval agency stars housework]: null
    [eval agency comments housework]: null
    [eval agency specify cuisines cooking]: CHINESE DISHES, WILLING TO LEARN MORE.
    [eval agency willing cooking]: Yes
    [eval agency years cooking]: null
    [eval agency stars cooking]: 4
    [eval agency comments cooking]: CHINESE DISHES, WILLING TO LEARN MORE.
    [eval agency language]: ENGLISH
    [eval agency willing language]: Yes
    [eval agency years language]: null
    [eval agency stars language]: null
    [eval agency comments language]: null
    [eval agency specify other skills]: null
    [eval agency willing other skills]: Yes
    [eval agency years other skills]: null
    [eval agency stars other skills]: null
    [eval agency comments other skills]: null
    [trainingctr name]: null
    [trainingctr certified]: null
    [eval trainingctr telephone]: null
    [eval trainingctr videoconference]: null
    [eval trainingctr in person]: null
    [eval trainingctr in person observation]: null
    [eval trainingctr age range infant child]: null
    [eval trainingctr willing infant child]: null
    [eval trainingctr years infant child]: null
    [eval trainingctr stars infant child]: null
    [eval trainingctr comments infant child]: null
    [eval trainingctr willing elderly]: null
    [eval trainingctr years elderly]: null
    [eval trainingctr stars elderly]: null
    [eval trainingctr comments elderly]: null
    [eval trainingctr willing disabled]: null
    [eval trainingctr years disabled]: null
    [eval trainingctr stars disabled]: null
    [eval trainingctr comments disabled]: null
    [eval trainingctr willing housework]: null
    [eval trainingctr years housework]: null
    [eval trainingctr stars housework]: null
    [eval trainingctr comments housework]: null
    [eval trainingctr specify cuisines cooking]: null
    [eval trainingctr willing cooking]: null
    [eval trainingctr years cooking]: null
    [eval trainingctr stars cooking]: null
    [eval trainingctr comments cooking]: null
    [eval trainingctr language]: null
    [eval trainingctr willing language]: null
    [eval trainingctr years language]: null
    [eval trainingctr stars language]: null
    [eval trainingctr comments language]: null
    [eval trainingctr specify other skills]: null
    [eval trainingctr willing other skills]: null
    [eval trainingctr years other skills]: null
    [eval trainingctr stars other skills]: null
    [eval trainingctr comments other skills]: null 
    [employment history]:
    - date: 10 NOV 2023 to 23 NOV 2024 
    - country: SINGAPORE 
    - employer: CHINESE 
    - work duties: {do all general household, cleaning, washing, ironing the clothes, wash the dishes, marketing, cooking, assist the nanny to look after the newborn}
    - remarks: {There are 3 people in the house consist Mam, Sir and newborn baby. HDB, 3 bedroom and 2 toilets. They have 2 helpers. baby need to change the diapers, make the milk, feeding, make a nap, playing and sing song for the baby.}
    - date: 25 JUN 2016 to 29 AUG 2018 
    - country: SINGAPORE 
    - employer: CHINESE 
    - work duties: {take care the kids need to prepare for school, sent / fetch to school bus, prepare for breakfast, food, remind to do homework and do all general household, cleaning, washing, ironing the clothes, marketing, wash the dishes and cooking}
    - remarks: {There are 3 people in the house consist Mam, Sir and 1 kids 10 years old. HDB, 2 bedroom and 2 toilets. She only helper in the house}
    [employer1_date_from]: 10 NOV 2023 
    [employer1_date_to]: 23 NOV 2024 
    [employer1_country]: SINGAPORE 
    [employer1_name]: CHINESE 
    [employer1_work_duties]: do all general household, cleaning, washing, ironing the clothes, wash the dishes, marketing, cooking, assist the nanny to look after the newborn 
    [employer1_remarks]: There are 3 people in the house consist Mam, Sir and newborn baby. HDB, 3 bedroom and 2 toilets. They have 2 helpers. baby need to change the diapers, make the milk, feeding, make a nap, playing and sing song for the baby.
    [employer2_date_from]: 25 JUN 2016 
    [employer2_date_to]: 29 AUG 2018 
    [employer2_country]: SINGAPORE 
    [employer2_name]: CHINESE 
    [employer2_work_duties]: take care the kids need to prepare for school, sent / fetch to school bus, prepare for breakfast, food, remind to do homework and do all general household, cleaning, washing, ironing the clothes, marketing, wash the dishes and cooking 
    [employer2_remarks]: There are 3 people in the house consist Mam, Sir and 1 kids 10 years old. HDB, 2 bedroom and 2 toilets. She only helper in the house 
    [employer3_date_from]: null 
    [employer3_date_to]: null 
    [employer3_country]: null 
    [employer3_name]: null 
    [employer3_work_duties]: null 
    [employer3_remarks]: null 
    [employer4_date_from]: null 
    [employer4_date_to]: null 
    [employer4_country]: null 
    [employer4_name]: null 
    [employer4_work_duties]: null 
    [employer4_remarks]: null 
    [employer5_date_from]: null 
    [employer5_date_to]: null 
    [employer5_country]: null 
    [employer5_name]: null 
    [employer5_work_duties]: null 
    [employer5_remarks]: null 
    [employer6_date_from]: null 
    [employer6_date_to]: null 
    [employer6_country]: null 
    [employer6_name]: null 
    [employer6_work_duties]: null 
    [employer6_remarks]: null 
    [employer7_date_from]: null 
    [employer7_date_to]: null 
    [employer7_country]: null 
    [employer7_name]: null 
    [employer7_work_duties]: null 
    [employer7_remarks]: null 
    [employer8_date_from]: null 
    [employer8_date_to>: null 
    [employer8_country>:null 
    [employer8_name>:null 
    [employer8_work_duties>:null 
    [employer8_remarks>:null  
    [prev work in sg] : Yes  
    [maid prev feedback1] :null  
    [maid prev feedback2] :null  
    [avail_interview_not_available] : No  
    [avail_interview_phone] : Yes  
    [avail_interview_videoconference] : Yes  
    [avail_interview_in_person] : No  
    [other remarks] :null  
    [maid passport no] :null  
    [trainingctr maid introduction] :null  
    [internal notes] :null  
        # """

    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"Received data from OpenAI GPT3.5")

    # save_log(os.path.join(LOGPATH, "logs.txt"),"Received data from OpenAI GPT3.5")
    return summary


  except Exception as e:
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"[Failed] Sending text to OpenAI GPT3.5...")
    save_log(os.path.join(session_folder, "logs.txt"),f"Error generating summary from OpenAI GPT3.5: {e}")
    # save_log(os.path.join(LOGPATH, "logs.txt"),"[Failed] Sending text to OpenAI GPT3.5...")
    # save_log(os.path.join(LOGPATH, "logs.txt"),f"Error generating summary from OpenAI GPT3.5: {e}")
    return f"Error generating summary: {e}"
    # return "Summary could not be generated due to an error."
  

def get_summary_from_text(summarized_string, session_id):
  # global LOGPATH

  client = OpenAI()

  response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are an assistant that generates structured text output in a specific format. Always follow the structure and instructions provided without omitting any elements."},
        {"role": "user", "content": summarized_string}
    ],
    temperature=0.3,
    max_tokens=4096,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1
  )



  print("[Success] Sending text to OpenAI GPT3.5")
  session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
  save_log(os.path.join(session_folder, "logs.txt"),"[Success] Sending text to OpenAI GPT3.5")


  try:
    summary = response.choices[0].message.content
    # print(summary)
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"Received data from OpenAI GPT3.5")
    return summary


  except Exception as e:
    # save_log(os.path.join(LOGPATH, "logs.txt"),"[Failed] Sending text to OpenAI GPT3.5...")
    # save_log(os.path.join(LOGPATH, "logs.txt"),f"Error generating summary from OpenAI GPT3.5: {e}")
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"[Failed] Sending text to OpenAI GPT3.5...")
    save_log(os.path.join(session_folder, "logs.txt"),"Error generating summary from OpenAI GPT3.5: {e}")
    return f"Error generating summary: {e}"
    # return "Summary could not be generated due to an error."
  

def get_summary_from_text_gpt4omini(summarized_string, session_id):
  # global LOGPATH


  client = OpenAI()

  response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are an assistant that generates structured text output in a specific format. Always follow the structure and instructions provided without omitting any elements."},
        {"role": "user", "content": summarized_string}
    ],
    temperature=0.3,
    # max_tokens=4096,
    max_tokens=16383,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1
  )



  print("[Success] Sending text to OpenAI GPT4omini")
  session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
  save_log(os.path.join(session_folder, "logs.txt"),"Sending text to OpenAI GPT4omini")


  try:
    summary = response.choices[0].message.content
    # print(summary)
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"Received data from OpenAI GPT4omini")
    return summary


  except Exception as e:
    # save_log(os.path.join(LOGPATH, "logs.txt"),"[Failed] Sending text to OpenAI GPT4omini...")
    # save_log(os.path.join(LOGPATH, "logs.txt"),f"Error generating summary from OpenAI GPT4omini: {e}")
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"[Failed] Sending text to OpenAI GPT4omini...")
    save_log(os.path.join(session_folder, "logs.txt"),"Error generating summary from OpenAI GPT4omini: {e}")
    return f"Error generating summary: {e}"
    # return "Summary could not be generated due to an error."
  

def get_summary_from_text_gpt4o(summarized_string, session_id):
  # global LOGPATH


  client = OpenAI()

  response = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=[
        {"role": "system", "content": "You are an assistant that generates structured text output in a specific format. Always follow the structure and instructions provided without omitting any elements."},
        {"role": "user", "content": summarized_string}
    ],
    temperature=0.3,
    max_tokens=4096,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1
  )

  print("[Success] Sending text to OpenAI GPT3.5")
  session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
  save_log(os.path.join(session_folder, "logs.txt"),"[Success] Sending text to OpenAI GPT4o")


  try:
    summary = response.choices[0].message.content
    # print(summary)
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"Received data from OpenAI GPT4o")
    return summary


  except Exception as e:

    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"[Failed] Sending text to OpenAI GPT4o...")
    save_log(os.path.join(session_folder, "logs.txt"),"Error generating summary from OpenAI GPT4o: {e}")

    # save_log(os.path.join(LOGPATH, "logs.txt"),"[Failed] Sending text to OpenAI GPT4o...")
    # save_log(os.path.join(LOGPATH, "logs.txt"),f"Error generating summary from OpenAI GPT4o: {e}")
    return f"Error generating summary: {e}"
    # return "Summary could not be generated due to an error."
  

def get_summary_from_image(image_path, session_id):

  try: 
    # Read the image file and encode it to base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')

    # Decode base64 string to bytes
    image_data = base64.b64decode(base64_image)

    # Convert bytes to numpy array
    np_arr = np.frombuffer(image_data, np.uint8)

    # Decode numpy array to image
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Convert image to grayscale
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize image to a smaller size
    scale_percent = 50  # percent of original size
    width = int(gray_img.shape[1] * scale_percent / 100)
    height = int(gray_img.shape[0] * scale_percent / 100)
    small_gray_img = cv2.resize(gray_img, (width, height), interpolation=cv2.INTER_AREA)

    # Encode grayscale image to base64
    _, buffer = cv2.imencode('.jpg', small_gray_img)
    base64_gray_image = base64.b64encode(buffer).decode('utf-8')

    # Construct the image URL payload
    image_url_payload = {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_gray_image}"  
        }
    }
    
    print("Sending image and text to OpenAI...")
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"Sending image and text to OpenAI...")

    client = OpenAI()

    response = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {
          "role": "system",
          "content": [
            {
              "type": "text",
              "text": "You are an OCR tool. Your task is to extract and transcribe text, checkboxes, and tables exactly as they appear in the images provided, without summarizing or altering any content. Maintain the exact formatting, punctuation, line breaks, and represent checkboxes and tables accurately."
            }
          ]
        },
        {
          "role": "user",
          "content": [
              {
                  "type": "text",
                  "text": """Extract and transcribe the content from the provided image exactly as it appears. This includes text, checkboxes, and tables. Do not summarize or alter any content. Maintain the exact formatting, punctuation, line breaks, and represent checkboxes and tables accurately.
                            - For checkboxes, use "[ ]" for unchecked and "[x]" for checked.
                            - For tables, preserve the structure with rows and columns as seen in the image."""
              },
              image_url_payload
          ]
        }
      ],
      temperature=1,
      max_tokens=4095,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )

    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"[Success] Sending image and text to OpenAI GPT4o...")

    try:
      summary = response.choices[0].message.content
      print("[Success] Sending image and text to OpenAI...")
      # save_log(os.path.join(LOGPATH, "logs.txt"),"Received data from OpenAI GPT4o...")
      session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
      save_log(os.path.join(session_folder, "logs.txt"),"Received data from OpenAI GPT4o...")
      # print(summary)
      return summary


    except Exception as e:
      print("[Failed] Sending image and text to OpenAI...")

      session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
      save_log(os.path.join(session_folder, "logs.txt"),"[Failed] Sending image and text to OpenAI GPT4o...")
      save_log(os.path.join(session_folder, "logs.txt"),f"Error generating summary from OpenAI GPT4o: {e}")

      return f"Error generating summary: {e}"
      # return "Summary could not be generated due to an error."

  except Exception as e:
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),f"Error generating summary from OpenAI GPT4o: {e}")
    return f"Error generating summary: {e}"


def get_summary_from_image_gpt4omini(image_path, session_id):

  try: 
    # Read the image file and encode it to base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')

    # Decode base64 string to bytes
    image_data = base64.b64decode(base64_image)

    # Convert bytes to numpy array
    np_arr = np.frombuffer(image_data, np.uint8)

    # Decode numpy array to image
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Convert image to grayscale
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize image to a smaller size
    scale_percent = 100  # percent of original size
    width = int(gray_img.shape[1] * scale_percent / 100)
    height = int(gray_img.shape[0] * scale_percent / 100)
    small_gray_img = cv2.resize(gray_img, (width, height), interpolation=cv2.INTER_AREA)

    # Encode grayscale image to base64
    _, buffer = cv2.imencode('.jpg', small_gray_img)
    base64_gray_image = base64.b64encode(buffer).decode('utf-8')

    # Construct the image URL payload
    image_url_payload = {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_gray_image}"  
        }
    }
    
    print("Sending image and text to OpenAI GPT4omini...")
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"Sending image and text to OpenAI GPT4omini...")

    client = OpenAI()

    response = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {
          "role": "system",
          "content": [
            {
              "type": "text",
              "text": "You are an OCR tool. Your task is to extract and transcribe text, checkboxes, and tables exactly as they appear in the images provided, without summarizing or altering any content. Maintain the exact formatting, punctuation, line breaks, and represent checkboxes and tables accurately."
            }
          ]
        },
        {
          "role": "user",
          "content": [
              {
                  "type": "text",
                  "text": """Extract and transcribe the content from the provided image exactly as it appears. This includes text, checkboxes, and tables. Do not summarize or alter any content. Maintain the exact formatting, punctuation, line breaks, and represent checkboxes and tables accurately.
                            - For checkboxes, use "[ ]" for unchecked and "[x]" for checked.
                            - For tables, preserve the structure with rows and columns as seen in the image."""
              },
              image_url_payload
          ]
        }
      ],
      temperature=1,
      # max_tokens=4095,
      max_tokens=16383,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )

    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),"[Success] Sending image and text to OpenAI GPT4omini...")

    try:
      summary = response.choices[0].message.content
      print("[Success] Sending image and text to OpenAI GPT4omini...")
      session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
      save_log(os.path.join(session_folder, "logs.txt"),"Received data from OpenAI GPT4omini...")
      # print(summary)
      return summary


    except Exception as e:
      print("[Failed] Sending image and text to OpenAI GPT4omini...")

      session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
      save_log(os.path.join(session_folder, "logs.txt"),"[Failed] Sending image and text to OpenAI GPT4omini...")
      save_log(os.path.join(session_folder, "logs.txt"),f"Error generating summary from OpenAI GPT4omini: {e}")
      return f"Error generating summary: {e}"
      # return "Summary could not be generated due to an error."

  except Exception as e:
    session_folder = os.path.join(app.config['EXTRACTED_PAGE_IMAGES_FOLDER'], session_id)
    save_log(os.path.join(session_folder, "logs.txt"),f"Error generating summary from OpenAI GPT4omini: {e}")
    return f"Error generating summary: {e}"



def get_summary_from_image_gpt5nano(image_path):
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')

        image_data = base64.b64decode(base64_image)
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        scale_percent = 100
        width = int(gray_img.shape[1] * scale_percent / 100)
        height = int(gray_img.shape[0] * scale_percent / 100)
        small_gray_img = cv2.resize(gray_img, (width, height), interpolation=cv2.INTER_AREA)

        _, buffer = cv2.imencode('.jpg', small_gray_img)
        base64_gray_image = base64.b64encode(buffer).decode('utf-8')

        image_url_payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_gray_image}"
            }
        }

        print("Sending image and text to OpenAI GPT5 Nano...")
        save_log(os.path.join(LOGPATH, "logs.txt"), "Sending image and text to OpenAI GPT5 Nano...")

        client = OpenAI()

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are an OCR tool. Extract and transcribe content exactly as shown, preserving formatting, tables, and checkboxes."
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract and transcribe the image exactly as it appears."
                        },
                        image_url_payload
                    ]
                }
            ],
            response_format={
                "type": "text"
              },
        )

        save_log(os.path.join(LOGPATH, "logs.txt"), "[Success] Received data from OpenAI GPT5 Nano")
        return response.choices[0].message.content

    except Exception as e:
        save_log(os.path.join(LOGPATH, "logs.txt"), f"[Failed] GPT5 Nano error: {e}")
        return f"Error generating summary: {e}"


def get_summary_from_image_gpt5mini(image_path):
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')

        image_data = base64.b64decode(base64_image)
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        scale_percent = 100
        width = int(gray_img.shape[1] * scale_percent / 100)
        height = int(gray_img.shape[0] * scale_percent / 100)
        small_gray_img = cv2.resize(gray_img, (width, height), interpolation=cv2.INTER_AREA)

        _, buffer = cv2.imencode('.jpg', small_gray_img)
        base64_gray_image = base64.b64encode(buffer).decode('utf-8')

        image_url_payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_gray_image}"
            }
        }

        print("Sending image and text to OpenAI GPT5 Mini...")
        save_log(os.path.join(LOGPATH, "logs.txt"), "Sending image and text to OpenAI GPT5 Mini...")

        # client = OpenAI()
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are an OCR tool. Extract and transcribe content exactly as shown, preserving formatting, tables, and checkboxes."
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract and transcribe the image exactly as it appears."
                        },
                        image_url_payload
                    ]
                }
            ],
            response_format={
                "type": "text"
              },
        )

        save_log(os.path.join(LOGPATH, "logs.txt"), "[Success] Received data from OpenAI GPT5 Mini")
        return response.choices[0].message.content

    except Exception as e:
        save_log(os.path.join(LOGPATH, "logs.txt"), f"[Failed] GPT5 Mini error: {e}")
        return f"Error generating summary: {e}"


def get_summary_from_text_gpt5nano(custom_prompt, summarized_string):
    global LOGPATH

    try:
        # client = OpenAI()
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "developer",
                    "content": f"You are an assistant that generates structured text output in a specific format. Always follow the structure and instructions provided without omitting any elements. {custom_prompt}"
                },
                {
                    "role": "user",
                    "content": summarized_string
                }
            ],
            response_format={
                "type": "text"
              },
        )

        print("[Success] Sending text to OpenAI GPT5 Nano")
        save_log(os.path.join(LOGPATH, "logs.txt"), "[Success] Sending text to OpenAI GPT5 Nano")

        summary = response.choices[0].message.content
        save_log(os.path.join(LOGPATH, "logs.txt"), "Received data from OpenAI GPT5 Nano")
        return summary

    except Exception as e:
        save_log(os.path.join(LOGPATH, "logs.txt"), "[Failed] Sending text to OpenAI GPT5 Nano...")
        save_log(os.path.join(LOGPATH, "logs.txt"), f"Error generating summary from OpenAI GPT5 Nano: {e}")
        return f"Error generating summary: {e}"


def get_summary_from_text_gpt5mini(custom_prompt, summarized_string):
    global LOGPATH

    try:
        # client = OpenAI()
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "developer",
                    "content": f"You are an assistant that generates structured text output in a specific format. Always follow the structure and instructions provided without omitting any elements. {custom_prompt}"
                },
                {
                    "role": "user",
                    "content": summarized_string
                }
            ],
        response_format={
            "type": "text"
          },

        )

        print("[Success] Sending text to OpenAI GPT5 Mini")
        save_log(os.path.join(LOGPATH, "logs.txt"), "[Success] Sending text to OpenAI GPT5 Mini")

        summary = response.choices[0].message.content
        save_log(os.path.join(LOGPATH, "logs.txt"), "Received data from OpenAI GPT5 Mini")
        return summary

    except Exception as e:
        save_log(os.path.join(LOGPATH, "logs.txt"), "[Failed] Sending text to OpenAI GPT5 Mini...")
        save_log(os.path.join(LOGPATH, "logs.txt"), f"Error generating summary from OpenAI GPT5 Mini: {e}")
        return f"Error generating summary: {e}"

