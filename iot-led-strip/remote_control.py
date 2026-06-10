#!/usr/bin/env python3
import sys
import paho.mqtt.publish as publish

MQTT_BROKER = "broker.hivemq.com"
TOPIC_PREFIX = "/anikets32/button/"

def trigger_button(pin_num):
    topic = f"{TOPIC_PREFIX}{pin_num}"
    print(f"Publishing to {topic} on {MQTT_BROKER}...")
    publish.single(topic, payload="press", hostname=MQTT_BROKER)
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./remote_control.py <pin_id>")
        sys.exit(1)
    
    pin = sys.argv[1]
    trigger_button(pin)
