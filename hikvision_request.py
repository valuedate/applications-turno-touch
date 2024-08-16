import requests
import json
from requests.auth import HTTPDigestAuth
from email import message_from_bytes
from email.policy import default

# Camera credentials and IP
#CAMERA_IP = '192.168.1.131'  # Replace with your camera's IP
CAMERA_IP = '10.0.0.115'
USERNAME = 'admin'  # Replace with your camera's username
#PASSWORD = 'qwerty12'  # Replace with your camera's password
PASSWORD = 'rFERNANDES18'

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
                                content_type = part.get_content_type()
                                if content_type == "application/json":
                                    event_data = part.get_payload(decode=True)
                                    try:
                                        event = json.loads(event_data)
                                        print("Event Received (JSON):")
                                        print(json.dumps(event, indent=4))
                                    except json.JSONDecodeError:
                                        print("Received malformed JSON event:")
                                        print(event_data)
                                elif content_type == "image/jpeg":
                                    image_data = part.get_payload(decode=True)
                                    # Handle the image data (e.g., save to file, process, etc.)
                                    print("Received image data of length:", len(image_data))
                                else:
                                    # Handle other content types if necessary
                                    other_data = part.get_payload(decode=True)
                                    print(f"Received data of content type {content_type}:")
                                    print(other_data)
                        else:
                            content_type = msg.get_content_type()
                            if content_type == "application/json":
                                event_data = msg.get_payload(decode=True)
                                try:
                                    event = json.loads(event_data)
                                    #print("Event Received (JSON):")
                                    print(json.dumps(event, indent=4))
                                except json.JSONDecodeError:
                                    #print("Received malformed JSON event:")
                                    print(event_data)
                            elif content_type == "image/jpeg":
                                image_data = msg.get_payload(decode=True)
                                # Handle the image data (e.g., save to file, process, etc.)
                                print("Received image data of length:", len(image_data))
                            else:
                                # Handle other content types if necessary
                                other_data = msg.get_payload(decode=True)
                                print(f"Received data of content type {content_type}:")
                                print('here')
                                print(other_data)
        else:
            print(f"Failed to connect to event stream. Status code: {response.status_code}")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    get_events()