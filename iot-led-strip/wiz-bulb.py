import socket
import json

ip = "192.168.29.216"
port = 38899

msg = {
    "method": "setPilot",
    "params": {
        "r": 255,
        "g": 0,
        "b": 0,
        "state": True
    }
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(json.dumps(msg).encode(), (ip, port))
