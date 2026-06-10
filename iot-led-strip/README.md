# ESP32 Smart LED Controller

An intelligent, cloud-connected bridge for "dumb" LED strips. This project uses an ESP32 to simulate button presses on an existing LED controller, adding WiFi, MQTT, and color-tracking intelligence.

## 🚀 Key Features

*   **Local-First Architecture**: Ultra-fast control via direct HTTP calls when on the home network.
*   **MQTT Cloud Fallback**: Control your lights from anywhere via the HiveMQ public broker.
*   **Intelligent Color Tracking**: Tracks the current state of a 20-color cycle LED strip.
*   **Jump-to-Color Macros**: Automatically pulses the "Light" button to reach a specific color from any state.
*   **Self-Healing**: Automatic WiFi and MQTT reconnection logic.
*   **Web Dashboard**: A responsive mobile-friendly UI hosted directly on the ESP32.

## 🛠 Hardware Mapping

| Device Pin | Function | Description |
| :--- | :--- | :--- |
| **P26** | **MODE** | Cycles through strobe/fade modes. |
| **P25** | **SPEED** | Adjusts mode speed or static intensity. |
| **P33** | **LIGHT** | Cycles through 20 static colors. |

*Common trace of the dome switches must be connected to ESP32 Ground.*

## 📱 Accessing the Dashboard

While on your home WiFi, navigate to:
**[http://192.168.29.118](http://192.168.29.118)**

## 🎨 Color Cycle (20 States)
The system tracks the following sequence:
1. Red, 2. Blue, 3. Green, 4. Magenta, 5. Cyan, 6. Yellow, 7. Teal-Blue, 8. Pink, 9. Purple, 10. Violet, 11. Blue 2, 12. Blue 3, 13. Blue 4, 14. Green 2, 15. Green 3, 16. Green 4, 17. White-Green, 18. Yellow-Green, 19. Teal, 20. Teal 2.

## 💻 Developer Commands

### Triggering Pins Locally (API)
```bash
# Press Mode
curl http://192.168.29.118/press/26

# Jump to Green (Index 2)
curl http://192.168.29.118/goto/2

# Sync to Red (Index 0)
curl http://192.168.29.118/sync/0
```

### Management (via USB)
1. **Activate Environment**: `source .venv/bin/activate`
2. **Update Code**: `mpremote cp main.py :main.py`
3. **Hard Reset**: `mpremote reset`

## 📝 Configuration
WiFi and MQTT settings are located at the top of `main.py`. State is persisted locally in `color_state.txt`.
