import ctypes
import time

# Load the DLL
hikvision_sdk = ctypes.CDLL('lib/HCNetSDK.dll')

# Initialize the SDK
if hikvision_sdk.NET_DVR_Init() == 0:
    print("SDK initialization failed")
    exit()

# Set the connection time and retry times
hikvision_sdk.NET_DVR_SetConnectTime(2000, 1)
hikvision_sdk.NET_DVR_SetReconnect(10000, True)

# Define login parameters structure
class NET_DVR_USER_LOGIN_INFO(ctypes.Structure):
    _fields_ = [
        ("sDeviceAddress", ctypes.c_char * 129),
        ("byUseTransport", ctypes.c_byte),
        ("wPort", ctypes.c_ushort),
        ("sUserName", ctypes.c_char * 64),
        ("sPassword", ctypes.c_char * 64),
        ("bUseAsynLogin", ctypes.c_int),
        ("byRes2", ctypes.c_byte * 128),
        ("pUser", ctypes.c_void_p),
        ("cbLoginResult", ctypes.c_void_p),
        ("byRes3", ctypes.c_byte * 128)
    ]

# Define device information structure
class NET_DVR_DEVICEINFO_V40(ctypes.Structure):
    _fields_ = [
        ("struDeviceV30", ctypes.c_byte * 236),
        ("bySupportLock", ctypes.c_byte),
        ("byRetryLoginTime", ctypes.c_byte),
        ("byPasswordLevel", ctypes.c_byte),
        ("byProxyType", ctypes.c_byte),
        ("dwSurplusLockTime", ctypes.c_uint),
        ("byCharEncodeType", ctypes.c_byte),
        ("byRes2", ctypes.c_byte * 243)
    ]

# Define the access control event structure
class NET_DVR_ACS_EVENT_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_uint),
        ("byCardNo", ctypes.c_char * 32),
        ("byCardType", ctypes.c_byte),
        ("byWhiteListNo", ctypes.c_byte),
        ("byReportChannel", ctypes.c_byte),
        ("byCardReaderKind", ctypes.c_byte),
        ("dwCardReaderNo", ctypes.c_uint),
        ("dwDoorNo", ctypes.c_uint),
        ("dwVerifyNo", ctypes.c_uint),
        ("dwAlarmInNo", ctypes.c_uint),
        ("dwAlarmOutNo", ctypes.c_uint),
        ("dwCaseSensorNo", ctypes.c_uint),
        ("dwRs485No", ctypes.c_uint),
        ("dwMultiCardGroupNo", ctypes.c_uint),
        ("wAccessChannel", ctypes.c_ushort),
        ("byDeviceNo", ctypes.c_byte),
        ("byDistractControlNo", ctypes.c_byte),
        ("dwEmployeeNo", ctypes.c_uint),
        ("wLocalControllerID", ctypes.c_ushort),
        ("byInternetAccess", ctypes.c_byte),
        ("byType", ctypes.c_byte),
        ("byMACAddr", ctypes.c_byte * 6),
        ("bySwipeCardType", ctypes.c_byte),
        ("byRes2", ctypes.c_byte * 3),
        ("dwSerialNo", ctypes.c_uint),
        ("byChannelControllerID", ctypes.c_byte),
        ("byChannelControllerLampID", ctypes.c_byte),
        ("byChannelControllerIRAdaptorID", ctypes.c_byte),
        ("byChannelControllerIREmitterID", ctypes.c_byte),
        ("dwRecordChannelNum", ctypes.c_uint),
        ("byUserType", ctypes.c_byte),
        ("byCurrentVerifyMode", ctypes.c_byte),
        ("byEmployeeNoString", ctypes.c_char * 32),
        ("byRes", ctypes.c_byte * 64)
    ]

# Define the callback function
def fMessageCallback(dwCommand, lpBuffer, dwBufLen, pUser):
    print('here')
    if dwCommand == 0x5002:  # ACS event command
        event_info = ctypes.cast(lpBuffer, ctypes.POINTER(NET_DVR_ACS_EVENT_INFO)).contents
        card_no = event_info.byCardNo.decode('utf-8').strip('\x00')
        door_no = event_info.dwDoorNo
        event_type = event_info.byType
        verify_mode = event_info.byCurrentVerifyMode

        if event_type == 1:  # Card swipe
            print(f"Card No: {card_no}, Door No: {door_no}, Event Type: Card Swipe")
        elif event_type == 2:  # Password entry
            print(f"Password entry at Door No: {door_no}")
        elif event_type == 3:  # Face recognition
            print(f"Face recognition at Door No: {door_no}")
        elif event_type == 4:  # Fingerprint recognition
            print(f"Fingerprint recognition at Door No: {door_no}")
        elif event_type == 5:  # Button click
            print(f"Button click at Door No: {door_no}")
        else:
            print(f"Other event type {event_type} at Door No: {door_no}")

# Define the callback function type
MESSAGE_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)

# Set the callback function
callback = MESSAGE_CALLBACK(fMessageCallback)
hikvision_sdk.NET_DVR_SetDVRMessageCallBack_V30(callback, None)

# Fill in login parameters
login_info = NET_DVR_USER_LOGIN_INFO()
login_info.sDeviceAddress = b'10.0.0.115'
login_info.wPort = 8000
login_info.sUserName = b'admin'
login_info.sPassword = b'rFERNANDES18'

# Prepare device information structure
device_info = NET_DVR_DEVICEINFO_V40()

# Login to the device
user_id = hikvision_sdk.NET_DVR_Login_V40(ctypes.byref(login_info), ctypes.byref(device_info))
if user_id < 0:
    print("Login failed")
    hikvision_sdk.NET_DVR_Cleanup()
    exit()

print("Login successful")

# Run the application (keep it running to receive events)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

# Logout from the device
hikvision_sdk.NET_DVR_Logout(user_id)

# Clean up the SDK resources
hikvision_sdk.NET_DVR_Cleanup()
