import machine
import time
import network
import _thread
import socket
import json
import gc

# --- Configuration ---
WIFI_SSID = "Anikets Wifi 2Ghz"
WIFI_PASS = "Ragnarok258369"
MQTT_BROKER = "broker.hivemq.com"
CLIENT_ID = "esp32_anikets_button_sim"
TOPIC_PREFIX = "/anikets32/button/"
STATUS_TOPIC = "/anikets32/status"
HOSTNAME = "ledstrip"

# WiZ Bulb Configuration
WIZ_IP = "192.168.29.216"
WIZ_PORT = 38899

# Pins mapping
PIN_MAP = {"26": 26, "25": 25, "33": 33}
COLORS = [
    "Red", "Blue", "Green", "Magenta", "Cyan", "Yellow", "Teal-Blue", "Pink", 
    "Purple", "Violet", "Blue 2", "Blue 3", "Blue 4", "Green 2", "Green 3", 
    "Green 4", "White-Green", "Yellow-Green", "Teal", "Teal 2"
]

COLOR_RGB = [
    (255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 128, 255), (255, 105, 180),
    (128, 0, 128), (148, 0, 211), (30, 144, 255), (0, 191, 255), (70, 130, 180), (50, 205, 50), (34, 139, 34), (0, 100, 0),
    (152, 251, 152), (173, 255, 47), (0, 128, 128), (0, 255, 127)
]

# --- Global State ---
mqtt_client = None
current_color_idx = 0
current_brightness = 7
target_color_idx = 0
target_brightness = 7
wlan = network.WLAN(network.STA_IF)
hw_lock = _thread.allocate_lock()
worker_lock = _thread.allocate_lock()
worker_running = False
wiz_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- Dependency Check ---
try:
    from umqtt.simple import MQTTClient
    MQTT_AVAILABLE = True
except ImportError:
    print("Warning: umqtt.simple not found. MQTT will be disabled.")
    MQTT_AVAILABLE = False

# --- Persistence ---
def load_state():
    global current_color_idx, current_brightness, target_color_idx, target_brightness
    try:
        with open('color_state.txt', 'r') as f:
            lines = f.readlines()
            current_color_idx = int(lines[0].strip())
            if len(lines) > 1:
                current_brightness = int(lines[1].strip())
            print("Loaded state: index", current_color_idx, "brightness", current_brightness)
    except Exception as e:
        print("State load failed:", e)
        current_color_idx = 0
        current_brightness = 7
    target_color_idx = current_color_idx
    target_brightness = current_brightness

def save_state():
    try:
        with open('color_state.txt', 'w') as f:
            f.write(f"{current_color_idx}\n{current_brightness}")
    except Exception as e:
        print("State save failed:", e)

# --- WiZ Control ---
def set_wiz(params):
    msg = {"method": "setPilot", "params": params}
    try:
        wiz_sock.sendto(json.dumps(msg).encode(), (WIZ_IP, WIZ_PORT))
    except Exception as e:
        print("WiZ Error:", e)

def sync_wiz_to_current():
    r, g, b = COLOR_RGB[current_color_idx]
    set_wiz({"r": r, "g": g, "b": b, "state": True})

# --- Network ---
def connect_wifi():
    global wlan
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi: %s..." % WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASS)
        for i in range(20):
            if wlan.isconnected(): break
            print("  Waiting... (%d)" % (i+1))
            time.sleep(1)
    
    if wlan.isconnected():
        print("WiFi Connected!")
        print("IP Info:", wlan.ifconfig())
        return True
    
    print("WiFi Connection FAILED")
    return False

# --- Logic ---
def press_pin_logic(pin_num, update_state=True):
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
                    sync_wiz_to_current()
                elif pin_num == "25":
                    current_brightness = (current_brightness + 1) % 8
                    if target_brightness == (current_brightness - 1) % 8: # If it was a manual press
                        target_brightness = current_brightness
                    save_state()
            
            if mqtt_client and MQTT_AVAILABLE:
                try:
                    mqtt_client.publish(STATUS_TOPIC, "SUCCESS:%s:%d:%d" % (pin_num, current_color_idx, current_brightness))
                except:
                    pass
            return True
    return False

