# NAME

casictool - configure a GPS receiver using CASIC protocol

# SYNOPSIS

**casictool** \[**-h**\|**--help**\]

\[**-d**\|**--device** *path*\] \[**-s**\|**--device-speed** *bps*\]

\[**--packet-log** *path*\]

\[**--show-config**\]

\[**--save**\] \[**--save-all**\] \[**--reset**\] \[**--reload**\]
\[**--factory-reset**\]

\[**-g**\|**--gnss** **GPS**\|**GAL**\|**BDS**\|**GLO**,...\]

\[**--time-gnss** **GPS**\|**GAL**\|**BDS**\|**GLO**\]

\[**--pps** *width*\]

\[**--mobile**\] \[**--fixed-pos-ecef** *X,Y,Z*\] \[**--fixed-pos-acc**
*meters*\]

\[**--survey**\] \[**--survey-time** *seconds*\] \[**--survey-acc**
*meters*\]

\[**--nmea-out**
**none**\|**GGA**\|**GLL**\|**GSA**\|**GSV**\|**RMC**\|**VTG**\|**ZDA**,...\]

\[**--casic-out** *messages*\]

# DESCRIPTION

The **casictool** command is used to configure a GPS receiver using the
CASIC protocol.

# OPTIONS

**-h**, **--help**  
Show usage help.

**--show-config**  
Show the current configuration of the GPS receiver.

**-d**, **--device** *path*  
Path to the serial device to communicate with the GPS receiver.

**-s**, **--device-speed** *bps*  
Set the speed of the serial port (as specified by **-d**) in bits per
second.

**--packet-log** *path*  
Log to *path* a description of the packets sent to and received from the
GPS receiver. The log is in `.jsonl` (JSON lines) format.

**-g**, **--gnss** *list*  
List of GNSS constellations that should be enabled. The *list* parameter
is a comma-separated list of:

**GPS**  
Global Positioning System (United States)

**GAL** or **Galileo**  
Galileo (European Union)

**BDS** or **BeiDou**  
BeiDou Navigation Satellite System (China)

**GLO** or **GLONASS**  
Global Navigation Satellite System (Russia)

**--time-gnss** *constellation*  
GNSS constellation used for timing purposes. The PPS signal is aligned
to the system time of this GNSS. (The system times of different GNSSs
can differ by tens of nanoseconds.) Valid values are GPS, GAL, BDS, and
GLO.

**--save**  
Save the configuration changed by this command to GPS receiver’s
non-volatile memory. Exactly what is saved depends on the specific GPS
receiver; casictool will save the minimum possible to ensure that
everything that was changed by this command is saved.

**--save-all**  
Save the current running configuration of the GPS receiver to its
non-volatile memory.

**--reload**  
Reloads the configuration of the GPS receiver from its non-volatile
memory. Any configuration settings that have not been saved will be
lost.

**--reset**  
Perform a reset that reloads the configuration of the GPS receiver from
its non-volatile memory (as with the **-reload** option), and discards
information about the last known position, current time, and satellite
orbital data (both ephemeris and almanac).

**--factory-reset**  
Restore the non-volatile memory of the GPS receiver to its default
settings, and the perform a reset as with the **--reset** option.

**--pps** *width*  
Configure the GPS receiver to enable a pulse-per-second (PPS) signal
with the specified pulse width in seconds. The *width* must be \>= 0 and
\<= 1.0. A width of 0 disables the PPS signal.

**--nmea-out** *flags*  
Configure NMEA message output. The *flags* parameter is a
comma-separated list of message names. Messages not in the list will be
disabled. Use **none** to disable all NMEA messages.

**GGA**  
Enable GGA (Global Positioning System Fix Data) messages

**GLL**  
Enable GLL (Geographic Position - Latitude/Longitude) messages

**GSA**  
Enable GSA (DOP and Active Satellites) messages

**GSV**  
Enable GSV (Satellites in View) messages

**RMC**  
Enable RMC (Recommended Minimum) messages

**VTG**  
Enable VTG (Vector Track Made Good) messages

**ZDA**  
Enable ZDA (Time and Date) messages

**--casic-out** *messages*  
Configure CASIC binary message output. The *messages* parameter is a
comma-separated list of message names (e.g., **TIM-TP,NAV-SOL**).
Messages not in the list will be disabled. Message names are
case-insensitive. Use **none** to disable all CASIC binary messages.

**--survey**  
Perform a survey to determine the position of the antenna, and then run
in a mode that assumes the position of the antenna does not change. The
survey makes measurements for a period of time and then computes the
position based on those measurements.

**--survey-time** *seconds*  
Set duration of the position survey (default: 2000).

**--survey-acc** *meters*  
Required survey accuracy in meters (default: 20.0). Minimum value is
0.001 (1 mm).

**--fixed-pos-ecef** *X,Y,Z*  
Use the specified coordinates as the fixed position of the antenna, and
then run in a mode that assumes the position of the antenna does not
change. The coordinates are comma-separated X, Y, and Z coordinates in
meters in the Earth-Centered, Earth-Fixed coordinate system.

**--fixed-pos-acc** *meters*  
Set the accuracy of the fixed position in meters (default: 20.0). This
value should reflect the actual uncertainty in the fixed position
coordinates. Minimum value is 0.001 (1 mm).

**--mobile**  
Run in a normal mode, where the position of the antenna may change. This
undoes the effect of **--survey** or **--fixed-pos-ecef**.

# EXAMPLES

Enable GPS and Galileo on `/dev/ttyACM0` at 9600 baud:

    casictool -d /dev/ttyACM0 -s 9600 -g GPS,GAL

Start a survey for 3000 seconds with 1.5m accuracy:

    casictool --survey --survey-time 3000 --survey-acc 1.5 -d /dev/ttyUSB0 -s 38400

Reset the receiver to factory defaults:

    casictool -d /dev/ttyUSB0 -s 38400 --factory-reset

Enable only NMEA RMC messages:

    casictool -d /dev/ttyACM0 -s 19200 --nmea-out RMC

Enable TIM-TP binary message output:

    casictool -d /dev/ttyUSB0 -s 38400 --casic-out TIM-TP

# AUTHORS

James Clark.
