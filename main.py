# main.py for ESP32 MicroPython (works with 128x32 or 128x64 OLED)
# Save this file to your ESP32, reset it, then run send_cpu.py on the PC.

import sys, uselect, utime
import uasyncio as asyncio
from machine import Pin, I2C, PWM
from ssd1306 import SSD1306_I2C
import math

# --- Hardware setup ---
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = SSD1306_I2C(128, 32, i2c)   # change to 64 if your OLED is 128x64
buzz_pin = 14                      # GPIO driving your buzzer

# --- Serial (USB) polling ---
poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

# --- Data buffer for 128‑pixel graph ---
W, H = 128, oled.height
buf = [0] * W
threshold = 50.0                  # CPU % threshold to trigger beep

def y_of(pct):
    """Map 0–100 % to y coordinate on OLED (0=top, H−1=bottom)."""
    return H - 1 - int((pct * (H - 1)) / 100)

def draw_graph(values, last_val):
    """Draw scrolling CPU graph and text HUD on the OLED."""
    oled.fill(0)
    # baseline at bottom
    # oled.hline(0, H - 1, W, 1)
    # 50% marker (dotted line)
    # for x in range(0, W, 4):
    #     oled.pixel(x, y_of(50), 1)
    # plot CPU line
    prev_y = y_of(values[0])
    for x in range(1, W):
        y = y_of(values[x])
        oled.line(x - 1, prev_y, x, y, 1)
        prev_y = y
    # overlay text
    oled.fill_rect(0, 0, 80, 12, 0)
    oled.text("RAM {:>5.1f}%".format(last_val), 0, 0)
    oled.show()

phase = 0
def idle_anim(speed = 0.1):
    global phase

    oled.fill(0)
    for x in range(W):
        y = int((H//2) + math.sin((x * 0.2) + phase) * (H//3))
        oled.pixel(x, y, 1)
        
    oled.show()
    phase += speed

async def cpu_reader():
    """Read CPU % from USB, update graph asynchronously."""
    last_rx_ms = utime.ticks_ms()
    last_val = 0.0
    while True:
        evs = poll.poll(0)
        # read all available lines quickly
        if evs and (evs[0][1] & uselect.POLLIN):
            line = sys.stdin.readline()
            try:
                v = float(line.strip())
            except:
                continue
            v = max(0.0, min(v, 100.0))  # clamp 0–100
            buf.pop(0)
            buf.append(int(v))
            last_val = v
            last_rx_ms = utime.ticks_ms()
            draw_graph(buf, last_val)
        else:      
            idle_anim(speed=0.3)
        # yield to other coroutines
        await asyncio.sleep_ms(100)

asyncio.run(cpu_reader())