def goal_worker():
    global worker_running, current_color_idx, current_brightness, target_color_idx, target_brightness
    worker_running = True
    while True:
        changed = False
        
        # Handle Color
        if current_color_idx != target_color_idx:
            press_pin_logic("33")
            changed = True
        
        # Handle Brightness
        elif current_brightness != target_brightness:
            press_pin_logic("25")
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

def jump_to_color_logic(target_idx):
    global target_color_idx
    target_color_idx = target_idx % len(COLORS)
    ensure_worker()

def set_brightness_logic(level):
    global target_brightness
    target_brightness = int(level) % 8
    ensure_worker()

# --- Web Server ---
def get_html_content():
    gc.collect()
    try:
        with open('index.html', 'r') as f:
            tmpl = f.read()
        
        color_buttons = "".join(['<button class="color-btn" onclick="goTo(%d)">%s</button>' % (i, COLORS[i]) for i in range(len(COLORS))])
        sync_buttons = "".join(['<button class="color-btn" onclick="sync(%d)">%s</button>' % (i, COLORS[i]) for i in range(len(COLORS))])
        sync_bright_buttons = "".join(['<button class="color-btn" onclick="syncB(%d)">%d</button>' % (i, i) for i in range(8)])
        
        return tmpl.format(
            current_color=COLORS[current_color_idx],
            current_brightness=target_brightness,
            color_buttons=color_buttons,
            sync_buttons=sync_buttons,
            sync_bright_buttons=sync_bright_buttons,
            colors_js=json.dumps(COLORS),
            colors_rgb=json.dumps(COLOR_RGB),
            status_topic=STATUS_TOPIC
        )
    except Exception as e:
        return "Error loading index.html: %s" % e

def serve_file(conn, filename, content_type):
    try:
        with open(filename, 'r') as f:
            conn.send("HTTP/1.1 200 OK\r\nContent-Type: %s\r\n\r\n" % content_type)
            while True:
                chunk = f.read(512)
                if not chunk: break
                conn.send(chunk)
    except:
        conn.send("HTTP/1.1 404 Not Found\r\n\r\n")

def mqtt_worker():
    global mqtt_client, current_color_idx, current_brightness, target_color_idx, target_brightness
    if not MQTT_AVAILABLE:
        print("MQTT Worker aborted: umqtt.simple not found.")
        return

    while True:
        try:
            if not wlan.isconnected():
                time.sleep(5)
                continue
            
            print("Connecting to MQTT Broker...")
            mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
            
            def sub_cb(topic, msg):
                global target_color_idx, target_brightness, current_color_idx, current_brightness
                t = topic.decode()
                m = msg.decode()
                print("MQTT Msg:", t, m)
                if "/goto" in t:
                    try: jump_to_color_logic(int(m))
                    except: pass
                elif "/sync" in t:
                    try:
                        current_color_idx = int(m) % len(COLORS)
                        target_color_idx = current_color_idx
                        save_state()
                        sync_wiz_to_current()
                    except: pass
                elif "/brightness" in t:
                    try: set_brightness_logic(int(m))
                    except: pass
                else:
                    press_pin_logic(t.split('/')[-1])
            
            mqtt_client.set_callback(sub_cb)
            mqtt_client.connect()
            mqtt_client.subscribe(TOPIC_PREFIX + "#")
            mqtt_client.subscribe("/anikets32/goto")
            mqtt_client.subscribe("/anikets32/sync")
            mqtt_client.subscribe("/anikets32/brightness")
            print("MQTT Connected and Subscribed")
            
            while True:
                mqtt_client.check_msg()
                time.sleep(0.1)
        except Exception as e:
            print("MQTT Error:", e)
            time.sleep(5)

