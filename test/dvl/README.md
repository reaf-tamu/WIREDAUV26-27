# Wayfinder DVL Test

This folder contains a basic Python test for communicating with the Teledyne Wayfinder DVL.

## Setup

The DVL was tested using:

- Teledyne Wayfinder DVL
- USB to RS232 adapter
- 115200 baud
- Teledyne Wayfinder Python driver
- Windows VM through VMware Fusion for initial testing

The Wayfinder Tools GUI detected the COM port but remained stuck while connecting. The official Teledyne Python driver successfully connected and returned DVL data.

## Python Dependencies

Install `pyserial`:

```bash
python -m pip install pyserial

Install the Teledyne Wayfinder Python driver from the downloaded driver directory:
python -m pip install .

Connection Test
Example:
from dvl.dvl import Dvldvl = Dvl()if dvl.connect("COM3", 115200):    print("Connected")    print(dvl.last_err)else:    print("Connection failed")


Successful output:
True
<ResponseStatusType.SUCCESS: 1>

Reading DVL Information
dvl.get_system()print(dvl.system_info)dvl.get_setup()print(dvl.system_setup)


Example system information:
Firmware Version : 1.1.0.4
Frequency        : 614400.0 Hz
Beam Angle       : 30.0 degrees
Speed of Sound   : 1500.0
Max Depth        : 60.0
Max VB Range     : 60.0

Reading Live DVL Data
The driver uses a callback to receive live data.
def show_data(data, obj):    if not data.is_valid:        return    print(        f"Vx={data.vel_x:.3f} m/s  "        f"Vy={data.vel_y:.3f} m/s  "        f"Vz={data.vel_z:.3f} m/s  "        f"Range={data.mean_range:.3f} m  "        f"B1={data.range_beam1:.3f}  "        f"B2={data.range_beam2:.3f}  "        f"B3={data.range_beam3:.3f}  "        f"B4={data.range_beam4:.3f}"    )dvl.register_ondata_callback(show_data)dvl.exit_command_mode()


Example output from the water test:
Vx=-0.133 m/s  Vy=0.484 m/s  Vz=-0.030 m/s  Range=1.001 m  B1=1.159  B2=0.707  B3=1.014  B4=1.125
Vx=-0.124 m/s  Vy=0.519 m/s  Vz=-0.032 m/s  Range=0.997 m  B1=1.142  B2=0.724  B3=1.006  B4=1.116

This confirmed that the DVL was returning live velocity and beam range measurements while submerged.
Running the Script
Run:
python read_dvl.py

The script:
1. Connects to the DVL on COM3 at 115200 baud
2. Registers a callback for live data
3. Starts DVL pinging
4. Prints velocity and beam range data
5. Stops and disconnects when finished
Stopping the DVL
Before disconnecting, return the DVL to command mode:
dvl.enter_command_mode()dvl.unregister_all_callbacks()dvl.disconnect()


Current Status
Python communication with the Wayfinder DVL is working.
Next Steps
- Integrate the DVL with ROS 2
- Publish velocity and range data
- Determine the desired coordinate frame
- Use DVL measurements in localization

Then save it and run:

```bash
git status
git add auv_dvl/read_dvl.py auv_dvl/README.md
git commit -m "Add Wayfinder DVL Python test"
git push -u origin add-wayfinder-dvl-test