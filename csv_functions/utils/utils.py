import os
import re
import codecs
import csv
from datetime import datetime
# from app import maid_status_global


# Define accepted characters as a regular expression pattern
accepted_chars_pattern = r'[ &_$a-zA-Z0-9\(\)\-\~\/\\\<\>=\.\@:;+|]' ## with "underscore"
# accepted_chars_pattern = r'[ &$a-zA-Z0-9\(\)\-\~\/\\\<\>=\.\@:;+|]'

# Regular expression to match date patterns
date_pattern = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')

def remove_non_digits(input_str):
    # Use regular expressions to keep only digits
    return re.sub(r'\D', '', input_str)

def filter_accepted_chars(item):
    # Use regular expression to filter out unwanted characters
    return ''.join(re.findall(accepted_chars_pattern, item))


def get_maid_name_index(header, column_name):
    try:
        # Return the index of the specified column_name
        return header.index(column_name)
    except ValueError:
        # Handle the case where column_name is not found in the header
        return -1  # or any other default value or message
    
def set_maid_status(maid_status_global):
    if maid_status_global == "Transfer" or maid_status_global == "Ex-SG":
        return "Yes"
    elif maid_status_global == "New Maid":
        return "No"
    elif maid_status_global == "Others":
        return maid_status_global  
    else:
        return maid_status_global 
    
def format_age(data):
    try:
        # Check if the data matches the expected format (e.g., 6/4 or 6/4/5)
        if '/' in data:
            # Split the data by the slash
            parts = data.split('/')
            # Check if all parts are numbers
            if all(part.isdigit() for part in parts):
                # Join the parts with commas and append " years old"
                return ', '.join(parts) + " years old"
        # If it doesn't match the expected format, return the original data
        return data
    except Exception as e:
        # Handle any unexpected errors and print the exception message
        print(f"Error: {e}")
        return data

def format_age2(data):
    try:
        # Check if the data matches the expected format (e.g., 6/4 or 6/4/5 or 6-4-5 or 6-4)
        if '/' in data or '-' in data:
            # Normalize the separator to '/' for consistent processing
            separator = '/' if '/' in data else '-'
            # Split the data by the separator
            parts = data.split(separator)
            # Check if all parts are numbers
            if all(part.isdigit() for part in parts):
                # Join the parts with commas and append " years old"
                return ', '.join(parts) + " years old"
        # If it doesn't match the expected format, return the original data
        return data
    except Exception as e:
        # Handle any unexpected errors and print the exception message
        print(f"Error: {e}")
        return data

# Function to convert date format
def convert_date_format(date_str):
    try:
        # Parse the date using the original format
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        # Format the date into the new format
        return date_obj.strftime("%d-%b-%y")
    except ValueError:
        return date_str

# Function to replace dates in text
def replace_dates(text):
    return date_pattern.sub(lambda match: convert_date_format(match.group()), text)

def convert_date(date_str):
    try:
        # Try to parse the date using the expected format
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        # Format the date object to the desired format
        return date_obj.strftime("%d/%m/%y")
    except ValueError:
        # Return an error message or placeholder if the input is not a valid date
        return "'"