def run_server():
    global current_color_idx, current_brightness, target_color_idx, target_brightness
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        s.bind(addr)
        s.listen(5)
    except Exception as e:
        print("Bind Error:", e)
        return

    print("Web server listening on", addr)
    last_wifi_check = time.time()
    
    while True:
        try:
            if time.time() - last_wifi_check > 30:
                if not wlan.isconnected():
                    print("WiFi lost, attempting reconnect...")
                    connect_wifi()
                last_wifi_check = time.time()
            
            s.settimeout(5)
            try:
                conn, client_addr = s.accept()
            except OSError:
                continue
            
            print("Request from:", client_addr)
            conn.settimeout(3)
            
            try:
                line = conn.readline()
                if not line:
                    conn.close()
                    continue
                
                request = line.decode()
                while True:
                    l = conn.readline()
                    if not l or l == b'\r\n': break
                
                response_data = None
                if "GET /style.css" in request:
                    serve_file(conn, "style.css", "text/css")
                    conn.close()
                    continue
                elif "GET /script.js" in request:
                    serve_file(conn, "script.js", "application/javascript")
                    conn.close()
                    continue
                elif "GET /press/" in request:
                    start = request.find("/press/") + 7
                    pin = request[start : start + 2]
                    press_pin_logic(pin)
                    response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
                elif "GET /goto/" in request:
                    try:
                        start = request.find("/goto/") + 6
                        end = request.find(" ", start)
                        idx_str = request[start:end]
                        jump_to_color_logic(int(idx_str))
                    except: pass
                    response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
                elif "GET /brightness/" in request:
                    try:
                        start = request.find("/brightness/") + 12
                        end = request.find(" ", start)
                        level_str = request[start:end]
                        set_brightness_logic(int(level_str))
                    except: pass
                    response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
                elif "GET /sync/" in request:
                    try:
                        start = request.find("/sync/") + 6
                        end = request.find(" ", start)
                        idx_str = request[start:end]
                        current_color_idx = int(idx_str) % len(COLORS)
                        target_color_idx = current_color_idx
                        save_state()
                        sync_wiz_to_current()
                    except: pass
                    response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
                elif "GET /sync_b/" in request:
                    try:
                        start = request.find("/sync_b/") + 8
                        end = request.find(" ", start)
                        b_str = request[start:end]
                        current_brightness = int(b_str) % 8
                        target_brightness = current_brightness
                        save_state()
                    except: pass
                    response_data = json.dumps({"target_index": target_color_idx, "target_brightness": target_brightness})
                elif "GET /wiz/temp/" in request:
                    try:
                        start = request.find("/wiz/temp/") + 10
                        end = request.find(" ", start)
                        temp = int(request[start:end])
                        set_wiz({"temp": temp, "state": True})
                    except: pass
                    response_data = json.dumps({"status": "ok"})
                elif "GET /wiz/dim/" in request:
                    try:
                        start = request.find("/wiz/dim/") + 9
                        end = request.find(" ", start)
                        dim = int(request[start:end])
                        set_wiz({"dimming": dim, "state": True})
                    except: pass
                    response_data = json.dumps({"status": "ok"})
                elif "GET /wiz/rgb/" in request:
                    try:
                        start = request.find("/wiz/rgb/") + 9
                        end = request.find(" ", start)
                        path_part = request[start:end]
                        parts = path_part.split('/')
                        set_wiz({"r": int(parts[0]), "g": int(parts[1]), "b": int(parts[2]), "state": True})
                    except: pass
                    response_data = json.dumps({"status": "ok"})
                
                if response_data:
                    conn.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n".encode())
                    conn.send(response_data.encode())
                else:
                    conn.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n".encode())
                    conn.send(get_html_content().encode())
                
                conn.close()
            except Exception as e:
                print("Request Error:", e)
                try: conn.close()
                except: pass
                
        except Exception as e:
            print("Server loop error:", e)
            time.sleep(1)

# --- Main ---
load_state()
if connect_wifi():
    if MQTT_AVAILABLE:
        _thread.start_new_thread(mqtt_worker, ())
    run_server()
else:
    print("System starting in offline mode. WiFi/MQTT unavailable.")
    # Still attempt to run server in case WiFi comes up later
    run_server()
