import serial
import time

try:
    ser = serial.Serial(
        "/dev/ttyACM0",
        115200,
        timeout=1,
        write_timeout=2,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False
    )

    time.sleep(3)
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    ser.write(b"Hallo vom Raspberry Pi\n")
    ser.flush()
    time.sleep(0.5)

    ser.write(b"USB Stick erkannt\n")
    ser.flush()
    time.sleep(0.5)

    print("Senden erfolgreich")
    ser.close()

except serial.SerialTimeoutException:
    print("Schreiben in /dev/ttyACM0 hat Timeout -> ESP antwortet/akzeptiert nicht sauber")
except serial.SerialException as e:
    print("Serial-Fehler:", e)