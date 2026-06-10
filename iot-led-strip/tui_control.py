from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Center, Middle
import paho.mqtt.publish as publish

MQTT_BROKER = "broker.hivemq.com"
TOPIC_PREFIX = "/anikets32/button/"

class ButtonSimApp(App):
    """A TUI to simulate button presses on ESP32 via MQTT."""

    CSS = """
    Screen {
        align: center middle;
    }

    #container {
        width: 40;
        height: 15;
        border: thick $primary;
        padding: 1;
    }

    Button {
        width: 100%;
        margin-bottom: 1;
    }

    #status {
        text-align: center;
        color: $accent;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("1", "press('26')", "Press 26"),
        ("2", "press('25')", "Press 25"),
        ("3", "press('33')", "Press 33"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center(id="container"):
            yield Static("ESP32 Button Simulator", id="title")
            yield Button("Pin 26 (Key: 1)", variant="primary", id="btn_26")
            yield Button("Pin 25 (Key: 2)", variant="success", id="btn_25")
            yield Button("Pin 33 (Key: 3)", variant="warning", id="btn_33")
            yield Static("Ready", id="status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        pin = event.button.id.split("_")[-1]
        self.action_press(pin)

    def action_press(self, pin: str) -> None:
        topic = f"{TOPIC_PREFIX}{pin}"
        try:
            publish.single(topic, payload="press", hostname=MQTT_BROKER)
            self.query_one("#status").update(f"Pressed Pin {pin}!")
        except Exception as e:
            self.query_one("#status").update(f"Error: {e}")

if __name__ == "__main__":
    app = ButtonSimApp()
    app.run()
