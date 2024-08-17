#!/usr/bin/env python3
import requests
import json
from requests.auth import HTTPDigestAuth
from email import message_from_bytes
from email.policy import default
import chardet
import os
import time
from datetime import datetime
import configparser
import logging


# Directory to save images
IMAGE_SAVE_DIR = 'saved_images'

# Ensure the directory exists
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

# Camera credentials and IP
#CAMERA_IP = '10.0.0.115'  # Replace with your camera's IP
#CAMERA_IP = '10.0.0.73'  # Replace with your camera's IP
#CAMERA_IP = '192.168.68.155'  # Replace with your camera's IP
#USERNAME = 'admin'  # Replace with your camera's username
#PASSWORD = 'rFERNANDES18'  # Replace with your camera's password
#PASSWORD = 'qwerty12'  # Replace with your camera's password


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

# Function to get events
def get_events(ip_address, ip_user, ip_pass, turno_api, token, lock_file_path, save_photos, debug_level):
    try:
        # hikvision connection
        EVENTS_API_URL = f'http://{ip_address}/ISAPI/Event/notification/alertStream'

        # Send the request to the camera
        response = requests.get(EVENTS_API_URL, auth=HTTPDigestAuth(ip_user, ip_pass), stream=True)

        # Check if the request was successful
        if response.status_code == 200:
            print("Connected to the event stream. Listening for events...")
            loop_count = 0
            buffer = b""
            for chunk in response.iter_content(chunk_size=4096):
                loop_count += 1
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                log_message = f"{current_time} Loop number: {loop_count}"
                print(log_message)
                logging.info(log_message)

                if os.path.exists(lock_file_path):
                    logging.info("Lock file found. Ending loop.")
                    print("Lock file found. Ending loop.")
                    break

                buffer += chunk
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
            print(f"Failed to connect to event stream. Status code: {response.status_code}")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def process_mime_part(part, turno_api, token):
    msg = message_from_bytes(part, policy=default)

    #----------------------------
    # Split headers and body
    try:
        headers, body = mime_part.split(b'\r\n\r\n', 1)
    except ValueError:
        # If split fails, the MIME part is likely incomplete
        print("Incomplete MIME part received, skipping...")
        return

    headers_str = headers.decode('utf-8', errors='ignore')

    # Check the content type and handle accordingly
    if 'Content-Type: application/json' in headers_str:
        try:
            event = json.loads(body.decode('utf-8', errors='ignore'))
            print("Event Received (JSON):")
            print(json.dumps(event, indent=4))
        except json.JSONDecodeError:
            print("Received malformed JSON event:")
            print(body.decode('utf-8', errors='ignore'))
    elif 'Content-Type: image/jpeg' in headers_str:
        filename = "unnamed.jpg"
        for header in headers_str.split('\r\n'):
            if header.startswith("Content-Disposition"):
                disposition = header.split(';')
                for item in disposition:
                    if item.strip().startswith("filename="):
                        filename = item.split('=')[1].strip().strip('"')
        save_image(filename, body)
    else:
        print(f"Unhandled content type in headers: {headers_str}")
    #----------------------------
    content_type = part.get_content_type()
    if content_type == "application/json":
        event_data = part.get_payload(decode=True)
        # Detect encoding before attempting to load the JSON
        encoding = chardet.detect(event_data)['encoding']
        if encoding is None:
            encoding = 'utf-8'  # Default to utf-8 if detection fails


        try:
            #event = json.loads(event_data)
            event = json.loads(event_data.decode(encoding, errors='replace'))
            if event.get("eventType") != "videoloss":
                event_ip_address = event.get("ipAddress")
                date_time = event.get("dateTime")
                event_type = event.get("eventType")
                event_state = event.get("eventState")
                event_description = event.get("eventDescription")
                # Extract employeeNoString if exists
                access_controller_event = event.get("AccessControllerEvent", {})
                employee_card_no = access_controller_event.get("cardNo")
                employee_user_type = access_controller_event.get("userType")
                employee_no_string = access_controller_event.get("employeeNoString")

                #print('+++++++++++++++++++++++++++++++++++++++++++++++++')
                #print(access_controller_event)
                #print('+++++++++++++++++++++++++++++++++++++++++++++++++')
                #print(f"Employee Number: {employee_no_string}")

                #print(f"Event Type: {event_type}\nEvent State: {event_state}\nEvent Description: {event_description}")
                #print('------------------------------------------------------------------')
                #print(event)
                #print('------------------------------------------------------------------')
                if employee_no_string:
                    post_to_turno_api(turno_api, token, employee_no_string, event_ip_address, date_time)

        except json.JSONDecodeError:
            print("Received malformed JSON event:")
            print(f"Received data of content type {content_type}:")
            #print(event_data)
            image_data = part.get_payload(decode=True)
            # Handle the image data (e.g., save to file, process, etc.)
            print("Received image data of length:", len(image_data))
            # Save the image with a timestamp prefix
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_name = f"{timestamp}_event_image.jpg"
            with open(file_name, 'wb') as f:
                f.write(image_data)
            print(f"Received image data of length: {len(image_data)} and saved as {file_name}")
    elif content_type == "text/plain":
        other_data = part.get_payload(decode=True)
        # Extract JSON part from text/plain content
        json_start = other_data.find(b'{')
        if json_start != -1:
            json_data = other_data[json_start:]
            try:
                # Detect encoding and handle errors similarly
                encoding = chardet.detect(json_data)['encoding']
                if encoding is None:
                    encoding = 'utf-8'

                #event = json.loads(json_data)
                event = json.loads(json_data.decode(encoding, errors='replace'))
                if event.get("eventType") != "videoloss":
                    event_ip_address = event.get("ipAddress")
                    date_time = event.get("dateTime")
                    event_type = event.get("eventType")
                    event_state = event.get("eventState")
                    event_description = event.get("eventDescription")
                    # Extract employeeNoString if exists
                    access_controller_event = event.get("AccessControllerEvent", {})
                    employee_card_no = access_controller_event.get("cardNo")
                    employee_user_type = access_controller_event.get("userType")
                    employee_no_string = access_controller_event.get("employeeNoString")

                    #print('+++++++++++++++++++++++++++++++++++++++++++++++++')
                    #print(access_controller_event)
                    #print('+++++++++++++++++++++++++++++++++++++++++++++++++')
                    #print(f"Employee Number: {employee_no_string}")

                    #print(f"Event Type: {event_type}\nEvent State: {event_state}\nEvent Description: {event_description}")
                    #print('------------------------------------------------------------------')
                    #print(event)
                    #print('------------------------------------------------------------------')
                    if employee_no_string:
                        post_to_turno_api(turno_api, token,employee_no_string, event_ip_address, date_time)

                    # clear all variables
                    #employee_no_string = None

            except json.JSONDecodeError:
                print("Received malformed JSON event:")
                print(f"Received data of content type {content_type}:")
                image_data = part.get_payload(decode=True)
                # Handle the image data (e.g., save to file, process, etc.)
                print("Received image data of length:", len(image_data))
                # Save the image with a timestamp prefix
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f"{timestamp}_event_image.jpg"
                with open(file_name, 'wb') as f:
                    f.write(image_data)
                print(f"Received image data of length: {len(image_data)} and saved as {file_name}")
                #print(json_data)
        else:
            print(f"Received data of content type {content_type} without JSON content:")
            print(other_data)
    elif content_type == "image/jpeg":
        image_data = part.get_payload(decode=True)
        # Handle the image data (e.g., save to file, process, etc.)
        print("Received image data of length:", len(image_data))
        # Save the image with a timestamp prefix
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{timestamp}_event_image.jpg"
        with open(file_name, 'wb') as f:
            f.write(image_data)
        print(f"Received image data of length: {len(image_data)} and saved as {file_name}")
    else:
        # Handle other content types if necessary
        other_data = part.get_payload(decode=True)
        print(f"Received data of content type {content_type}:")
        #print(other_data)

