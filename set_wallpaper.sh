#!/bin/bash

# Script to download wallpaper and set as desktop background
# For Raspberry Pi OS

# Enable debugging to help troubleshoot
set -x

# Create Downloads directory if it doesn't exist
DOWNLOAD_DIR="$HOME/Downloads"
mkdir -p "$DOWNLOAD_DIR"

# Set wallpaper filename and path
WALLPAPER_URL="https://www.turno.pt/static/img/wallpaper.jpg"
WALLPAPER_FILE="$DOWNLOAD_DIR/wallpaper.jpg"

echo "Downloading wallpaper from $WALLPAPER_URL..."

# Download the wallpaper using curl or wget (whichever is available)
if command -v curl &> /dev/null; then
    curl -L -o "$WALLPAPER_FILE" "$WALLPAPER_URL" || { echo "curl download failed"; exit 1; }
elif command -v wget &> /dev/null; then
    wget --no-check-certificate -O "$WALLPAPER_FILE" "$WALLPAPER_URL" || { echo "wget download failed"; exit 1; }
else
    echo "Error: Neither curl nor wget is installed. Please install one of them."
    exit 1
fi

# Check if download was successful
if [ ! -f "$WALLPAPER_FILE" ]; then
    echo "Error: Failed to download wallpaper."
    exit 1
fi

# Check file size to ensure it's not empty or an error page
FILESIZE=$(stat -c%s "$WALLPAPER_FILE")
if [ "$FILESIZE" -lt 1000 ]; then
    echo "Warning: Downloaded file is suspiciously small ($FILESIZE bytes). It might not be a valid image."
    cat "$WALLPAPER_FILE" | head -n 20
else
    echo "Wallpaper downloaded to $WALLPAPER_FILE (Size: $FILESIZE bytes)"
fi

# Detect desktop environment
if [ -n "$DESKTOP_SESSION" ]; then
    echo "Detected desktop session: $DESKTOP_SESSION"
else
    echo "No DESKTOP_SESSION variable found, assuming LXDE/PIXEL"
fi

# Try multiple methods to set wallpaper
echo "Setting wallpaper as desktop background..."

# Method 1: pcmanfm (most common for Raspberry Pi OS)
if command -v pcmanfm &> /dev/null; then
    echo "Trying pcmanfm method..."
    pcmanfm --set-wallpaper="$WALLPAPER_FILE" || echo "pcmanfm method failed"
    # Alternative syntax
    pcmanfm --desktop --profile LXDE-pi --set-wallpaper="$WALLPAPER_FILE" || echo "Alternative pcmanfm method failed"
fi

# Method 2: GNOME settings
if command -v gsettings &> /dev/null; then
    echo "Trying gsettings method..."
    gsettings set org.gnome.desktop.background picture-uri "file://$WALLPAPER_FILE" || echo "gsettings method failed"
fi

# Method 3: feh (lightweight image viewer)
if command -v feh &> /dev/null; then
    echo "Trying feh method..."
    feh --bg-scale "$WALLPAPER_FILE" || echo "feh method failed"
else
    echo "feh not installed. Consider installing it: sudo apt-get install feh"
fi

# Method 4: Use the xfconf-query for XFCE
if command -v xfconf-query &> /dev/null; then
    echo "Trying xfconf-query method..."
    xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/last-image -s "$WALLPAPER_FILE" || echo "xfconf-query method failed"
fi

# Method 5: Directly modify the configuration file for LXDE desktop
LXDE_CONFIG_DIR="$HOME/.config/pcmanfm/LXDE-pi"
mkdir -p "$LXDE_CONFIG_DIR"
LXDE_CONFIG_FILE="$LXDE_CONFIG_DIR/desktop-items-0.conf"

if [ -f "$LXDE_CONFIG_FILE" ]; then
    echo "Modifying existing LXDE config file..."
    sed -i "s|wallpaper=.*|wallpaper=$WALLPAPER_FILE|g" "$LXDE_CONFIG_FILE"
else
    echo "Creating new LXDE config file..."
    cat > "$LXDE_CONFIG_FILE" << EOF
[*]
wallpaper_mode=stretch
wallpaper_common=0
wallpaper=$WALLPAPER_FILE
desktop_bg=#000000
desktop_fg=#ffffff
desktop_shadow=#000000
EOF
fi

# Make the change permanent by updating the autostart file
AUTOSTART_DIR="$HOME/.config/lxsession/LXDE-pi"
mkdir -p "$AUTOSTART_DIR"
AUTOSTART_FILE="$AUTOSTART_DIR/autostart"

# Check if autostart file exists, create it if not
if [ ! -f "$AUTOSTART_FILE" ]; then
    echo "Creating new autostart file..."
    cat > "$AUTOSTART_FILE" << EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
EOF
fi

# Add or update wallpaper setting in autostart file
if grep -q "@pcmanfm --set-wallpaper" "$AUTOSTART_FILE"; then
    # Replace existing wallpaper setting
    sed -i "s|@pcmanfm --set-wallpaper=.*|@pcmanfm --set-wallpaper=\"$WALLPAPER_FILE\"|g" "$AUTOSTART_FILE"
else
    # Add new wallpaper setting
    echo "@pcmanfm --set-wallpaper=\"$WALLPAPER_FILE\"" >> "$AUTOSTART_FILE"
fi

# Add feh to autostart as a fallback
if command -v feh &> /dev/null; then
    if ! grep -q "feh --bg-scale" "$AUTOSTART_FILE"; then
        echo "@feh --bg-scale \"$WALLPAPER_FILE\"" >> "$AUTOSTART_FILE"
    fi
fi

echo "Attempted to set wallpaper using multiple methods."
echo "If none worked, you may need to install additional software:"
echo "  sudo apt-get update"
echo "  sudo apt-get install feh pcmanfm"
echo "Done!"

# Disable debugging
set +x
