#!/usr/bin/env python3
import requests
import json
from requests.auth import HTTPDigestAuth
import os
import signal
import sys
import time
from datetime import datetime
import configparser
import logging
import pyfiglet
import threading
import re
import random


# Directory to save images
IMAGE_SAVE_DIR = 'saved_images'

# Define the boundary string for MIME parts
boundary = '--MIME_boundary'

# Ensure the directory exists
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)


# init logging
def setup_logging():
    # Create a log file with the start date of the cycle
    start_date = datetime.now().strftime('%Y-%m-%d_%H-%M')
    log_filename = f'logs/log_{start_date}.log'  # Replace with your desired log directory and filename

    # Set up logging configuration
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M'
    )
    return log_filename

def signal_handler(sig, frame):
    print_with_timestamp("CTRL+C detected. Exiting gracefully...")
    logging.info("CTRL+C detected. Exiting gracefully...")
    sys.exit(0)
#
def print_with_timestamp(message):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{current_time} - {message}")

# prettify messages
def print_ascii_message(message):
    #message = "Turno Touch interface by valuedate.io"
    ascii_art = pyfiglet.figlet_format(message)
    print(ascii_art)


def ping_turno_api_loop(turno_ping, token):
    while True:
        try:
            ping_turno_api(turno_ping, token)  # Call the ping_turno_api function
            time.sleep(300)  # Wait for 300 seconds
        except Exception as e:
            logging.error(f"Error during turno API ping: {e}")
            time.sleep(300)  # Wait for 300 seconds even in case of an error


def extract_content_and_json(text):
    # Extract only the main part of Content-Type (before the semicolon)
    content_type_match = re.search(r'Content-Type:\s*([^;]+)', text)
    content_type = content_type_match.group(1).strip() if content_type_match else None

    # Extract JSON content using another regular expression
    json_match = re.search(r'(\{.*\})', text, re.DOTALL)
    body = json.loads(json_match.group(1)) if json_match else None

    return content_type, body


# Function to get events
def get_events(ip_address, ip_user, ip_pass, turno_api, token, lock_file_path, save_photos, debug_level, turno_ping):
    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)

    logging.info(f"Connecting to: {ip_address}")
    print_with_timestamp(f"Connecting to: {ip_address}")

    # Start the ping_turno_api in a separate thread
    ping_thread = threading.Thread(target=ping_turno_api_loop, args=(turno_ping,token))
    ping_thread.daemon = True  # This ensures the thread will exit when the main program exits
    ping_thread.start()

    # API URL for alert stream
    url = f'http://{ip_address}/ISAPI/Event/notification/alertStream'

    # Start a session to maintain connection
    session = requests.Session()


    try:
        # Send the request to the camera with a timeout
        with session.get(url, auth=HTTPDigestAuth(ip_user, ip_pass), stream=True, timeout=999) as response:
            # check if theres a lock file
            if os.path.exists(lock_file_path):
                logging.info("Lock file found. Ending loop.")
                print_with_timestamp("Lock file found. Ending loop.")
                response.close()
                return  # Exit function when lock file is found

            # Check if the request was successful
            if response.status_code == 200:
                logging.info("Connected to the event stream. Listening for events...")
                print_with_timestamp("Connected to the event stream. Listening for events...")
                buffer = ''
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        buffer += decoded_line + '\n'

                        # Check if the buffer contains a complete MIME part (split by boundary)
                        if boundary in buffer:
                            # Split the buffer by the boundary
                            parts = buffer.split(boundary)

                            # Process each part except the last one (it's incomplete)
                            for part in parts[:-1]:
                                if part.strip():
                                    process_mime_part(part.strip(), turno_api, token)

                            # Keep the remaining incomplete part in the buffer
                            buffer = parts[-1]
            else:
                logging.error(f"Failed to connect, status code: {response.status_code}")
                print_with_timestamp(f"Failed to connect, status code: {response.status_code}")
                #loop_count = 0

    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {e}")
        print_with_timestamp(f"Error occurred: {e}")




