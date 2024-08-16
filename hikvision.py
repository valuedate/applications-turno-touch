#!/usr/bin/env python3
import ctypes
import os
import time

# Update LD_LIBRARY_PATH
os.environ['LD_LIBRARY_PATH'] = '/home/turno/lib:' + os.environ.get('LD_LIBRARY_PATH', '')

# Load the Hikvision SDK shared library for Linux
HCNetSDK = ctypes.CDLL('/home/turno/lib/libhcnetsdk.so')

# Define constants and structures from the SDK
NET_DVR_LOGIN_V30 = 1
NET_DVR_DEVICEINFO_V30 = 2
NET_DVR_PLAYBACKCONTROL = 3

# Initialize the SDK
HCNetSDK.NET_DVR_Init()

# Define a device info structure
class NET_DVR_DEVICEINFO_V30(ctypes.Structure):
    _fields_ = [
        ("sSerialNumber", ctypes.c_byte * 48),
        ("byAlarmInPortNum", ctypes.c_byte),
        ("byAlarmOutPortNum", ctypes.c_byte),
        ("byDiskNum", ctypes.c_byte),
        ("byDVRType", ctypes.c_byte),
        ("byChanNum", ctypes.c_byte),
        ("byStartChan", ctypes.c_byte),
        ("byAudioChanNum", ctypes.c_byte),
        ("byIPChanNum", ctypes.c_byte),
        ("byZeroChanNum", ctypes.c_byte),
        ("byMainProto", ctypes.c_byte),
        ("bySubProto", ctypes.c_byte),
        ("bySupport", ctypes.c_byte),
        ("bySupport1", ctypes.c_byte),
        ("bySupport2", ctypes.c_byte),
        ("wDevType", ctypes.c_ushort),
        ("bySupport3", ctypes.c_byte),
        ("byMultiStreamProto", ctypes.c_byte),
        ("byStartDChan", ctypes.c_byte),
        ("byStartDTalkChan", ctypes.c_byte),
        ("byHighDChanNum", ctypes.c_byte),
        ("bySupport4", ctypes.c_byte),
        ("byLanguageType", ctypes.c_byte),
        ("byVoiceInChanNum", ctypes.c_byte),
        ("byStartVoiceInChanNo", ctypes.c_byte),
        ("bySupport5", ctypes.c_byte),
        ("bySupport6", ctypes.c_byte),
        ("byMirrorChanNum", ctypes.c_byte),
        ("wStartMirrorChanNo", ctypes.c_ushort),
        ("byRes2", ctypes.c_byte * 2),
        ("dwSupportAbility", ctypes.c_uint),
        ("byRes3", ctypes.c_byte * 2)
    ]

def capture_snapshot(ip, port, username, password, channel, filename):
    # Login to the device
    device_info = NET_DVR_DEVICEINFO_V30()
    user_id = HCNetSDK.NET_DVR_Login_V30(
        ip.encode('utf-8'),
        port,
        username.encode('utf-8'),
        password.encode('utf-8'),
        ctypes.byref(device_info)
    )

    if user_id < 0:
        print("Login failed")
        return
    else:
        print("Login successful")

    # Capture a snapshot
    command = 3520  # NET_DVR_CAPTURE_JPEG_PIC_WITHOUT_RES
    jpeg_param = ctypes.create_string_buffer(40)  # Adjust size if needed
    HCNetSDK.NET_DVR_SetCaptureJPEGConfig(user_id, channel, command, ctypes.byref(jpeg_param))
    HCNetSDK.NET_DVR_CaptureJPEGPicture(user_id, channel, filename.encode('utf-8'))

    # Logout and clean up
    HCNetSDK.NET_DVR_Logout(user_id)
    HCNetSDK.NET_DVR_Cleanup()

def main():
    parser = argparse.ArgumentParser(description="Capture a snapshot from a Hikvision camera")
    parser.add_argument('--ip', required=True, help="IP address of the Hikvision device")
    parser.add_argument('--port', type=int, default=8000, help="Port of the Hikvision device")
    parser.add_argument('--username', required=True, help="Username for the Hikvision device")
    parser.add_argument('--password', required=True, help="Password for the Hikvision device")
    parser.add_argument('--channel', type=int, default=1, help="Channel number to capture the snapshot from")
    parser.add_argument('--filename', default="snapshot.jpg", help="Filename to save the snapshot")

    args = parser.parse_args()
    capture_snapshot(args.ip, args.port, args.username, args.password, args.channel, args.filename)

if __name__ == "__main__":
    main()