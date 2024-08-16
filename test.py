#!/usr/bin/env python3
from hikvisionapi import Client

cam = Client('https://10.0.0.115', 'admin', 'rFERNANDES18')


# Dict response (default)
response = cam.System.deviceInfo(method='get')
# xml text response
response = cam.System.deviceInfo(method='get', present='text')

print(str(response))