import requests
import json
from requests.auth import HTTPDigestAuth
from email import message_from_bytes
from email.policy import default
from datetime import datetime

# Camera credentials and IP
#CAMERA_IP = '10.0.0.115'  # Replace with your camera's IP
#CAMERA_IP = '10.0.0.73'  # Replace with your camera's IP
CAMERA_IP = '192.168.68.155'  # Replace with your camera's IP
USERNAME = 'admin'  # Replace with your camera's username
#PASSWORD = 'rFERNANDES18'  # Replace with your camera's password
PASSWORD = 'qwerty12'  # Replace with your camera's password

# TURNO Endpoint
TURNO_API_URL = 'http://127.0.0.1:8001/api/v1/timesheets/?token='
TURNO_TOKEN = '9dfc5d78-c909-482a-bf51-4e96111b4375'
# API Endpoint for event notifications
EVENTS_API_URL = f'http://{CAMERA_IP}/ISAPI/Event/notification/alertStream'

# Function to get events
def get_events():
    try:
        # Send the request to the camera
        response = requests.get(EVENTS_API_URL, auth=HTTPDigestAuth(USERNAME, PASSWORD), stream=True)

        # Check if the request was successful
        if response.status_code == 200:
            print("Connected to the event stream. Listening for events...")
            buffer = b""
            for chunk in response.iter_content(chunk_size=4096):
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
                                process_mime_part(part)
                        else:
                            process_mime_part(msg)
        else:
            print(f"Failed to connect to event stream. Status code: {response.status_code}")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def process_mime_part(part):
    content_type = part.get_content_type()
    if content_type == "application/json":
        event_data = part.get_payload(decode=True)
        try:
            event = json.loads(event_data)
            if event.get("eventType") != "videoloss":
                ip_address = event.get("ipAddress")
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
                print('------------------------------------------------------------------')
                print(event)
                print('------------------------------------------------------------------')
                if employee_no_string:
                    post_to_turno_api(employee_no_string, ip_address, date_time)

        except json.JSONDecodeError:
            print("Received malformed JSON event:")
            print(event_data)
    elif content_type == "text/plain":
        other_data = part.get_payload(decode=True)
        # Extract JSON part from text/plain content
        json_start = other_data.find(b'{')
        if json_start != -1:
            json_data = other_data[json_start:]
            try:
                event = json.loads(json_data)
                if event.get("eventType") != "videoloss":
                    ip_address = event.get("ipAddress")
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
                    print('------------------------------------------------------------------')
                    print(event)
                    print('------------------------------------------------------------------')
                    if employee_no_string:
                        post_to_turno_api(employee_no_string, ip_address, date_time)

                    # clear all variables
                    #employee_no_string = None

            except json.JSONDecodeError:
                print("Received malformed JSON event:")
                print(json_data)
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
        print(other_data)

def post_to_turno_api(employee_no_string, ip_address, date_time):
    url = f"{TURNO_API_URL}{TURNO_TOKEN}"
    payload = {
        'employeeNoString': employee_no_string,
        'ipAddress': ip_address,
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
        print('exception')
        #print(f"Error posting to Turno API: {e}")

if __name__ == "__main__":
    get_events()
