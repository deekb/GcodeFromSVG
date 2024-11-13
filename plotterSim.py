import serial
import time

ser = serial.Serial('/dev/pts/2', baudrate=115200)

while True:
    if ser.in_waiting:
        data = ser.readline().decode('utf-8').strip()
        print(f"Received command: {data}")
        if data == "G28":
            time.sleep(0.5)  # Simulate some delay
            ser.write(b"OK\n")
        elif data.startswith("M"):
            time.sleep(0.2)
            ser.write(b"OK\n")
        else:
            ser.write(b"OK\n")
    time.sleep(0.01)