def process_mime_part(part, turno_api, token):

    content_type, body = extract_content_and_json(part)

    if content_type == "application/json":

        event_data = body
        try:
            encoding = 'utf-8'  # Default to utf-8 if detection fails

            event = event_data #json.loads(event_data.decode(encoding, errors='replace'))
            if event.get("eventType") != "videoloss":
                event_ip_address = event.get("ipAddress")
                date_time = event.get("dateTime")
                event_type = event.get("eventType")
                event_state = event.get("eventState")
                event_description = event.get("eventDescription")
                access_controller_event = event.get("AccessControllerEvent", {})
                employee_no_string = access_controller_event.get("employeeNoString")

                if employee_no_string:
                    #print_with_timestamp('post to turno')
                    post_to_turno_api(turno_api, token, employee_no_string, event_ip_address, date_time)

        except json.JSONDecodeError:
            logging.error("Received malformed JSON event")
            print_with_timestamp("Received malformed JSON event")



    elif content_type == "image/jpeg":
        image_data = body
        print_with_timestamp("Received image data of length:", len(image_data))
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{timestamp}_event_image.jpg"
        with open(file_name, 'wb') as f:
            f.write(image_data)
        logging.info(f"Received image data of length: {len(image_data)} and saved as {file_name}")
        print_with_timestamp(f"Received image data of length: {len(image_data)} and saved as {file_name}")
    else:
        other_data = body
        logging.info(f"Received data of content type {content_type}")
        print_with_timestamp(f"Received data of content type {content_type}:")

def post_to_turno_api(turno_api, token, employee_no_string, event_ip_address, date_time):
    url = f"{turno_api}{token}"
    payload = {
        'employeeNoString': employee_no_string,
        'ipAddress': event_ip_address,
        'dateTime': date_time
    }
    headers = {'Content-Type': 'application/json'}

    max_retries = 8
    base_sleep_time = 5  # Base sleep time in seconds

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            if response.status_code == 200:
                logging.info(f"Successfully posted {employee_no_string} to Turno API")
                print_with_timestamp(f"Successfully posted {employee_no_string} to Turno API")
                break  # Exit the loop on success
            elif response.status_code == 404:
                print(response)
                logging.error(f"Post to Turno of {employee_no_string} received 404 error. User code doesn't exist in Turno")
                print_with_timestamp(f"Post to Turno of {employee_no_string} received 404 error. User code doesn't exist in Turno")
                break  # Exit the loop for 404 (user doesn't exist)
            else:
                print_with_timestamp(f"Failed to post {employee_no_string} to Turno API. Status code: {response.status_code}")
                logging.info(f"Failed to post {employee_no_string} to Turno API. Status code: {response.status_code}")
                sleep_time = random.uniform(base_sleep_time, base_sleep_time * attempt)  # Increase sleep time after each failure
                print_with_timestamp(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)  # Wait before retrying
        except requests.exceptions.RequestException as e:
            logging.error(f"Error posting to Turno API: {e}")
            print_with_timestamp(f"Error posting to Turno API: {e}")
            break  # Exit the loop on request exception


def ping_turno_api(turno_ping, token):
    url = f"{turno_ping}{token}"
    payload = {
        'token': token,
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        if response.status_code == 200:
            print_with_timestamp("Successfully ping to Turno API")
        else:
            print_with_timestamp(f"Failed to ping to Turno API. Status code: {response.status_code}")
            logging.info(f"Failed to ping to Turno API. Status code: {response.status_code}")
            # Optionally, you can print the response text or log it
            # print_with_timestamp(response.text)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error pinging to Turno API: {e}")
        print_with_timestamp(f"Error pinging to Turno API: {e}")


# Function to save image data to a file
def save_image(filename, image_data):
    file_path = os.path.join(IMAGE_SAVE_DIR, filename)
    with open(file_path, 'wb') as image_file:
        image_file.write(image_data)
    print_with_timestamp(f"Image saved as: {file_path}")

def main():
    print('##############################################################')
    print_ascii_message('TURNO')
    print('##############################################################')
    print('####################### www.turno.cloud ######################')
    print('##############################################################')
    print('                  on-prem to cloud interface')
    print('                    developed by valuedate')
    print('##############################################################')
    config = configparser.ConfigParser()
    config.read('config.ini')  # Replace with the actual path to the config file

    loop_count = int(config['settings']['loop_count'])
    lock_file_path = config['settings']['lock_file_path']
    ip_address = config['settings']['ip_address']
    ip_user = config['settings']['user']
    ip_pass = config['settings']['pass']
    turno_api = config['settings']['turno_api']
    turno_ping = config['settings']['turno_ping']
    token = config['settings']['token']
    save_photos = config['settings']['save_photos']
    debug_level = config['settings']['debug_level']

    log_filename = setup_logging()
    logging.info(f"Starting new cycle. Log file: {log_filename}")

    get_events(ip_address, ip_user, ip_pass, turno_api, token, lock_file_path, save_photos, debug_level, turno_ping)


if __name__ == "__main__":
    #TODO faltam logs
    #TODO falta enviar imagem - necessário também alterar endpoint turno
    main()
