import machine
import time
import network
import _thread
import socket
import json
import gc
from umqtt.simple import MQTTClient

# Configuration
WIFI_SSID = "Anikets Wifi 2Ghz"
WIFI_PASS = "Ragnarok258369"
MQTT_BROKER = "broker.hivemq.com"
CLIENT_ID = "esp32_anikets_button_sim"
TOPIC_PREFIX = "/anikets32/button/"
STATUS_TOPIC = "/anikets32/status"
HOSTNAME = "ledstrip"

# Pins mapping
PIN_MAP = {"26": 26, "25": 25, "33": 33}
COLORS = [
    "Red", "Blue", "Green", "Magenta", "Cyan", "Yellow", "Teal-Blue", "Pink", 
    "Purple", "Violet", "Blue 2", "Blue 3", "Blue 4", "Green 2", "Green 3", 
    "Green 4", "White-Green", "Yellow-Green", "Teal", "Teal 2"
]

mqtt_client = None
current_color_idx = 0
current_brightness = 7
target_color_idx = 0
target_brightness = 7
wlan = network.WLAN(network.STA_IF)
hw_lock = _thread.allocate_lock()
worker_lock = _thread.allocate_lock()
worker_running = False

def connect_wifi():
    global wlan
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    
    if wlan.isconnected():
        print("WiFi Connected. IP:", wlan.ifconfig()[0])
        try:
            import mdns
            m = mdns.mDNS()
            m.start(HOSTNAME, "MicroPython LED Strip")
            m.add_service("_http", "_tcp", 80)
            print(f"mDNS started: {HOSTNAME}.local")
        except:
            print("mDNS not available")
        return True
    else:
        print("WiFi Connection Failed")
        return False

def load_state():
    global current_color_idx, current_brightness, target_color_idx, target_brightness
    try:
        with open('color_state.txt', 'r') as f:
            lines = f.readlines()
            current_color_idx = int(lines[0].strip())
            if len(lines) > 1:
                current_brightness = int(lines[1].strip())
    except:
        current_color_idx = 0
        current_brightness = 7
    target_color_idx = current_color_idx
    target_brightness = current_brightness

def save_state():
    try:
        with open('color_state.txt', 'w') as f:
            f.write(f"{current_color_idx}\n{current_brightness}")
    except:
        pass

# HTML Content (JavaScript updated to not jump back)
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
        .brightness-section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }}
        .slider {{ width: 100%; margin: 10px 0; }}
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
        <button class="btn-speed" onclick="press('25')">SPEED (Inc)</button>
        <button class="btn-light" style="grid-column: span 2" onclick="press('33')">NEXT COLOR (Inc)</button>
    </div>

    <div class="brightness-section">
        <div style="display: flex; justify-content: space-between; font-weight: bold;">
            <span>Target Brightness:</span>
            <span id="brightness-val">{current_brightness}</span>
        </div>
        <input type="range" min="0" max="7" value="{current_brightness}" class="slider" id="brightness-slider" onchange="changeBrightness(this.value)" oninput="document.getElementById('brightness-val').innerText=this.value">
    </div>

    <div style="font-size: 0.9rem; font-weight: bold; color: #444;">Jump to Color:</div>
    <div class="color-grid">
        {color_buttons}
    </div>

    <div id="status-msg">Ready</div>

    <div class="sync-section">
        <details>
            <summary>Desynced? Set actual states:</summary>
            <div style="font-size: 0.75rem; margin-top: 10px;">Fix Color Index:</div>
            <div class="color-grid">
                {sync_buttons}
            </div>
            <div style="font-size: 0.75rem; margin-top: 10px;">Fix Brightness (0-7):</div>
            <div class="color-grid">
                {sync_bright_buttons}
            </div>
        </details>
    </div>
</div>