def post_to_turno_api(turno_api, token, employee_no_string, event_ip_address, date_time):
    url = f"{turno_api}{token}"
    payload = {
        'employeeNoString': employee_no_string,
        'ipAddress': event_ip_address,
        'dateTime': date_time
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        if response.status_code == 200:
            print("Successfully posted to Turno API")
        else:
            print(f"Failed to post to Turno API. Status code: {response.status_code}")
            #print(response.text)
    except requests.exceptions.RequestException as e:
        #print('exception')
        print(f"Error posting to Turno API: {e}")

# Function to save image data to a file
def save_image(filename, image_data):
    file_path = os.path.join(IMAGE_SAVE_DIR, filename)
    with open(file_path, 'wb') as image_file:
        image_file.write(image_data)
    print(f"Image saved as: {file_path}")

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')  # Replace with the actual path to the config file

    loop_count = int(config['settings']['loop_count'])
    lock_file_path = config['settings']['lock_file_path']
    ip_address = config['settings']['ip_address']
    ip_user = config['settings']['user']
    ip_pass = config['settings']['pass']
    turno_api = config['settings']['turno_api']
    token = config['settings']['token']
    save_photos = config['settings']['save_photos']
    debug_level = config['settings']['debug_level']

    log_filename = setup_logging()
    logging.info(f"Starting new cycle. Log file: {log_filename}")

    get_events(ip_address, ip_user, ip_pass, turno_api, token, lock_file_path, save_photos, debug_level)


if __name__ == "__main__":
    #TODO faltam logs
    #TODO falta enviar imagem - necessário também alterar endpoint turno
    main()
