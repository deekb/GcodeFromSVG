import pygame
import serial
import time
import re

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
UPDATE_INTERVAL = 0.05  # 50 ms

# ----------------------
# Read GRBL settings
# ----------------------
def read_grbl_settings(ser):
    ser.write(b"$$\n")
    time.sleep(0.2)

    text = ser.read(4096).decode("utf-8", errors="ignore")
    print("GRBL settings dump:")
    print(text)

    def parse_val(name):
        match = re.search(rf"\${name}=([\d.]+)", text)
        return float(match.group(1)) if match else 500.0

    max_x = parse_val(110)  # mm/min
    max_y = parse_val(111)
    max_z = parse_val(112)

    # Convert to mm/sec
    return max_x / 60.0, max_y / 60.0, max_z / 60.0


# ----------------------
# Init hardware
# ----------------------
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.2)
time.sleep(3)

# Read GRBL feed rates
MAX_VX, MAX_VY, MAX_VZ = read_grbl_settings(ser)
print(f"Max Speeds from GRBL: X={MAX_VX} mm/s  Y={MAX_VY} mm/s  Z={MAX_VZ} mm/s")

# Init pygame
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() == 0:
    raise RuntimeError("No joystick found")
joystick = pygame.joystick.Joystick(0)
joystick.init()

print("Using joystick:", joystick.get_name())

# Position state
px = py = pz = 0.0
laser_on = False
laser_power = 0
last_time = time.time()


def send(cmd):
    ser.write((cmd + "\n").encode("utf-8"))
    resp = ser.readline().decode("utf-8", errors="ignore").strip()
    print(">>", cmd, "<<", resp)
    return resp


# ----------------------
# Main loop
# ----------------------
try:
    while True:
        now = time.time()
        if now - last_time >= UPDATE_INTERVAL:
            last_time = now

            pygame.event.pump()

            # -------------------
            # Read axis input
            # -------------------
            x_axis = joystick.get_axis(0)
            y_axis = -joystick.get_axis(1)  # INVERTED
            z_axis = -joystick.get_axis(3)  # INVERTED

            # Deadzone
            if abs(x_axis) < 0.1: x_axis = 0
            if abs(y_axis) < 0.1: y_axis = 0
            if abs(z_axis) < 0.1: z_axis = 0

            dt = UPDATE_INTERVAL

            # -------------------
            # Apply GRBL speeds (mm/sec)
            # -------------------
            px += x_axis * MAX_VX * dt
            py += y_axis * MAX_VY * dt
            pz += z_axis * MAX_VZ * dt

            send(f"G0 X{px:.3f} Y{py:.3f} Z{pz:.3f}")

            # -------------------
            # Laser on/off
            # -------------------
            button_a = joystick.get_button(1)
            button_b = joystick.get_button(2)

            if button_a and not laser_on:
                laser_on = True
                send("M3")

            if button_b and laser_on:
                laser_on = False
                send("M5")

            # -------------------
            # Laser power (D-pad)
            # -------------------
            hat_x, hat_y = joystick.get_hat(0)
            if hat_x == 1:
                laser_power = min(1000, laser_power + 10)
                send(f"S{laser_power}")
            if hat_x == -1:
                laser_power = max(0, laser_power - 10)
                send(f"S{laser_power}")

        time.sleep(0.01)

except KeyboardInterrupt:
    print("Exiting...")

finally:
    ser.close()
    pygame.quit()