<script>
    const COLORS = {colors_js};
    const MQTT_BROKER = "broker.hivemq.com";
    const TOPIC_PREFIX = "{topic_prefix}";
    const client = new Paho.MQTT.Client(MQTT_BROKER, 8000, "web_" + Math.random().toString(16).substr(2, 8));
    
    let userInteracting = false;
    const slider = document.getElementById("brightness-slider");
    slider.addEventListener('mousedown', () => {{ userInteracting = true; }});
    slider.addEventListener('mouseup', () => {{ userInteracting = false; }});
    slider.addEventListener('touchstart', () => {{ userInteracting = true; }});
    slider.addEventListener('touchend', () => {{ userInteracting = false; }});

    client.onMessageArrived = (m) => {{
        if (m.destinationName === "{status_topic}" && m.payloadString.startsWith("SUCCESS")) {{
            const parts = m.payloadString.split(":");
            if (parts.length > 2) {{
                document.getElementById("current-color").innerText = COLORS[parseInt(parts[2])];
            }}
            if (parts.length > 3 && !userInteracting) {{
                const bVal = parseInt(parts[3]);
                document.getElementById("brightness-val").innerText = bVal;
                document.getElementById("brightness-slider").value = bVal;
            }}
            document.getElementById("status-msg").innerText = "Update: " + m.payloadString;
        }}
    }};
    client.connect({{ onSuccess: () => {{ client.subscribe("{status_topic}"); }} }});

    function mqttFallback(path) {{
        console.log("Using MQTT Fallback for " + path);
        let msg = "press";
        let topic = TOPIC_PREFIX;
        if (path.includes("/press/")) topic += path.split("/press/")[1];
        else if (path.includes("/goto/")) {{ topic = "/anikets32/goto"; msg = path.split("/goto/")[1]; }}
        else if (path.includes("/sync/")) {{ topic = "/anikets32/sync"; msg = path.split("/sync/")[1]; }}
        else if (path.includes("/brightness/")) {{ topic = "/anikets32/brightness"; msg = path.split("/brightness/")[1]; }}
        
        try {{
            const message = new Paho.MQTT.Message(msg);
            message.destinationName = topic;
            client.send(message);
            document.getElementById("status-msg").innerText = "Sent via MQTT";
        }} catch(e) {{
            document.getElementById("status-msg").innerText = "MQTT Error: " + e;
        }}
    }}

    async function apiCall(path) {{
        document.getElementById("status-msg").innerText = "Sending...";
        try {{
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            const res = await fetch(path, {{ signal: controller.signal }});
            clearTimeout(timeoutId);
            if (res.ok) {{
                const data = await res.json();
                if (data.target_index !== undefined) document.getElementById("current-color").innerText = COLORS[data.target_index];
                if (data.target_brightness !== undefined && !userInteracting) {{
                    document.getElementById("brightness-val").innerText = data.target_brightness;
                    document.getElementById("brightness-slider").value = data.target_brightness;
                }}
                document.getElementById("status-msg").innerText = "Command Queued";
            }} else {{
                throw new Error("HTTP error");
            }}
        }} catch(e) {{
            document.getElementById("status-msg").innerText = "Local Error, trying MQTT...";
            mqttFallback(path);
        }}
    }}

    function press(p) {{ apiCall('/press/' + p); }}
    function goTo(idx) {{ apiCall('/goto/' + idx); }}
    function sync(idx) {{ apiCall('/sync/' + idx); }}
    function syncB(val) {{ apiCall('/sync_b/' + val); }}
    function changeBrightness(val) {{ apiCall('/brightness/' + val); }}
