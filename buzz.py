from machine import Pin, PWM
import time

# simple buzzer "laser shot" alert asynchronous
async def buzz_alert(PIN=14):
    buzz = PWM(PIN)
    buzz.duty(512)

    # "laser shot" sweep
    for f in range(2000, 200, -10):
        buzz.freq(f)
        time.sleep(0.01)

    buzz.deinit()