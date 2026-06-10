import machine
import time
import network
import _thread
import socket
import json
from umqtt.simple import MQTTClient

# Configuration
WIFI_SSID = "Anikets Wifi 2Ghz"
WIFI_PASS = "Ragnarok258369"
MQTT_BROKER = "broker.hivemq.com"
CLIENT_ID = "esp32_anikets_button_sim"
TOPIC_PREFIX = "/anikets32/button/"
STATUS_TOPIC = "/anikets32/status"

# Pins mapping
PIN_MAP = {"26": 26, "25": 25, "33": 33}
COLORS = [
    "Red", "Blue", "Green", "Magenta", "Cyan", "Yellow", "Teal-Blue", "Pink", 
    "Purple", "Violet", "Blue 2", "Blue 3", "Blue 4", "Green 2", "Green 3", 
    "Green 4", "White-Green", "Yellow-Green", "Teal", "Teal 2"
]

mqtt_client = None
current_color_idx = 0

def load_state():
    global current_color_idx
    try:
        with open('color_state.txt', 'r') as f:
            current_color_idx = int(f.read())
    except:
        current_color_idx = 0

def save_state():
    try:
        with open('color_state.txt', 'w') as f:
            f.write(str(current_color_idx))
    except:
        pass

# Load state on boot
load_state()

# HTML Content
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 LED Control</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js"></script>
    <style>
        body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; margin: 0; background: #f0f2f5; }}
        .container {{ background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; width: 100%; max-width: 400px; }}
        h1 {{ font-size: 1.4rem; color: #333; margin-bottom: 10px; }}
        .status-card {{ background: #212529; color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
        .color-display {{ font-size: 1.2rem; font-weight: bold; color: #ffc107; }}
        .controls {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
        button {{ padding: 15px; border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer; }}
        .btn-mode {{ background: #007bff; }} .btn-speed {{ background: #28a745; }} .btn-light {{ background: #6f42c1; }}
        .color-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-top: 15px; }}
        .color-btn {{ padding: 8px 2px; font-size: 0.7rem; background: #e9ecef; color: #333; border: 1px solid #dee2e6; border-radius: 4px; }}
        #status-msg {{ margin-top: 15px; font-size: 0.85rem; color: #666; min-height: 20px; }}
        .sync-section {{ margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; font-size: 0.8rem; }}
    </style>
</head>
<body>
<div class="container">
    <h1>LED Controller</h1>
    
    <div class="status-card">
        <div>Current Color:</div>
        <div id="current-color" class="color-display">{current_color}</div>
    </div>

    <div class="controls">
        <button class="btn-mode" onclick="press('26')">MODE</button>
        <button class="btn-speed" onclick="press('25')">SPEED</button>
        <button class="btn-light" style="grid-column: span 2" onclick="press('33')">NEXT COLOR (Cycle)</button>
    </div>

    <div style="font-size: 0.9rem; font-weight: bold; color: #444;">Jump to Color:</div>
    <div class="color-grid">
        {color_buttons}
    </div>

    <div id="status-msg">Ready</div>

    <div class="sync-section">
        <details>
            <summary>Desynced? Set actual color:</summary>
            <div class="color-grid">
                {sync_buttons}
            </div>
        </details>
    </div>
</div>

<script>
    const COLORS = {colors_js};
    const MQTT_BROKER = "broker.hivemq.com";
    const client = new Paho.MQTT.Client(MQTT_BROKER, 8000, "web_" + Math.random().toString(16).substr(2, 8));
    
    client.onMessageArrived = (m) => {{
        if (m.destinationName === "/anikets32/status" && m.payloadString.startsWith("SUCCESS")) {{
            const parts = m.payloadString.split(":");
            if (parts.length > 2) {{
                document.getElementById("current-color").innerText = COLORS[parseInt(parts[2])];
            }}
            document.getElementById("status-msg").innerText = "Confirmed: " + m.payloadString;
        }}
    }};
    client.connect({{ onSuccess: () => {{ client.subscribe("/anikets32/status"); }} }});

    async function apiCall(path) {{
        document.getElementById("status-msg").innerText = "Sending...";
        try {{
            const res = await fetch(path);
            if (res.ok) {{
                const data = await res.json();
                document.getElementById("current-color").innerText = COLORS[data.index];
                document.getElementById("status-msg").innerText = "Ready";
            }}
        }} catch(e) {{
            document.getElementById("status-msg").innerText = "Local Error, trying MQTT...";
            // Fallback to MQTT if needed
        }}
    }}

    function press(p) {{ apiCall('/press/' + p); }}
    function goTo(idx) {{ apiCall('/goto/' + idx); }}
    function sync(idx) {{ apiCall('/sync/' + idx); }}
</script>
</body>
</html>
"""

def get_html():
    color_buttons = "".join([f'<button class="color-btn" onclick="goTo({i})">{COLORS[i]}</button>' for i in range(len(COLORS))])
    sync_buttons = "".join([f'<button class="color-btn" onclick="sync({i})">{COLORS[i]}</button>' for i in range(len(COLORS))])
    return HTML_TEMPLATE.format(
        current_color=COLORS[current_color_idx],
        color_buttons=color_buttons,
        sync_buttons=sync_buttons,
        colors_js=json.dumps(COLORS)
    )

def press_pin(pin_num, silent=False):
    global current_color_idx
    if pin_num in PIN_MAP:
        p_id = PIN_MAP[pin_num]
        p = machine.Pin(p_id, machine.Pin.OUT)
        p.value(0)
        time.sleep(0.1)
        machine.Pin(p_id, machine.Pin.IN)
        
        if pin_num == "33" and not silent:
            current_color_idx = (current_color_idx + 1) % len(COLORS)
            save_state()
            
        try:
            if mqtt_client: 
                mqtt_client.publish(STATUS_TOPIC, f"SUCCESS:{pin_num}:{current_color_idx}")
        except: pass
        return True
    return False

def jump_to_color(target_idx):
    global current_color_idx
    steps = (target_idx - current_color_idx) % len(COLORS)
    for _ in range(steps):
        press_pin("33")
        time.sleep(0.4) # Wait for controller to register and cycle

def mqtt_thread():
    global mqtt_client
    while True:
        try:
            mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
            mqtt_client.set_callback(lambda t, m: press_pin(t.decode().split('/')[-1]))
            mqtt_client.connect()
            mqtt_client.subscribe(TOPIC_PREFIX + "#")
            while True:
                mqtt_client.check_msg()
                time.sleep(0.1)
        except:
            time.sleep(5)

def web_server():
    global current_color_idx
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    while True:
        try:
            conn, addr = s.accept()
            request = conn.recv(1024).decode()
            
            response_data = None
            if "GET /press/" in request:
                pin = request[request.find("/press/")+7 : request.find("/press/")+9]
                press_pin(pin)
                response_data = json.dumps({"index": current_color_idx})
            elif "GET /goto/" in request:
                target = int(request[request.find("/goto/")+6 : request.find(" HTTP")])
                jump_to_color(target)
                response_data = json.dumps({"index": current_color_idx})
            elif "GET /sync/" in request:
                current_color_idx = int(request[request.find("/sync/")+6 : request.find(" HTTP")])
                save_state()
                response_data = json.dumps({"index": current_color_idx})
            
            if response_data:
                conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response_data)
            else:
                conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + get_html())
            conn.close()
        except:
            try: conn.close()
            except: pass

# Start
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)
while not wlan.isconnected(): time.sleep(1)
print("IP:", wlan.ifconfig()[0])

_thread.start_new_thread(mqtt_thread, ())
web_server()
