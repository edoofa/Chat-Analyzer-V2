import os
import pandas as pd
import datetime
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Function to list all chat files in the directory structure
def list_chat_files(date_directory):
    chat_files = []
    for date_folder in os.listdir(date_directory):
        date_path = os.path.join(date_directory, date_folder)
        if os.path.isdir(date_path):
            for team_folder in os.listdir(date_path):
                team_path = os.path.join(date_path, team_folder)
                if os.path.isdir(team_path):
                    for person_folder in os.listdir(team_path):
                        person_path = os.path.join(team_path, person_folder)
                        if os.path.isdir(person_path):
                            for file in os.listdir(person_path):
                                if file.endswith('.txt'):
                                    chat_files.append(os.path.join(person_path, file))
    return chat_files

def parse_chat_file(file_path, expected_date_minus_one, person_name):
    chat_data = []
    last_non_person_time = None
    date_pattern = re.compile(r'^\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2}\s?[APMapm]{2} - ')

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    current_message = ""

    for line in lines:
        if date_pattern.match(line):
            if current_message:
                chat_data.extend(process_line(current_message, expected_date_minus_one, person_name, last_non_person_time))
                last_non_person_time = update_last_non_person_time(chat_data, last_non_person_time)
            current_message = line.rstrip()
        else:
            if current_message:
                current_message += " " + line.strip()
    if current_message:
        chat_data.extend(process_line(current_message, expected_date_minus_one, person_name, last_non_person_time))

    return chat_data

def process_line(line, expected_date_minus_one, person_name, last_non_person_time):
    message_match = re.match(r'(\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2}\s?[APMapm]{2}) - (.*?): (.*)', line)
    if message_match:
        date_time_str, sender, message = message_match.groups()
        try:
            date_time = pd.to_datetime(date_time_str, format='%d/%m/%y, %I:%M %p', errors='coerce')
        except ValueError:
            return []

        if date_time is pd.NaT or date_time.date() != expected_date_minus_one:
            return []

        message_type = 'person' if sender == person_name else 'other'
        delay = calculate_delay(date_time, last_non_person_time, message_type)
        return [(date_time, sender, message_type, delay)]
    else:
        return []

def update_last_non_person_time(chat_data, last_non_person_time):
    if chat_data and chat_data[-1][2] == 'other':
        return chat_data[-1][0]
    return last_non_person_time

def calculate_delay(current_time, last_non_person_time, message_type):
    if message_type == 'person' and last_non_person_time:
        diff = current_time - last_non_person_time
        return diff.total_seconds() > 900  # 15 minutes in seconds
    return False


def create_template_dataframe():
    times = [datetime.datetime(2000, 1, 1, 0, 0) + datetime.timedelta(minutes=1 * i) for i in range(1440)]
    intervals = [time.strftime('%I:%M %p') for time in times]
    df = pd.DataFrame(index=intervals)
    return df

