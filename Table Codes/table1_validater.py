import os
import pandas as pd
import re

def parse_chat_group_name(file_name, team_name):
    # Remove the "WhatsApp Chat with " prefix and the file extension
    group_name_with_extension = file_name.replace("WhatsApp Chat with ", "")
    group_name = os.path.splitext(group_name_with_extension)[0]
    
    # Check for duplicates like (1), (2) etc., and remove them
    group_name = re.sub(r'\(\d+\)$', '', group_name)
    print(group_name)

    # Special rule for 'SALES' team
    if team_name.lower() == 'sales':
        # Check for specific patterns after an underscore or the bracketed date format
        pattern = re.compile(r'.+?_(EDOOFA|edoofa|Edoofa|EA)|\(\d{2}_\d{2}\)')
        expected_format = 'yes' if pattern.search(group_name) else 'no'
    else:
        # Check for special characters in the first two parts
        parts = group_name.split()
        print(parts)
        if len(parts) >= 2 and not (re.search(r'[^A-Za-z0-9]', parts[0]) or re.search(r'[^A-Za-z0-9]', parts[1])):
            expected_format = 'yes'
        else:
            expected_format = 'no'

    return group_name, expected_format

def remove_duplicate_files(df):
    # Function to clean file names by removing the (number) suffix
    def clean_file_name(file_name):
        return re.sub(r'\(\d+\)\.txt$', '.txt', file_name)

    # Apply the cleaning function to each file name
    df['Cleaned File'] = df['Chat Name'].apply(clean_file_name)

    # Keep only the first occurrence of each cleaned file name
    df_cleaned = df.drop_duplicates(subset='Cleaned File', keep='first')

    # Drop the temporary 'Cleaned File' column
    df_cleaned.drop(columns=['Cleaned File'], inplace=True)

    return df_cleaned

def fetch_chat_data(date_directory):
    # Define the columns for the DataFrame
    columns = ['Date', 'Team', 'Person', 'Chat Name', 'Chat Group Name', 'Expected Format', 'File Size']
    data = []

    # Iterate through each 'Date' directory
    for date_folder in os.listdir(date_directory):
        date_path = os.path.join(date_directory, date_folder)
        if os.path.isdir(date_path):
            # Iterate through each 'Team' subdirectory
            for team_folder in os.listdir(date_path):
                team_path = os.path.join(date_path, team_folder)
                if os.path.isdir(team_path):
                    # Iterate through each 'Person' subdirectory
                    for person_folder in os.listdir(team_path):
                        person_path = os.path.join(team_path, person_folder)
                        if os.path.isdir(person_path):
                            # Process each chat file in the 'Person' subdirectory
                            for file in os.listdir(person_path):
                                if file.endswith('.txt'):
                                    file_path = os.path.join(person_path, file)
                                    file_size = os.path.getsize(file_path)
                                    chat_group_name, expected_format = parse_chat_group_name(file, team_folder)
                                    data.append([date_folder, team_folder, person_folder, file, chat_group_name, expected_format, file_size])

    # Debugging: Check the first few entries of the data list
    print("First few entries of data list:", data[:5])

    # Create a DataFrame from the data list
    df = pd.DataFrame(data, columns=columns)

    # Debugging: Print column names to confirm
    print("DataFrame columns:", df.columns)
    return df


# Replace 'your_date_directory_path' with the path to the 'Date' directory
date_directory = 'C:\\Users\\maurice\\Downloads\\drive-download-20231129T124901Z-001'
chat_data_df = fetch_chat_data(date_directory)
chat_data_df = remove_duplicate_files(chat_data_df)


# Display the DataFrame
#chat_data_df.head(10)

