# 🍳 ESP32 Cookbook

A collection of MicroPython experiments, drivers, and IoT projects for the ESP32. From low-level hardware control to cloud-connected bridges.

## 📁 Repository Structure

### 📈 PC Stats Visualizer (Root)
Real-time monitoring of your PC's RAM/CPU usage displayed on an SSD1306 OLED.
- `main.py`: ESP32 firmware that renders a scrolling graph and handles serial data.
- `send_cpu.py`: PC-side Python script (requires `psutil` and `pyserial`) to stream stats to the ESP32.
- `ssd1306.py`: Standard driver for the OLED display.
- `buzz.py`: Asynchronous buzzer alerts ("laser shot" sound) triggered by events.

### 💡 IoT LED Strip (`/iot-led-strip`)
A cloud-connected bridge for "dumb" LED strips, adding WiFi, MQTT, and a web dashboard.
- **Features**: MQTT fallback, color tracking, jump-to-color macros, and a mobile-friendly UI.
- **Architecture**: Local-first HTTP control with HiveMQ cloud integration.

## 🛠 Hardware Used
- **MCU**: ESP32 Devkit WROOM-32 (38-pin version).
- **Expansion**: 38-Pin ESP32S Expansion Board.
- **Display**: SSD1306 OLED 128x32 (I2C on Pins 21/22).
- **Buzzer**: Active/Passive piezo buzzer (PWM on Pin 14).
- **LEDs**: Standard 12V RGB LED strip with a push-button controller (bridged via GPIO).

## 🚀 Quick Start

### 1. RAM Visualizer
1. Flash `main.py` and `ssd1306.py` to your ESP32.
2. Install PC dependencies: `pip install psutil pyserial`.
3. Update `PORT` in `send_cpu.py` and run it: `python send_cpu.py`.

### 2. Smart LED Controller
Navigate to the `iot-led-strip` directory and follow the instructions in its [README.md](./iot-led-strip/README.md).

## 🔌 Connection Map (General)
| Peripheral | ESP32 Pin | Protocol |
| :--- | :--- | :--- |
| OLED SDA | GPIO 21 | I2C |
| OLED SCL | GPIO 22 | I2C |
| Buzzer | GPIO 14 | PWM |
| LED Mode | GPIO 26 | Digital Out |
| LED Speed | GPIO 25 | Digital Out |
| LED Light | GPIO 33 | Digital Out |

---
*Everything here runs on MicroPython. Happy Hacking!*