let userInteracting = false;
const COLORS_JS = JSON.parse(document.getElementById('colors-data').textContent);
const COLORS_RGB = JSON.parse(document.getElementById('colors-rgb').textContent);
const STATUS_TOPIC = document.getElementById('config-status-topic').textContent;

const slider = document.getElementById("brightness-slider");
slider.addEventListener('mousedown', () => { userInteracting = true; });
slider.addEventListener('mouseup', () => { userInteracting = false; });
slider.addEventListener('touchstart', () => { userInteracting = true; });
slider.addEventListener('touchend', () => { userInteracting = false; });

const MQTT_BROKER = "broker.hivemq.com";
const client = new Paho.MQTT.Client(MQTT_BROKER, 8000, "web_" + Math.random().toString(16).substr(2, 8));

client.onMessageArrived = (m) => {
    if (m.destinationName === STATUS_TOPIC && m.payloadString.startsWith("SUCCESS")) {
        const parts = m.payloadString.split(":");
        if (parts.length > 2) {
            document.getElementById("current-color").innerText = COLORS_JS[parseInt(parts[2])];
        }
        if (parts.length > 3 && !userInteracting) {
            const bVal = parseInt(parts[3]);
            document.getElementById("brightness-val").innerText = bVal;
            document.getElementById("brightness-slider").value = bVal;
        }
    }
};

client.connect({ onSuccess: () => { client.subscribe(STATUS_TOPIC); } });

async function apiCall(path) {
    document.getElementById("status-msg").innerText = "Updating...";
    try {
        const res = await fetch(path);
        if (res.ok) {
            const data = await res.json();
            if (data.target_index !== undefined) document.getElementById("current-color").innerText = COLORS_JS[data.target_index];
            if (data.target_brightness !== undefined && !userInteracting) {
                document.getElementById("brightness-val").innerText = data.target_brightness;
                document.getElementById("brightness-slider").value = data.target_brightness;
            }
            document.getElementById("status-msg").innerText = "Done";
            setTimeout(() => { document.getElementById("status-msg").innerText = "System Ready"; }, 2000);
        }
    } catch(e) {
        document.getElementById("status-msg").innerText = "Connection lost";
    }
}

function press(p) { apiCall('/press/' + p); }
function goTo(idx) { apiCall('/goto/' + idx); }
function sync(idx) { apiCall('/sync/' + idx); }
function syncB(val) { apiCall('/sync_b/' + val); }
function changeBrightness(val) { apiCall('/brightness/' + val); }
function wizTemp(v) { apiCall('/wiz/temp/' + v); }
function wizDim(v) { apiCall('/wiz/dim/' + v); }
function wizColor(hex) {
    const r = parseInt(hex.substr(1,2), 16);
    const g = parseInt(hex.substr(3,2), 16);
    const b = parseInt(hex.substr(5,2), 16);
    apiCall('/wiz/rgb/' + r + '/' + g + '/' + b);
}
function toggleComplement() {
    fetch('/complement/').then(res => res.json()).then(data => {
        const status = data.complement_mode ? "ON" : "OFF";
        document.getElementById("complement-btn").innerText = "Complement: " + status;
        document.getElementById("status-msg").innerText = "Complement " + status;
        setTimeout(() => { document.getElementById("status-msg").innerText = "System Ready"; }, 2000);
    }).catch(e => {
        document.getElementById("status-msg").innerText = "Connection lost";
    });
}

// UI Initialization
function initUI() {
    const grid = document.getElementById('main-color-grid');
    COLORS_JS.forEach((name, i) => {
        const rgb = COLORS_RGB[i];
        const circle = document.createElement('div');
        circle.className = 'color-circle';
        circle.style.backgroundColor = `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
        circle.title = name;
        circle.onclick = () => goTo(i);
        grid.appendChild(circle);
    });
}

initUI();
