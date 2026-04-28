import serial
import time

ser = serial.Serial("/dev/ttyACM0", 115200, timeout=1)
time.sleep(2)
ser.write(b"Hallo vom Raspberry Pi\n")
ser.write(b"USB Stick erkannt\n")
ser.close()