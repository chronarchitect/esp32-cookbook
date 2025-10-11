# send_cpu.py (run on your PC)
import time, sys
import serial
import psutil

# CHANGE THIS to your port:
# Windows: "COM5" (check Device Manager -> Ports)
# Linux:   "/dev/ttyUSB0" or "/dev/ttyACM0"
# macOS:   "/dev/tty.SLAB_USBtoUART" or "/dev/tty.usbssserial-xxxx"
PORT = "COM9"
BAUD = 115200
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
except Exception as e:
    print("Could not open serial port:", e)
    print("Hint: close Thonny/serial monitor and pick the right port.")
    sys.exit(1)

def reset_esp32():
    """Pulse EN via RTS to reset. Keep GPIO0 (DTR) high -> normal boot"""
    try:
        print("Resetting ESP32")
        ser.setDTR(False)
        ser.setRTS(True)
        time.sleep(0.1)
        ser.setRTS(False)
    except Exception as e:
        print(e)
        pass

def main():

    # first read primes psutil; the first call can be averaged over an interval
    psutil.virtual_memory()

    print("Streaming RAM % to ESP32. Ctrl+C to stop.")
    try:
        while True:
            # a short interval gives a responsive graph
            pct = psutil.virtual_memory().percent
            line = f"{pct:.1f}\n"
            ser.write(line.encode("ascii"))
            # small pacing (ESP redraws ~10 Hz)
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        reset_esp32()
        try: ser.close()
        except: pass
        sys.exit(0)

if __name__ == "__main__":
    main()
