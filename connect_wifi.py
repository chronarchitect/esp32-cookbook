import network

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# might already be connected somehow.
if wlan.isconnected() == False:
    wlan.connect("my_network", "my_password")

# Wait for connection.
while wlan.isconnected() == False:
    pass

print('connected!')