def populate_dataframe(df, parsed_data, start_column_index):
    new_columns = {}

    for entry in parsed_data:
        date_time, sender, message_type, delay = entry
        interval_index = min((date_time.hour * 60 + date_time.minute) // 1, 1439)
        interval = df.index[interval_index]

        if start_column_index not in new_columns:
            new_columns[start_column_index] = pd.Series(0, index=df.index)  # For 'person'
        if start_column_index + 1 not in new_columns:
            new_columns[start_column_index + 1] = pd.Series(0, index=df.index)  # For 'other'
        if start_column_index + 2 not in new_columns:
            new_columns[start_column_index + 2] = pd.Series(False, index=df.index)  # For delay column

        if message_type == 'person':
            new_columns[start_column_index].at[interval] = 1
        elif message_type == 'other':
            new_columns[start_column_index + 1].at[interval] = 1

        new_columns[start_column_index + 2].at[interval] = delay  # Set delay flag

    df = pd.concat([df, pd.DataFrame(new_columns)], axis=1)
    return df, start_column_index + 3

def process_person_chats(chat_files):
    dataframes = {}
    for file in chat_files:
        parts = file.split(os.sep)
        date_folder, person = parts[-4], parts[-2]

        try:
            folder_date = pd.to_datetime(date_folder, format='%Y-%m-%d').date()
        except ValueError:
            continue

        expected_date_minus_one = folder_date - datetime.timedelta(days=1)
        key = f"{folder_date.strftime('%Y-%m-%d')}_{person}"

        if key not in dataframes:
            dataframes[key] = create_template_dataframe()
            start_column_index = 0
        else:
            if not dataframes[key].columns.empty:
                start_column_index = max(dataframes[key].columns) + 1
            else:
                start_column_index = 0

        parsed_data = parse_chat_file(file, expected_date_minus_one, person)
        dataframes[key], start_column_index = populate_dataframe(dataframes[key], parsed_data, start_column_index)

    return dataframes


def create_graphs(df, person_identifier, base_directory):
    # Splitting person_identifier to adjust the date
    folder_date_str, person_name = person_identifier.split('_')
    folder_date = pd.to_datetime(folder_date_str).date() - datetime.timedelta(days=1)
    adjusted_date_str = folder_date.strftime('%Y-%m-%d')
    adjusted_person_identifier = f"{adjusted_date_str}_{person_name}"

    graph_directory = os.path.join(base_directory, "Graphs")
    os.makedirs(graph_directory, exist_ok=True)

    # Sum the values for 'person' and 'other' messages for each minute
    person_chat_activity = df.iloc[:, 0::3].sum(axis=1)
    other_chat_activity = df.iloc[:, 1::3].sum(axis=1)
    
    # Find the first and last non-zero indices for chats
    non_zero_indices = person_chat_activity[person_chat_activity > 0].index
    first_chat_time = non_zero_indices[0] if not non_zero_indices.empty else df.index[0]
    last_chat_time = non_zero_indices[-1] if not non_zero_indices.empty else df.index[-1]

    # Creating the plot
    fig, ax = plt.subplots(figsize=(30, 10))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.xaxis.label.set_color('black')
    ax.yaxis.label.set_color('black')
    ax.title.set_color('black')
    ax.tick_params(axis='x', colors='black')
    ax.tick_params(axis='y', colors='black')

    # Plot the bar for 'person' messages
    ax.bar(df.index, person_chat_activity, color='lime', width=2, label='Counselor')

    # Plot for 'other' messages
    ax.plot(df.index, other_chat_activity, color='darkgreen', linestyle=':', label='Student')

    # Draw lines for the axes
    ax.axhline(0, color='black', linewidth=3)
    ax.axvline(first_chat_time, color='white', linewidth=3)

    # Rotate x-axis labels and increase label font sizes
    plt.xticks(rotation=90, fontsize=12)
    plt.yticks(np.arange(0, 11, 1), fontsize=12)

    # Set x-axis and y-axis limits and locators
    ax.set_xlim(first_chat_time, last_chat_time)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(96))
    max_activity = max(person_chat_activity.max(), other_chat_activity.max())
    ax.set_ylim(0, 11)

    # Setting labels and title
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Number of Chats', fontsize=12)
    ax.set_title(f'Chat Activity for {adjusted_person_identifier}', fontsize=14)

    # Setting the legend
    legend = ax.legend(facecolor='lightgray', edgecolor='black', fontsize=12, fancybox=True)
    for text in legend.get_texts():
        text.set_color('black')
        text.set_weight('bold')

    # Saving the graph
    graph_file_name = f"{adjusted_person_identifier}.png"
    plt.savefig(os.path.join(graph_directory, graph_file_name), format='png', dpi=300, bbox_inches='tight')
    print(f"Graph saved as {graph_file_name}")

    plt.close(fig)



# Main script
date_directory = "D:\\Github\\Chat-Analyzer-V2\\Chat Folder from Drive\\2024-01-03-20240103T025503Z-001"
chat_files = list_chat_files(date_directory)
person_dataframes = process_person_chats(chat_files)

for person_identifier, df in person_dataframes.items():
    create_graphs(df, person_identifier, date_directory)