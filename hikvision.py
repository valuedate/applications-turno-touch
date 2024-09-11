#!/usr/bin/env python3
import requests
import json
from requests.auth import HTTPDigestAuth
from email import message_from_bytes
from email.policy import default
import chardet
import os
import signal
import sys
import time
from datetime import datetime
import configparser
import logging
import pyfiglet
import threading


# Directory to save images
IMAGE_SAVE_DIR = 'saved_images'

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
            time.sleep(60)  # Wait for 60 seconds
        except Exception as e:
            logging.error(f"Error during turno API ping: {e}")
            time.sleep(60)  # Wait for 60 seconds even in case of an error


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

        #EVENTS_API_URL = f'http://{ip_address}/ISAPI/Event/notification/alertStream'

        # Send the request to the camera with a timeout
        with session.get(url, auth=HTTPDigestAuth(ip_user, ip_pass), stream=True, timeout=999) as response:

            # Check if the request was successful
            if response.status_code == 200:
                print_with_timestamp("Connected to the event stream. Listening for events...")
                loop_count = 0
                buffer = b""
                last_chunk_time = time.time()

                for chunk in response.iter_content(chunk_size=4096):
                    current_time = time.time()

                    # Check if connection is still active by comparing time intervals
                    if current_time - last_chunk_time > 15:  # 15 seconds threshold
                        print_with_timestamp("No data received for 15 seconds. Reconnecting...")
                        logging.warning("No data received for 15 seconds. Reconnecting...")
                        response.close()
                        break

                    loop_count += 1
                    log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} Loop number: {loop_count}"
                    print_with_timestamp(log_message)
                    logging.info(log_message)

                    if os.path.exists(lock_file_path):
                        logging.info("Lock file found. Ending loop.")
                        print_with_timestamp("Lock file found. Ending loop.")
                        response.close()
                        return  # Exit function when lock file is found

                    buffer += chunk
                    last_chunk_time = current_time  # Reset last chunk time

                    while b"--MIME_boundary" in buffer:
                        # Split the buffer by the MIME boundary
                        parts = buffer.split(b"--MIME_boundary", 1)
                        buffer = parts[1]
                        mime_part = parts[0]

                        if mime_part:
                            # Parse the MIME part
                            msg = message_from_bytes(mime_part, policy=default)
                            if msg.is_multipart():
                                for part in msg.iter_parts():
                                    process_mime_part(part, turno_api, token)
                                    logging.info(part)
                            else:
                                process_mime_part(msg, turno_api, token)
                                logging.info(msg)

            else:
                print_with_timestamp(f"Failed to connect to event stream. Status code: {response.status_code}")
                print_with_timestamp(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")




def process_mime_part(part, turno_api, token):
    content_type = part.get_content_type()
    print_with_timestamp(content_type)
    if content_type == "application/json":
        #print_with_timestamp('application json')
        event_data = part.get_payload(decode=True)
        try:
            # Detect encoding before attempting to load the JSON
            encoding = chardet.detect(event_data)['encoding']
            if encoding is None:
                encoding = 'utf-8'  # Default to utf-8 if detection fails

            event = json.loads(event_data.decode(encoding, errors='replace'))
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
            print_with_timestamp("Received malformed JSON event")
            #print(event_data)

    elif content_type == "text/plain":
        other_data = part.get_payload(decode=True)
        json_start = other_data.find(b'{')
        if json_start != -1:
            json_data = other_data[json_start:]
            try:
                # Detect encoding and handle errors similarly
                encoding = chardet.detect(json_data)['encoding']
                if encoding is None:
                    encoding = 'utf-8'

                event = json.loads(json_data.decode(encoding, errors='replace'))
                if event.get("eventType") != "videoloss":
                    event_ip_address = event.get("ipAddress")
                    date_time = event.get("dateTime")
                    event_type = event.get("eventType")
                    event_state = event.get("eventState")
                    event_description = event.get("eventDescription")
                    access_controller_event = event.get("AccessControllerEvent", {})
                    employee_no_string = access_controller_event.get("employeeNoString")

                    if employee_no_string:
                        post_to_turno_api(turno_api, token, employee_no_string, event_ip_address, date_time)

            except json.JSONDecodeError:
                print_with_timestamp("Received malformed JSON event:")
                print_with_timestamp(json_data)
        else:
            print_with_timestamp(f"Received data of content type {content_type} without JSON content:")
            #print(other_data)
    elif content_type == "image/jpeg":
        image_data = part.get_payload(decode=True)
        print_with_timestamp("Received image data of length:", len(image_data))
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{timestamp}_event_image.jpg"
        with open(file_name, 'wb') as f:
            f.write(image_data)
        print_with_timestamp(f"Received image data of length: {len(image_data)} and saved as {file_name}")
    else:
        other_data = part.get_payload(decode=True)
        print_with_timestamp(f"Received data of content type {content_type}:")
        #print(other_data)

def post_to_turno_api(turno_api, token, employee_no_string, event_ip_address, date_time):
    url = f"{turno_api}{token}"
    payload = {
        'employeeNoString': employee_no_string,
        'ipAddress': event_ip_address,
        'dateTime': date_time
    }
    headers = {'Content-Type': 'application/json'}

    while True:
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            if response.status_code == 200:
                print_with_timestamp("Successfully posted {employee_no_string} to Turno API")
                break  # Exit the loop on success
            elif response.status_code == 404:
                print_with_timestamp(f"Post to Turno of {employee_no_string} received 404 error. Retrying in 10 seconds...")
                time.sleep(10)  # Wait for 10 seconds before retrying
            else:
                print_with_timestamp(f"Failed to post {employee_no_string} to Turno API. Status code: {response.status_code}")
                logging.info(f"Failed to post {employee_no_string} to Turno API. Status code: {response.status_code}")
                # Optionally, you can print the response text or log it
                # print_with_timestamp(response.text)
                break  # Exit the loop for any status code other than 404
        except requests.exceptions.RequestException as e:
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
        print_with_timestamp(f"Error pinging to Turno API: {e}")


# Function to save image data to a file
def save_image(filename, image_data):
    file_path = os.path.join(IMAGE_SAVE_DIR, filename)
    with open(file_path, 'wb') as image_file:
        image_file.write(image_data)
    print_with_timestamp(f"Image saved as: {file_path}")

def main():
    print('###############################')
    print_ascii_message('TURNO')
    print('###############################')
    print('####### www.turno.cloud #######')
    print('###############################')
    print('  on-prem to cloud interface')
    print('    developed by valuedate')
    print('###############################')
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
