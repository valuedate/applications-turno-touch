import requests
from requests.auth import HTTPDigestAuth

# Hikvision device information
hikvision_ip = "192.168.68.117"  # Replace with your Hikvision device IP
username = "admin"              # Replace with your username
password = "qwerty12"      # Replace with your password

# API URL for alert stream
url = f"http://{hikvision_ip}/ISAPI/Event/notification/alertStream"

# Start a session to maintain connection
session = requests.Session()

try:
    # Send a request to the alert stream with digest authentication
    with session.get(url, auth=HTTPDigestAuth(username, password), stream=True, timeout=10) as response:
        if response.status_code == 200:
            print("Connected to alert stream.")
            # Stream the event data line by line
            for line in response.iter_lines():
                if line:
                    # Decode and print each line of event data (assuming it's in XML or JSON format)
                    decoded_line = line.decode('utf-8')
                    print(decoded_line)
        else:
            print(f"Failed to connect, status code: {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"Error occurred: {e}")