def save_csv(filename, header, data):

    # Normalize the file path (this ensures that it works on both Windows and Linux)
    filepath = os.path.normpath(filename)
    
    # Get the directory from the file path
    directory = os.path.dirname(filepath)
    
    # Create the directory and any necessary subdirectories if they don't exist
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Replace spaces with underscores in headers
    header = [column.replace(' ', '_') for column in header]

    # character cleansing in the list "header"
    header = [filter_accepted_chars(item) for item in header]

    # Modify specific header value if found
    for i in range(len(header)):
        if header[i] == 'language_english_experience':
            header[i] = 'Language–English–Experience'
        if header[i] == 'language_english_stars':
            header[i] = 'Language–English–stars'
        if header[i] == 'expertise_care_for_infant|children_experience__willing':
            header[i] = 'Expertise–Care for Infant/Children–Experience – Willing?'
        if header[i] == 'expertise_care_for_infant|children_experience_willing':
            header[i] = 'Expertise–Care for Infant/Children–Experience – Willing?'
        if header[i] == 'expertise_care_for_infant|children_experience':
            header[i] = 'Expertise–Care for Infant/Children–Experience'

        if header[i] == 'expertise_care_for_infant|children_stars':
            header[i] = 'Expertise–Care for Infant/Children–stars'
        if header[i] == 'expertise_care_for_elderly_experience__willing':
            header[i] = 'Expertise–Care for Elderly–Experience – Willing?'

        if header[i] == 'expertise_care_for_elderly_experience':
            header[i] = 'Expertise–Care for Elderly–Experience'

        if header[i] == 'expertise_care_for_elderly_stars':
            header[i] = 'Expertise–Care for Elderly–stars'
        if header[i] == 'expertise_care_for_disabled_experience__willing':
            header[i] = 'Expertise–Care for Disabled–Experience – Willing?'
        if header[i] == 'expertise_care_for_disabled_experience_willing':
            header[i] = 'Expertise–Care for Disabled–Experience – Willing?'
        
        if header[i] == 'expertise_care_for_disabled_experience':
            header[i] = 'Expertise–Care for Disabled–Experience'
        if header[i] == 'expertise_care_for_disabled_stars':
            header[i] = 'Expertise–Care for Disabled–stars'
        if header[i] == 'expertise_general_housework_experience__willing':
            header[i] = 'Expertise–General Housework–Experience – Willing?'
        if header[i] == 'expertise_general_housework_experience_willing':
            header[i] = 'Expertise–General Housework–Experience – Willing?'
        if header[i] == 'expertise_general_housework_experience_willing':
            header[i] = 'Expertise–General Housework–Experience – Willing?'

        if header[i] == 'expertise_general_housework_experience':
            header[i] = 'Expertise–General Housework–Experience'
        if header[i] == 'expertise_general_housework_stars':
            header[i] = 'Expertise–General Housework–stars'
        if header[i] == 'expertise_cooking_experience__willing':
            header[i] = 'Expertise–Cooking–Experience – Willing?'
        if header[i] == 'expertise_cooking_experience_willing':
            header[i] = 'Expertise–Cooking–Experience – Willing?'

        if header[i] == 'expertise_cooking_experience':
            header[i] = 'Expertise–Cooking–Experience'
        if header[i] == 'expertise_cooking_stars':
            header[i] = 'Expertise–Cooking–stars'

        if header[i] == 'additional_info_able_to_handle_pork':
            header[i] = 'AdditionalInfo–Able to handle pork?'
        if header[i] == 'additional_info_able_to_eat_pork':
            header[i] = 'AdditionalInfo–Able to eat pork?'
        if header[i] == 'additional_info_able_to_handle_beef':
            header[i] = 'AdditionalInfo–Able to handle beef?'
        if header[i] == 'additional_info_able_to_care_dog|cat':
            header[i] = 'AdditionalInfo–Able to care dog/cat?'

        if header[i] == 'additional_info_able_to_do_gardening_work':
            header[i] = 'AdditionalInfo–Able to do gardening work?'

        if header[i] == 'additional_info_able_to_do_simple_sewing':
            header[i] = 'AdditionalInfo–Able to do simple sewing?'
        if header[i] == 'additional_info_willing_to_wash_car':
            header[i] = 'AdditionalInfo–Willing to wash car?'
        if header[i] == 'experience_singaporean_experience':
            header[i] = 'Experience–Singaporean–Experience'

        if header[i] == 'language_mandarin|chinese_dialect_experience':
            header[i] = 'Language–Mandarin/Chinese–Dialect–Experience'
        if header[i] == 'language_mandarin|chinese_dialect_stars':
            header[i] = 'Language–Mandarin/Chinese–Dialect–stars'
        if header[i] == 'experience_others_experience':
            header[i] = 'Experience–Others–Experience'

    # Check if the file exists
    file_exists = os.path.exists(filename)

    # Function to process each data item
    def process_data_item(item):
        unwanted_values = ["not provided", "n/a", "n.a","null", "not found", "not-found", "not specified", "not applicable", "none", "not mentioned", "not-mentioned", "not evaluated"]
        item_lower = item.strip().lower()

        # Replace 'X' with 'Yes'
        if item_lower == 'x':
            return 'Yes'
        
        # Check for unwanted values
        for unwanted in unwanted_values:
            if item_lower == unwanted:
                return ""

        # Check for values
        for unwanted in ["no."]:
            item_lower = item.strip().lower()
            if item_lower == unwanted:
                return "No"

        for unwanted in ["yes."]:
            item_lower = item.strip().lower()
            if item_lower == unwanted:
                return "Yes"
                
        # Check if any unwanted value is in item_lower
        # Therefore, if item_lower is " language english experience null, ", the process_data_item function will return ""

        if len(item_lower) <= 17: ## to make sure that it will not affect a item's value has long content like "maid employment history" or others
            # Execute the block only if item_lower is 17 characters or shorter
            for unwanted in unwanted_values:
                if unwanted in item_lower:
                    return ""  # Return empty string if unwanted value is found

        # Filter accepted characters
        filtered_item = filter_accepted_chars(item)

        ## replace "comma" symbol with whitespace in the each item's data to avaold conflict with csv delimiter
        filtered_item = filtered_item.replace(",", " ")
        filtered_item = filtered_item.replace("_", "")
        
        return filtered_item.strip()

    # Process each item in data list
    processed_data = [process_data_item(item) for item in data]

    # Function to process each data item and capitalize words
    def process_data_item2(item):
        words = item.split()
        processed_words = []
        for word in words:
            processed_words.append(word.lower().capitalize())
        return ' '.join(processed_words)

    def extract_numeric(data):

        # Return empty string if data contains "null"
        if "null" in data:
            return ""

        # Regex pattern to extract the initial numeric value before any non-numeric characters
        match = re.match(r'(\d+\.\d+|\d+)', data)
        if match:
            return match.group()
        return ""  # or handle the case when no match is found

    # Process each item in data list
    processed_data2 = [process_data_item2(item) for item in processed_data]

    # Store first the date of birth before date replacement
    new_dateofbirth = processed_data2[12]

    # Apply the date replacement to each text in the list
    processed_data2 = [replace_dates(text) for text in processed_data2]

    ## after the date replacement (not affected), bring back the date of birth with a new format
    processed_data2[12] = convert_date(new_dateofbirth) # Output: 22/07/76

    # processed_data2[12] = "'" + new_dateofbirth ## the date of birth in your CSV file is treated as text and not automatically formatted as a date in Excel, you should enclose the date values in double quotes and prefix them with an apostrophe ('). This tells Excel to treat the content as text.

    # processed_data2[12] = '"' + new_dateofbirth + '"' ## the date of birth in your CSV file is treated as text and not automatically formatted as a date in Excel, you should enclose the date values in double quotes and prefix them with an apostrophe ('). This tells Excel to treat the content as text.


    # clean the maid_expected_salary, only 0-9 character is allowed.
    processed_data2[3] = remove_non_digits(processed_data2[3])

    try:

        # Special Case: Uppercase the second index in processed_data2
        if len(processed_data2) > 1:
            processed_data2[1] = processed_data2[1].upper()

        # Special Case: Function to extract numeric characters from a string for "evalsg_lang_english_stars"
        if len(processed_data2) > 6:
            processed_data2[6] = extract_numeric(processed_data2[6] )

        # Special Case: Function to extract numeric characters from a string for "evalsg_lang_mandarin_stars"
        if len(processed_data2) > 7:
            processed_data2[7] = extract_numeric(processed_data2[7] )

        # Special Case: Function to extract numeric characters from a string for "evalsg_lang_malay_stars"
        if len(processed_data2) > 8:
            processed_data2[8] = extract_numeric(processed_data2[8] )

        # Special Case: Function to extract numeric characters from a string for "evalsg_lang_tamil_stars"
        if len(processed_data2) > 9:
            processed_data2[9] = extract_numeric(processed_data2[9] )

        # Special Case: Function to extract numeric characters from a string for "evalsg_lang_hindi_stars"
        if len(processed_data2) > 10:
            processed_data2[10] = extract_numeric(processed_data2[10] )

        # Special Case: Function to extract numeric characters from a string for "public_introduction"
        if len(processed_data2) > 10:
            processed_data2[11] = processed_data2[11].replace('. ', '.\n') # handles space after period
 
        # Special Case: Function to extract numeric characters from a string for "height_cm"
        if len(processed_data2) > 14:
            processed_data2[14] = extract_numeric(processed_data2[14] )

        # Special Case: Function to extract numeric characters from a string for "weight_kg"
        if len(processed_data2) > 15:
            processed_data2[15] = extract_numeric(processed_data2[15] )

        # Special Case: Function to extract numeric characters from a string for "siblings_count"
        if len(processed_data2) > 23:
            if processed_data2[23] == "":
                processed_data2[23] = "0"
            else:
                processed_data2[23] = extract_numeric(processed_data2[23] )
            

        # Special Case: Function to extract numeric characters from a string for "children_count"
        if len(processed_data2) > 25:
            processed_data2[25] = extract_numeric(processed_data2[25] )

        ## # Special Case: for "children_ages"
        processed_data2[26] = format_age(processed_data2[26])

        # Special Case: Function to extract numeric characters from a string for "eval_agency_years_infant_child"
        if len(processed_data2) > 54:
            processed_data2[54] = extract_numeric(processed_data2[54] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_stars_infant_child"
        if len(processed_data2) > 55:
            processed_data2[55] = extract_numeric(processed_data2[55] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_years_elderly"
        if len(processed_data2) > 58:
            processed_data2[58] = extract_numeric(processed_data2[58] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_stars_elderly"
        if len(processed_data2) > 59:
            processed_data2[59] = extract_numeric(processed_data2[59] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_years_disabled"
        if len(processed_data2) > 62:
            processed_data2[62] = extract_numeric(processed_data2[62] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_stars_disabled"
        if len(processed_data2) > 63:
            processed_data2[63] = extract_numeric(processed_data2[63] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_years_housework"
        if len(processed_data2) > 66:
            processed_data2[66] = extract_numeric(processed_data2[66] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_stars_housework"
        if len(processed_data2) > 67:
            processed_data2[67] = extract_numeric(processed_data2[67] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_years_cooking"
        if len(processed_data2) > 71:
            processed_data2[71] = extract_numeric(processed_data2[71] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_stars_cooking"
        if len(processed_data2) > 72:
            processed_data2[72] = extract_numeric(processed_data2[72] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_years_language"
        if len(processed_data2) > 76:
            processed_data2[76] = extract_numeric(processed_data2[76] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_stars_language"
        if len(processed_data2) > 77:
            processed_data2[77] = extract_numeric(processed_data2[77] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_years_other_skills"
        if len(processed_data2) > 81:
            processed_data2[81] = extract_numeric(processed_data2[81] )

        # Special Case: Function to extract numeric characters from a string for "eval_agency_stars_other_skills"
        if len(processed_data2) > 82:
            processed_data2[82] = extract_numeric(processed_data2[82] )

        ## # Special Case: for "eval_agency_age_range_infant_child"
        processed_data2[90] = format_age2(processed_data2[90])

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_years_infant_child"
        if len(processed_data2) > 92:
            processed_data2[92] = extract_numeric(processed_data2[92] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_stars_infant_child"
        if len(processed_data2) > 93:
            processed_data2[93] = extract_numeric(processed_data2[93] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_years_elderly"
        if len(processed_data2) > 96:
            processed_data2[96] = extract_numeric(processed_data2[96] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_stars_elderly"
        if len(processed_data2) > 97:
            processed_data2[97] = extract_numeric(processed_data2[97] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_years_disabled"
        if len(processed_data2) > 100:
            processed_data2[100] = extract_numeric(processed_data2[100] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_stars_disabled"
        if len(processed_data2) > 101:
            processed_data2[101] = extract_numeric(processed_data2[101] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_years_housework"
        if len(processed_data2) > 104:
            processed_data2[104] = extract_numeric(processed_data2[104] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_stars_housework"
        if len(processed_data2) > 105:
            processed_data2[105] = extract_numeric(processed_data2[105] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_years_cooking"
        if len(processed_data2) > 109:
            processed_data2[109] = extract_numeric(processed_data2[109] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_stars_cooking"
        if len(processed_data2) > 110:
            processed_data2[110] = extract_numeric(processed_data2[110] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_years_language"
        if len(processed_data2) > 114:
            processed_data2[114] = extract_numeric(processed_data2[114] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_stars_language"
        if len(processed_data2) > 115:
            processed_data2[115] = extract_numeric(processed_data2[115] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_years_other_skills"
        if len(processed_data2) > 119:
            processed_data2[119] = extract_numeric(processed_data2[119] )

        # Special Case: Function to extract numeric characters from a string for "eval_trainingctr_stars_other_skills"
        if len(processed_data2) > 121:
            processed_data2[121] = extract_numeric(processed_data2[121] )


        # Indices and default values to check for empty string and replace with "No"
        special_cases = {
            27: "No", 
            28: "No",  ## "illness_mental"
            29: "No", 
            30: "No", 
            31: "No", 
            32: "No", 
            33: "No", 
            34: "No", 
            35: "No", 
            36: "No",  ## "illness_operations"
            37: "No",  ## "illness_others"
            40: "No",  ## "handle_pork"
            41: "No",  ## "handle_beef"
            42: "No",  ## "handle_pets"
            44: "No",  ## "0 Rest Day Per Month"
            46: "No",  ## "eval_no_agency_no_trainingctr"
            51: "No",  ## "eval_agency_in_person_observation"
            53: "No",  ## "eval_agency_willing_infant_child"
            57: "No",  ## "eval_agency_willing_elderly"
            61: "No",  ## "eval_agency_willing_disabled"
            65: "No",  ## "eval_agency_willing_housework"
            80: "No",  ## "eval_agency_willing_cooking"
            75: "No",  ## "eval_agency_willing_language"
            80: "No",  ## "eval_agency_willing_other_skills"
            86: "No",  ## "eval_trainingctr_telephone"
            87: "No",
            88: "No",
            89: "No",  ## "eval_trainingctr_in_person_observation"
            91: "Yes",  ## "eval_trainingctr_willing_infant_child"
            92: "0",  ## "eval_trainingctr_years_infant_child"
            95: "Yes",  ## "eval_trainingctr_willing_elderly"
            96: "0",  ## "eval_trainingctr_years_elderly"
            99: "Yes",  ## "eval_trainingctr_willing_disabled"
            100: "0",  ## "eval_trainingctr_years_disabled"
            103: "No",  ## "eval_trainingctr_willing_housework"
            104: "0",  ## "eval_trainingctr_years_housework"
            108: "Yes",  ## "eval_trainingctr_willing_cooking"
            109: "0",  ## "eval_trainingctr_years_cooking"
            113: "Yes",  ## "eval_trainingctr_willing_language"
            114: "0",  ## "eval_trainingctr_years_language"
            118: "Yes",  ## "eval_trainingctr_willing_other_skills"
            119: "0",    ## "eval_trainingctr_years_other_skills"
            # 171: "No",  ## "prev_work_in_sg"

            174: "Yes", ## "avail_interview_not_available"
            175: "Yes",  ## "avail_interview_phone"
            176: "Yes",  ## "avail_interview_videoconference"
            177: "Yes"   ##  "avail_interview_in_person"
        }

        for index, default_value in special_cases.items():
            if len(processed_data2) > index and processed_data2[index] == "":
                processed_data2[index] = default_value

         ## "prev_work_in_sg"
        if len(processed_data2) > 171:
            processed_data2[171] = set_maid_status(processed_data2[171])

            
        # Convert "Yrs" or "Years" to "yrs" or "years" in processed_data2[22]
        if len(processed_data2) > 22:
            processed_data2[22] = processed_data2[22].replace("Yrs", "yrs").replace("Years", "years").replace("Level", "level")
    
    except Exception as e:
        print(e)

    # Replace "Ex-sg Maid" to "Ex-SG Maid"
    def process_data_item3(item):
        if item == "Ex-sg Maid":
            return "Ex-SG Maid"
        return item

    # Process each item in data list
    processed_data2 = [process_data_item3(item) for item in processed_data2]

    # # Write data to CSV file with UTF-8
    # with open(filename, 'a', 'utf-8') as csvfile:
    #     if not file_exists:
    #         # Join headers with commas (no double quotes)
    #         header_row = ','.join(header)
    #         csvfile.write(f'{header_row}')
        
    #     # Write processed data with commas (no double quotes)
    #     processed_data_rows = ','.join(processed_data2)
    #     csvfile.write(f'\n{processed_data_rows}')

    ## simple csv generation
    # with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
    #     # If the file doesn't exist, write the header
    #     if not file_exists:
    #         csvfile.write('"' + '","'.join(header) + '"\n')

    #     # Write the data
    #     csvfile.write('"' + '","'.join(processed_data2) + '"\n')


    ## csv generation 
    # ## Write data to CSV file with UTF-8 BOM
    # with codecs.open(filename, 'a', 'utf-8-sig') as csvfile:
    #     if not file_exists:
    #         csvfile.write('"' + '","'.join(header) + '"\n')
    #     csvfile.write('"' + '","'.join(processed_data2) + '"\n')

    # ## Write data to CSV file with UTF-8 BOM
    # with codecs.open(filename, 'a', 'utf-8-sig') as csvfile:
    #     if not file_exists:
    #         csvfile.write('"' + '","'.join(header) + '"\n')
        
    #     # Extract the first item and join the remaining items with quotes
    #     first_item = processed_data2[0]
    #     remaining_items = '","'.join(processed_data2[1:])
    #     csvfile.write(f'{first_item},"{remaining_items}"\n')


    # # Write data to CSV file with UTF-8 BOM
    # with codecs.open(filename, 'a', 'utf-8-sig') as csvfile:
    #     if not file_exists:
    #         # Join headers with commas (no double quotes)
    #         header_row = ','.join(header)
    #         csvfile.write(f'{header_row}\n')
        
    #     # Write processed data with commas (no double quotes)
    #     processed_data_rows = ','.join(processed_data2)
    #     csvfile.write(f'{processed_data_rows}\n')

    # # Open file in append mode with UTF-8 encoding
    # with open(filename, 'a', encoding='utf-8') as csvfile:
    #     if not file_exists:
    #         # Join headers with commas and write the header row
    #         header_row = ','.join(header)
    #         csvfile.write(f'{header_row}')  # Write the header with a newline
        
    #     # Join processed data with commas and write the processed data row
    #     processed_data_rows = ','.join(processed_data2)
    #     csvfile.write(f'\n{processed_data_rows}')

    try:
        # Open file in append mode with UTF-8 encoding
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile, lineterminator='\r\n')

            # Write header if file does not exist
            if not file_exists:
                csvwriter.writerow(header)

            # Write processed data row once
            csvwriter.writerow(processed_data2)

    except Exception as e:
        print(f"Error writing to CSV file: {e}")

    # try:
    #     ## csv generation with double quotes
    #     with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
    #         # If the file doesn't exist, write the header
    #         if not file_exists:
    #             csvfile.write('"' + '","'.join(header) + '"\r\n')
    
    #         # Write the data
    #         csvfile.write('"' + '","'.join(processed_data2) + '"\r\n')
    # except Exception as e:
    #     print(f"Error writing to CSV file: {e}")

    # try:
    #     # Open file in append mode with UTF-8 encoding
    #     with open(filename, 'a', encoding='utf-8', newline='') as csvfile:
    #         if not file_exists:
    #             # Join headers with commas and write the header row
    #             header_row = ','.join(header)
    #             csvfile.write(f'{header_row}')  # Write the header with CRLF newline
            
    #         # Join processed data with commas and write the processed data row
    #         processed_data_rows = ','.join(processed_data2)
    #         csvfile.write(f'\r\n{processed_data_rows}')  # Write the processed data row with CRLF newline

    # except Exception as e:
    #     print(f"Error writing to CSV file: {e}")



    # # Write data to CSV file
    # with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
    #     writer = csv.writer(csvfile)
        
    #     if not file_exists:
    #         # Write the header row
    #         writer.writerow(header)
        
    #     # Write the processed data row
    #     writer.writerow(processed_data2)

# # # Example usage:
# filename = 'example.csv'
# # header = ['Column 1', 'Column 2', 'Column 3']
# # data = ['$456â‰0%abA', "hello", 'Secondary level (8~9 Yrs)', 'null']

header = ["maid_name","maid_ref_code","maid_type","maid_expected_salary","availability_status","youtube_link","evalsg_lang_english_stars","evalsg_lang_mandarin_stars","evalsg_lang_malay_stars","evalsg_lang_tamil_stars","evalsg_lang_hindi_stars","public_maid_introduction","date_of_birth","place_of_birth","height_cm","weight_kg","nationality","sub_nationality","home_address","home_airport_repatriate","home_contact_number","religion","education","siblings_count","marital_status","children_count","children_ages","allergies","illness_mental","illness_epilepsy","illness_asthma","illness_diabetes","illness_hypertension","illness_tuberculosis","illness_heart_disease","illness_malaria","illness_operations","illness_others","physical_disabilities","dietary_restrictions","handle_pork","handle_beef","handle_pets","handle_others","maid_preferred_rest_day","maid_other_remarks","eval_no_agency_no_trainingctr","eval_agency","eval_agency_telephone","eval_agency_videoconference","eval_agency_in_person","eval_agency_in_person_observation","eval_agency_age_range_infant_child","eval_agency_willing_infant_child","eval_agency_years_infant_child","eval_agency_stars_infant_child","eval_agency_comments_infant_child","eval_agency_willing_elderly","eval_agency_years_elderly","eval_agency_stars_elderly","eval_agency_comments_elderly","eval_agency_willing_disabled","eval_agency_years_disabled","eval_agency_stars_disabled","eval_agency_comments_disabled","eval_agency_willing_housework","eval_agency_years_housework","eval_agency_stars_housework","eval_agency_comments_housework","eval_agency_specify_cuisines_cooking","eval_agency_willing_cooking","eval_agency_years_cooking","eval_agency_stars_cooking","eval_agency_comments_cooking","eval_agency_language","eval_agency_willing_language","eval_agency_years_language","eval_agency_stars_language","eval_agency_comments_language","eval_agency_specify_other_skills","eval_agency_willing_other_skills","eval_agency_years_other_skills","eval_agency_stars_other_skills","eval_agency_comments_other_skills","trainingctr_name","trainingctr_certified","eval_trainingctr_telephone","eval_trainingctr_videoconference","eval_trainingctr_in_person","eval_trainingctr_in_person_observation","eval_trainingctr_age_range_infant_child","eval_trainingctr_willing_infant_child","eval_trainingctr_years_infant_child","eval_trainingctr_stars_infant_child","eval_trainingctr_comments_infant_child","eval_trainingctr_willing_elderly","eval_trainingctr_years_elderly","eval_trainingctr_stars_elderly","eval_trainingctr_comments_elderly","eval_trainingctr_willing_disabled","eval_trainingctr_years_disabled","eval_trainingctr_stars_disabled","eval_trainingctr_comments_disabled","eval_trainingctr_willing_housework","eval_trainingctr_years_housework","eval_trainingctr_stars_housework","eval_trainingctr_comments_housework","eval_trainingctr_specify_cuisines_cooking","eval_trainingctr_willing_cooking","eval_trainingctr_years_cooking","eval_trainingctr_stars_cooking","eval_trainingctr_comments_cooking","eval_trainingctr_language","eval_trainingctr_willing_language","eval_trainingctr_years_language","eval_trainingctr_stars_language","eval_trainingctr_comments_language","eval_trainingctr_specify_other_skills","eval_trainingctr_willing_other_skills","eval_trainingctr_years_other_skills","eval_trainingctr_stars_other_skills","eval_trainingctr_comments_other_skills","employment_history","employer1_date_from","employer1_date_to","employer1_country","employer1_name","employer1_work_duties","employer1_remarks","employer2_date_from","employer2_date_to","employer2_country","employer2_name","employer2_work_duties","employer2_remarks","employer3_date_from","employer3_date_to","employer3_country","employer3_name","employer3_work_duties","employer3_remarks","employer4_date_from","employer4_date_to","employer4_country","employer4_name","employer4_work_duties","employer4_remarks","employer5_date_from","employer5_date_to","employer5_country","employer5_name","employer5_work_duties","employer5_remarks","employer6_date_from","employer6_date_to","employer6_country","employer6_name","employer6_work_duties","employer6_remarks","employer7_date_from","employer7_date_to","employer7_country","employer7_name","employer7_work_duties","employer7_remarks","employer8_date_from","employer8_date_to","employer8_country","employer8_name","employer8_work_duties","employer8_remarks","prev_work_in_sg","maid_prev_feedback1","maid_prev_feedback2","avail_interview_not_available","avail_interview_phone","avail_interview_videoconference","avail_interview_in_person","other_remarks","maid_passport_no","trainingctr_maid_introduction","internal_notes",""]
# data = ["Nur Arisa","DS0318","Ex-sg Maid","","Other","","3yeasrs",
# "3years","9years","9years","9years",
# "She Has Experience As A Housemaid In Singapore For 10 Years. She Is Good At Taking Care Of Children And Elderly. She Is Good Patient And Obedient Girl. She Can Speak Good English And Mandarin Also Can Cook Chinese Food. She Is Highly Recommended To Work In Singapore With Family Who Have New Born Baby Children And Elderly.","04/03/1987","Banyuwangi / East Java","161cm","89lbs","Indonesian","","Dusun Sumbersuko Rt. 001/002 Desa Kesilir Kec. Siliragung Kab. Banyuwangi East Java","Jakarta","62","Muslim",
# "High School (11-12 yrs)","6siblings","Married","1","11 Y.o-boy","Nil","","Yes","No","No","No","No","No","No","No","No","Nil","Nil","Yes","Yes","Yes","","1 Rest Days Per Month","","","Overseas Training Centre/ea","No","No","No","Yes","NBB-BOY","Yes","4","3","","Yes","4","4","","Yes","","3","","Yes","10","4","","Soup Fried Vegetables Porridge Steam Fish Etc.","Yes","10","3","","English","Yes","10","3","English Is Good With 10 Years Of Experience.","Handle Pets","Yes","2","3","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","- Date: Sep 2020 - Feb 2024","Sep-20","Feb-24","Singapore","Mr Muhamad Fadil","Cleaning House Making Bed Washing & Ironing Cooking Serve Meal Take Care Ahma 83 Y.o-stroke.","Finish Contract","Jul-20","Sep-20","Singapore","Mr Patrick","Cleaning House Making Bed Washing & Ironing Cooking Serve Meal Take Care Baby 4 Months-boy","2 Months/ Er Back To Vietnam","Dec-19","Jul-20","Singapore","Ms Ling"," Cleaning House Making Bed Washing & Cooking Take Care Akong 89 Y.o-stroke.","7 Months/ Er Pass Away","Mar-15","Feb-19","Singapore","Mr Lee Lay Peng","Cleaning House Making Bed Washing & Ironing Cooking Take Care Nbb-boy.","Finish Contract","Mar-10","Feb-12","Singapore","Mr Wong Sing Kuew","Cleaning House Making Bed Washing & Ironing Cooking Handling 2 Dogs.","Finish Contract","","","","","","","","","","","","","","","","","","","Yes","Wong Sing Kuwe Mr","Lee Lay Peng Ms","","X","X","X","I Have Gone Through The Biodata Of This Fdw And Confirm That I Would Like To Employ Her.","",""]


# print(get_maid_name_index(header,"eval_trainingctr_years_other_skills"))
# print(header[119])

# print(header[26]) ## chilren_ages
# print(data[3])
# # print(header[174])
# # print(data[174])
# # save_csv(filename, header, data)
# print("Done")