</script>
</body>
</html>
"""

def get_html():
    gc.collect()
    color_buttons = "".join([f'<button class="color-btn" onclick="goTo({i})">{COLORS[i]}</button>' for i in range(len(COLORS))])
    sync_buttons = "".join([f'<button class="color-btn" onclick="sync({i})">{COLORS[i]}</button>' for i in range(len(COLORS))])
    sync_bright_buttons = "".join([f'<button class="color-btn" onclick="syncB({i})">{i}</button>' for i in range(8)])
    return HTML_TEMPLATE.format(
        current_color=COLORS[current_color_idx],
        current_brightness=target_brightness,
        color_buttons=color_buttons,
        sync_buttons=sync_buttons,
        sync_bright_buttons=sync_bright_buttons,
        colors_js=json.dumps(COLORS),
        topic_prefix=TOPIC_PREFIX,
        status_topic=STATUS_TOPIC
    )

def press_pin(pin_num, update_state=True):
    global current_color_idx, current_brightness, target_color_idx, target_brightness
    with hw_lock:
        if pin_num in PIN_MAP:
            p_id = PIN_MAP[pin_num]
            p = machine.Pin(p_id, machine.Pin.OUT)
            p.value(0)
            time.sleep(0.1)
            machine.Pin(p_id, machine.Pin.IN)
            
            if update_state:
                if pin_num == "33":
                    current_color_idx = (current_color_idx + 1) % len(COLORS)
                    if target_color_idx == (current_color_idx - 1) % len(COLORS): # If it was a manual press
                         target_color_idx = current_color_idx
                    save_state()
                elif pin_num == "25":
                    current_brightness = (current_brightness + 1) % 8
                    if target_brightness == (current_brightness - 1) % 8: # If it was a manual press
                        target_brightness = current_brightness
                    save_state()
                
            try:
                if mqtt_client: 
                    mqtt_client.publish(STATUS_TOPIC, f"SUCCESS:{pin_num}:{current_color_idx}:{current_brightness}")
            except: pass
            return True
    return False

def goal_worker():
    global worker_running, current_color_idx, current_brightness, target_color_idx, target_brightness
    worker_running = True
    while True:
        changed = False
        
        # Handle Color
        if current_color_idx != target_color_idx:
            press_pin("33")
            changed = True
        
        # Handle Brightness
        elif current_brightness != target_brightness:
            press_pin("25")
            changed = True
            
        if not changed:
            # Check if targets changed while we were working
            with worker_lock:
                if current_color_idx == target_color_idx and current_brightness == target_brightness:
                    worker_running = False
                    break
        time.sleep(0.4)

def ensure_worker():
    global worker_running
    with worker_lock:
        if not worker_running:
            _thread.start_new_thread(goal_worker, ())

def mqtt_thread():
    global mqtt_client, current_color_idx, current_brightness, target_color_idx, target_brightness
    while True:
        try:
            if not wlan.isconnected():
                time.sleep(5)
                continue
            mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
            def sub_cb(topic, msg):
                global target_color_idx, target_brightness, current_color_idx, current_brightness
                t = topic.decode()
                m = msg.decode()
                if "/goto" in t:
                    try: 
                        target_color_idx = int(m) % len(COLORS)
                        ensure_worker()
                    except: pass
                elif "/sync" in t:
                    try:
                        current_color_idx = int(m) % len(COLORS)
                        target_color_idx = current_color_idx
                        save_state()
                    except: pass
                elif "/brightness" in t:
                    try: 
                        target_brightness = int(m) % 8
                        ensure_worker()
                    except: pass
                else:
                    press_pin(t.split('/')[-1])
            
            mqtt_client.set_callback(sub_cb)
            mqtt_client.connect()
            mqtt_client.subscribe(TOPIC_PREFIX + "#")
            mqtt_client.subscribe("/anikets32/goto")
            mqtt_client.subscribe("/anikets32/sync")
            mqtt_client.subscribe("/anikets32/brightness")
            while True:
                mqtt_client.check_msg()
                time.sleep(0.1)
        except Exception as e:
            print("MQTT Error:", e)
            time.sleep(5)

def web_server():
    global current_color_idx, current_brightness, target_color_idx, target_brightness
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    print("Web server started on port 80")
    
    last_wifi_check = time.time()
    
    while True:
        try:
            if time.time() - last_wifi_check > 30:
                if not wlan.isconnected():
                    connect_wifi()
                last_wifi_check = time.time()

            s.settimeout(5)
            try:
                conn, addr = s.accept()
            except OSError:
                continue
            
            s.settimeout(None)
            request_bytes = conn.recv(1024)
            if not request_bytes:
                conn.close()
                continue
            request = request_bytes.decode()
            
            response_data = None
            if "GET /press/" in request:
                pin = request[request.find("/press/")+7 : request.find("/press/")+9]
                press_pin(pin)
                response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
            elif "GET /goto/" in request:
                try:
                    idx_str = request[request.find("/goto/")+6 : request.find(" HTTP")]
                    target_color_idx = int(idx_str) % len(COLORS)
                    ensure_worker()
                except: pass
                response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
            elif "GET /brightness/" in request:
                try:
                    b_str = request[request.find("/brightness/")+12 : request.find(" HTTP")]
                    target_brightness = int(b_str) % 8
                    ensure_worker()
                except: pass
                response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
            elif "GET /sync/" in request:
                try:
                    idx_str = request[request.find("/sync/")+6 : request.find(" HTTP")]
                    current_color_idx = int(idx_str) % len(COLORS)
                    target_color_idx = current_color_idx
                    save_state()
                except: pass
                response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
            elif "GET /sync_b/" in request:
                try:
                    b_str = request[request.find("/sync_b/")+8 : request.find(" HTTP")]
                    current_brightness = int(b_str) % 8
                    target_brightness = current_brightness
                    save_state()
                except: pass
                response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
            
            if response_data:
                conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response_data)
            else:
                html = get_html()
                conn.sendall("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html)
            conn.close()
        except Exception as e:
            print("Web Error:", e)
            try: conn.close()
            except: pass

# Start
load_state()
if connect_wifi():
    _thread.start_new_thread(mqtt_thread, ())
    web_server()
else:
    print("Failed to start networking. Rebooting in 30s...")
    time.sleep(30)
    machine.reset()
