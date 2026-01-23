# casictool

A command-line tool for configuring GPS receivers using the CASIC binary protocol.
[Zhongke Microsysystems](https://www.icofchina.com/) make a range of very inexpensive GPS receivers (ATGM332D, ATGM336H) which use this protocol.

If you have any problems, please open an issue.

## Caveats

This has been developed with extensive AI assistance (Claude Code Opus 4.5 mostly).
It works for me, but use with caution, particularly the options that affect non-volatile memory.

One of the main goals of this is to prototype support for CASIC in [SatPulse](https://satpulse.net).
When support for CASIC has been added to SatPulse, then the functionality of this tool will be available in `satpulsetool gps`; at that point I will no longer maintain this repository.

There needs to be some spare bandwidth between the GPS receiver and the host for this to work reliably.
If the speed is 9600 baud, then NMEA GSV sentences can use up most of the bandwidth, particularly if multiple constellations are enabled. On the tinyGTC, the internal connection to the GPS receiver is fixed at 9600 baud, so I recommend you enable only the GPS constellation before you try to run this.

If you are using tinyGTC, then I strongly recommend staying away from the options that affect non-volatile memory.
If you get the GPS into a state where it doesn't work, you can open the case (remove the four screws on the back), and detach the battery for a few seconds.

casictool can check that the receiver properly acknowledges the configuration message, and with `--show-config` you can check that the configured parameter was correctly stored, but there is no guarantee that the GPS receiver will actually use the configured parameter. For example, ATGM332D-5N31 and ATGM-336H-5N31 do not appear to make use of the parameter set by `--min-elev`.

## Installation

### Using pipx (recommended)

```bash
pipx install git+https://github.com/jclark/casictool.git
```

If you don't have pipx, [install it first](https://pipx.pypa.io/stable/installation/).

### From source

```bash
git clone https://github.com/jclark/casictool.git
cd casictool
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Then run with `casictool` while the virtual environment is active.

## Usage

See the [man page](man/casictool.1.md) for full details. The command-line interface is modelled after [satpulsetool gps](https://satpulse.net/man/satpulsetool-gps.1.html).

Run `casictool --help` for all options.

Here are some examples assuming the GPS receiver is connected to `/dev/ttyUSB0` at 9600 baud.

```bash
# Show current configuration
casictool -d /dev/ttyUSB0 -s 9600 --show-config

# Enable GPS and BeiDou constellations
casictool -d /dev/ttyUSB0 -s 9600 --gnss GPS,BDS

# Configure for time mode with survey-in
casictool -d /dev/ttyUSB0 -s 9600 --survey --survey-time 3600

# Set fixed position (ECEF coordinates in meters)
casictool -d /dev/ttyUSB0 -s 9600 --fixed-pos-ecef -2430000,4700000,3560000 --fixed-pos-acc 0.5

# Configure PPS output (pulse width in seconds)
casictool -d /dev/ttyUSB0 -s 9600 --pps 0.1 --time-gnss GPS
```

## CASIC binary protocol specification

As part of this exercise I got an AI (Gemini 3 Pro) to translate a Chinese PDF spec into [English](spec/README.md) in Markdown (convenient for input to an AI).

## Tested Hardware

- [StarRiver](http://sragps.com) [SR1612Z1](http://sragps.com/down/SR1612Z1%E8%A7%84%E6%A0%BC%E4%B9%A6.pdf) (uses AT6558D)
- [TinyGTC](https://www.tinydevices.org/wiki/pmwiki.php?n=TinyGTC.Homepage), which has an ATGM336H-5N31 (uses AT6558)
- ATGM332D-5N31 (uses AT6558) from [AliExpress](https://aliexpress.com/item/1005004402839841.html)