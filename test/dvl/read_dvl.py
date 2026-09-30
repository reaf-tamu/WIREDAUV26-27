from dvl.dvl import Dvl

def show_data(data, obj):
    print(data)

dvl = Dvl()

print("Connecting...")
if not dvl.connect("COM3", 115200):
    print("Could not connect:", dvl.last_err)
    raise SystemExit

print("Connected")

dvl.register_ondata_callback(show_data)

print("Starting pinging...")
if not dvl.exit_command_mode():
    print("Could not start pinging:", dvl.last_err)
    dvl.disconnect()
    raise SystemExit

print("Receiving data. Press ENTER to stop.")

try:
    input()
finally:
    print("Stopping...")
    dvl.enter_command_mode()
    dvl.unregister_all_callbacks()
    dvl.disconnect()
    print("Disconnected")
#'@ | Set-Content read_dvl.py