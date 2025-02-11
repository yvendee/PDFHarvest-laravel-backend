import os 

# def save_log(filepath, data):
#     with open(filepath, "a", encoding="utf-8") as text_file:
#         text_file.write(f"{data}\n")



def save_log(filepath, data):

    # Normalize the file path (this ensures that it works on both Windows and Linux)
    filepath = os.path.normpath(filepath)
    
    # Get the directory from the file path
    directory = os.path.dirname(filepath)
    
    # Create the directory and any necessary subdirectories if they don't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    # Check if the file exists, if not, create it
    if not os.path.exists(filepath):
        # Create the file if it doesn't exist
        with open(filepath, "w", encoding="utf-8") as text_file:
            text_file.write(f"{data}\n")
    else:
        # If the file exists, append the data
        with open(filepath, "a", encoding="utf-8") as text_file:
            text_file.write(f"{data}\n")
