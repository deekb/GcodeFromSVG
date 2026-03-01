import serial
import time

# -----------------------------
# User Config
# -----------------------------
PORT = "/dev/ttyUSB0"  # Change to your port (Windows: "COM3")
BAUDRATE = 115200
WAIT_AFTER_CONNECT = 2  # seconds

# -----------------------------
# Connect to GRBL
# -----------------------------
ser = serial.Serial(PORT, BAUDRATE, timeout=1)
time.sleep(WAIT_AFTER_CONNECT)
ser.write(b"\n")             # wake up GRBL
time.sleep(0.1)
ser.reset_input_buffer()      # clear startup junk

# -----------------------------
# Utility Functions
# -----------------------------
def send_command(cmd):
    """Send a command to GRBL and return response lines before 'ok'"""
    ser.write((cmd + "\n").encode())
    response = []
    while True:
        line = ser.readline().decode().strip()
        if line == "ok" or line == "":
            break
        response.append(line)
    return response

def read_all_settings():
    """Return a dictionary of all GRBL settings"""
    lines = send_command("$$")
    settings = {}
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
    return settings

def print_settings(settings):
    """Print settings nicely"""
    for key, val in sorted(settings.items(), key=lambda x: int(x[0][1:])):
        print(f"{key} = {val}")

def set_setting(key, value):
    """Set a single GRBL setting (key='$nnn', value=number)"""
    response = send_command(f"{key}={value}")
    print(f"Set {key} = {value} -> Response: {response}")

def get_acceleration(settings):
    """Return acceleration dictionary"""
    return {
        "X": float(settings.get("$120", 0)),
        "Y": float(settings.get("$121", 0)),
        "Z": float(settings.get("$122", 0))
    }

def get_speed(settings):
    """Return maximum speeds (feedrates)"""
    return {
        "X": float(settings.get("$110", 0)),
        "Y": float(settings.get("$111", 0)),
        "Z": float(settings.get("$112", 0))
    }

# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    print("Reading current GRBL settings...")
    settings = read_all_settings()
    print_settings(settings)

    accel = get_acceleration(settings)
    print(f"\nCurrent acceleration (mm/sec^2): X={accel['X']}, Y={accel['Y']}, Z={accel['Z']}")

    speed = get_speed(settings)
    print(f"Current max speed (mm/min): X={speed['X']}, Y={speed['Y']}, Z={speed['Z']}")

    # --- Example: adjust acceleration ---
    print("\nSetting new acceleration to 1000 mm/sec^2")
    set_setting("$120", 2000)
    set_setting("$121", 2000)
    set_setting("$122", 500)

    # --- Example: adjust max speeds ---
    print("\nSetting new maximum feedrates (1000 mm/min X/Y, 600 mm/min Z)")
    set_setting("$110", 1000)  # X-axis max feedrate
    set_setting("$111", 1000)  # Y-axis max feedrate
    set_setting("$112", 600)   # Z-axis max feedrate

    # Verify changes
    print("\nUpdated GRBL settings:")
    settings = read_all_settings()
    print_settings(settings)

    ser.close()
    print("\nGRBL connection closed.")
