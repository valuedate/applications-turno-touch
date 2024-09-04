#!/bin/bash
sleep 30 # Wait for 10 seconds to ensure network is up
chromium-browser --start-fullscreen --noerrdialogs --disable-infobars --kiosk https://www.turno24.com
