# CASICTool Implementation Plan

## Executive Summary

This document collates the findings from investigating the CASIC protocol documentation (casic2.md) to determine how to implement a GPS configuration tool (`casictool.py`) with a CLI modeled on `satpulsetool-gps`.

### Key Findings

1. **Supported Constellations**: GPS, BDS (BeiDou), GLONASS only - no Galileo, QZSS, NAVIC, or SBAS
2. **No Band Selection**: The CASIC protocol controls constellations, not individual frequency bands
3. **No RTCM Support**: RTCM output is not natively supported in the CASIC protocol
4. **Good Coverage**: PPS, timing, survey, position, message output, save/reset are well supported

---

## 1. CASIC Message Format

### Frame Structure
```
[0xBA][0xCE][Length:2][Class:1][ID:1][Payload:variable][Checksum:4]
```

| Field | Size | Description |
|-------|------|-------------|
| Header | 2 bytes | Sync bytes: 0xBA 0xCE |
| Length | 2 bytes | Payload length (little-endian) |
| Class | 1 byte | Message class |
| ID | 1 byte | Message ID |
| Payload | variable | Message data (< 2KB) |
| Checksum | 4 bytes | Cumulative sum |

### Checksum Algorithm
```python
def calc_checksum(class_id, msg_id, payload):
    length = len(payload)
    ck_sum = (msg_id << 24) + (class_id << 16) + length
    for i in range(0, len(payload), 4):
        word = int.from_bytes(payload[i:i+4], 'little')
        ck_sum = (ck_sum + word) & 0xFFFFFFFF
    return ck_sum
```

### Message Classes
| Class | ID | Name | Purpose |
|-------|-----|------|---------|
| NAV | 0x01 | Navigation | Position, velocity, time results |
| TIM | 0x02 | Timing | Time pulse information |
| RXM | 0x03 | Receiver | Raw measurements |
| ACK | 0x05 | Acknowledge | ACK/NAK responses |
| CFG | 0x06 | Configuration | All CFG- commands |
| MSG | 0x08 | Messages | Ephemeris, UTC, ionosphere |
| MON | 0x0A | Monitoring | Hardware status |
| AID | 0x0B | Assistance | Position/time assistance |

---

## 2. Query vs Set Operations

All CFG commands support both **Query** and **Set** operations:

| Operation | Payload Length | Description |
|-----------|----------------|-------------|
| **Query** | 0 bytes | Receiver responds with current configuration |
| **Set** | N bytes | Receiver applies the configuration |

**Query Protocol**:
1. Send CFG command with Class/ID but empty payload (length=0)
2. Receiver responds with same Class/ID containing current settings
3. Parse response payload to extract configuration values

**Example Query Sequence** (for `--show-config`):
```
Send:    [0xBA 0xCE] [0x00 0x00] [0x06 0x07] [checksum]  (CFG-NAVX query)
Receive: [0xBA 0xCE] [0x2C 0x00] [0x06 0x07] [44 bytes payload] [checksum]
```

**Commands to Query for --show-config**:
| Command | Class/ID | Information Returned |
|---------|----------|---------------------|
| CFG-PRT | 0x06 0x00 | Baud rate, protocol mode |
| CFG-NAVX | 0x06 0x07 | GNSS constellations, fix mode, accuracy settings |
| CFG-TP | 0x06 0x03 | PPS interval/width, time source, polarity |
| CFG-TMODE | 0x06 0x06 | Mode (auto/survey/fixed), position, survey params |
| CFG-RATE | 0x06 0x04 | Navigation update interval |
| CFG-GROUP | 0x06 0x08 | GLONASS group delays |

---

---

## 3. Option-to-Command Mapping

### Well Supported Options

| Option | CFG Command | Status |
|--------|-------------|--------|
| `--show-config` | Query all CFG commands | Fully supported |
| `--gnss` | CFG-NAVX (0x06 0x07) | Supported (GPS/BDS/GLO only) |
| `--time-gnss` | CFG-TP (0x06 0x03) | Fully supported |
| `--pps` | CFG-TP (0x06 0x03) | Fully supported |
| `--speed` | CFG-PRT (0x06 0x00) | Fully supported |
| `--save/--save-all` | CFG-CFG (0x06 0x05) | Fully supported |
| `--reload` | CFG-CFG (0x06 0x05) | Fully supported |
| `--reset` | CFG-RST (0x06 0x02) | Fully supported |
| `--factory-reset` | CFG-RST (0x06 0x02) | Fully supported |
| `--survey` | CFG-TMODE (0x06 0x06) | Fully supported |
| `--fixed-pos-ecef` | CFG-TMODE (0x06 0x06) | Fully supported |
| `--mobile` | CFG-TMODE (0x06 0x06) | Fully supported |
| `--pvt-out` | CFG-MSG (0x06 0x01) | Supported |
| `--sats-out` | CFG-MSG (0x06 0x01) | Supported |
| `--raw-out` | CFG-MSG (0x06 0x01) | Supported |
| `--nmea-out` | CFG-MSG (0x06 0x01) | Fully supported (Class 0x4E) |

### Not Supported / Limited

| Option | Status | Notes |
|--------|--------|-------|
| `--band` | NOT SUPPORTED | Protocol controls constellations, not bands |
| `--rtcm-out` | NOT SUPPORTED | No RTCM class in CASIC protocol |
| `--ant-cable-delay` | LIMITED | Only userDelay in CFG-TP (seconds, not nanoseconds) |

---

## 4. Detailed Command Specifications

### 4.1 CFG-PRT (0x06 0x00) - Serial Port Configuration

**Purpose**: Configure baud rate and protocol mode
**Options**: `--speed`

**Payload (Set, 8 bytes)**:
| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U1 | portID | 0=UART0, 1=UART1, 0xFF=current |
| 1 | U1 | protoMask | B0=BinaryIn, B1=TextIn, B4=BinaryOut, B5=TextOut |
| 2 | U2 | mode | Data/parity/stop bits |
| 4 | U4 | baudRate | Baud rate in bps |

**Mode Field**:
- Bits [7:6]: Data bits (11=8 bits)
- Bits [11:9]: Parity (100=none)
- Bits [12:11]: Stop bits (00=1 bit)
- Standard 8N1 = 0x0800

---

### 4.2 CFG-MSG (0x06 0x01) - Message Output Configuration

**Purpose**: Enable/disable specific message output
**Options**: `--pvt-out`, `--sats-out`, `--raw-out`, `--nmea-out`, `--binary`

**Payload (Set, 4 bytes)**:
| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U1 | clsID | Message class |
| 1 | U1 | msgID | Message ID |
| 2 | U2 | rate | 0=off, 1=every fix, N=every N fixes |

**Message Types for --nmea-out** (Class 0x4E):
| Flag | Class | ID | Message |
|------|-------|-----|---------|
| GGA | 0x4E | 0x00 | Receiver positioning data |
| GLL | 0x4E | 0x01 | Geographic position - Lat/Lon |
| GSA | 0x4E | 0x02 | DOP and active satellites |
| GSV | 0x4E | 0x03 | Visible satellites |
| RMC | 0x4E | 0x04 | Recommended minimum data |
| VTG | 0x4E | 0x05 | Course/speed over ground |
| ZDA | 0x4E | 0x08 | Time and Date |

**Message Types for --pvt-out** (Class 0x01 NAV):
| Flag | Class | ID | Message |
|------|-------|-----|---------|
| pos/vel | 0x01 | 0x03 | NAV-PV |
| time | 0x01 | 0x10 | NAV-TIMEUTC |
| tp | 0x02 | 0x00 | TIM-TP |
| leap | 0x01 | 0x11 | NAV-CLOCK |
| ecef | 0x01 | 0x02 | NAV-SOL |

**Message Types for --sats-out**:
| Flag | Class | ID | Message |
|------|-------|-----|---------|
| sat (GPS) | 0x01 | 0x20 | NAV-GPSINFO |
| sat (BDS) | 0x01 | 0x21 | NAV-BDSINFO |
| sat (GLO) | 0x01 | 0x22 | NAV-GLNINFO |

**Message Types for --raw-out**:
| Flag | Class | ID | Message |
|------|-------|-----|---------|
| obs | 0x03 | 0x10 | RXM-MEASX |
| nav (GPS) | 0x08 | 0x07 | MSG-GPSEPH |
| nav (BDS) | 0x08 | 0x02 | MSG-BDSEPH |
| nav (GLO) | 0x08 | 0x08 | MSG-GLNEPH |

---

### 4.3 CFG-RST (0x06 0x02) - Reset Receiver

**Purpose**: Reset receiver and clear data
**Options**: `--reset`, `--factory-reset`

**Payload (Set, 4 bytes)**:
| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U2 | navBbrMask | Data to clear (see below) |
| 2 | U1 | resetMode | 0=HW, 1=SW, 2=SW(GPS), 4=HW after shutdown |
| 3 | U1 | startMode | 0=Hot, 1=Warm, 2=Cold, 3=Factory |

**BBR Mask Bits**:
- B0: Ephemeris
- B1: Almanac
- B2: Health
- B3: Ionosphere
- B4: Position
- B5: Clock Drift
- B6: Osc Parameters
- B7: UTC Params
- B8: RTC
- B9: Config

**Implementation**:
- `--reset`: navBbrMask=0x01FF (clear all except config), startMode=2 (cold)
- `--factory-reset`: navBbrMask=0x03FF (clear all), startMode=3 (factory)

---

### 4.4 CFG-TP (0x06 0x03) - Time Pulse (PPS) Configuration

**Purpose**: Configure PPS output
**Options**: `--pps`, `--time-gnss`, `--ant-cable-delay` (limited)

**Payload (Set, 16 bytes)**:
| Offset | Type | Name | Unit | Description |
|--------|------|------|------|-------------|
| 0 | U4 | interval | us | Pulse interval (1000000 for 1Hz) |
| 4 | U4 | width | us | Pulse width |
| 8 | U1 | enable | | 0=Off, 1=On, 2=Auto, 3=FixOnly |
| 9 | I1 | polar | | 0=Rising, 1=Falling |
| 10 | U1 | timeRef | | 0=UTC, 1=Satellite |
| 11 | U1 | timeSource | | See below |
| 12 | R4 | userDelay | s | User delay compensation |

**timeSource Values** (for `--time-gnss`):
| Value | Constellation |
|-------|---------------|
| 0 | GPS |
| 1 | BDS |
| 2 | GLONASS |
| 4 | BDS (Main) |
| 5 | GPS (Main) |
| 6 | GLONASS (Main) |

**Implementation**:
- `--pps <width>`: Convert width (0-1 seconds) to microseconds, set enable=1
- `--pps 0`: Set enable=0 to disable
- `--time-gnss GPS`: Set timeSource=0 or 5

---

### 4.5 CFG-RATE (0x06 0x04) - Navigation Rate

**Purpose**: Set navigation/fix rate
**Options**: Affects output message timing

**Payload (Set, 4 bytes)**:
| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U2 | interval | Interval between fixes (ms) |
| 2 | U2 | reserved | Reserved |

---

### 4.6 CFG-CFG (0x06 0x05) - Save/Load Configuration

**Purpose**: Save/load/clear configuration to/from NVM
**Options**: `--save`, `--save-all`, `--reload`

**Payload (Set, 4 bytes)**:
| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U2 | mask | Config sections to affect |
| 2 | U1 | mode | 0=Clear, 1=Save, 2=Load |
| 3 | U1 | reserved | Reserved |

**Mask Bits**:
- B0: Port (CFG-PRT)
- B1: Msg (CFG-MSG)
- B2: INF (CFG-INF)
- B3: Rate (CFG-RATE/TMODE)
- B4: TP (CFG-TP)
- B5: Group Delay (CFG-GROUP)

**Implementation**:
- `--save`: mode=1, mask based on what was changed
- `--save-all`: mode=1, mask=0xFFFF
- `--reload`: mode=2, mask=0xFFFF

---

### 4.7 CFG-TMODE (0x06 0x06) - Timing Mode Configuration

**Purpose**: Configure survey-in or fixed position mode
**Options**: `--survey`, `--survey-time`, `--survey-acc`, `--fixed-pos-ecef`, `--fixed-pos-acc`, `--mobile`

**Payload (Set, 40 bytes)**:
| Offset | Type | Name | Unit | Description |
|--------|------|------|------|-------------|
| 0 | U4 | mode | | 0=Auto, 1=Survey-In, 2=Fixed |
| 4 | R8 | fixedPosX | m | ECEF X coordinate |
| 12 | R8 | fixedPosY | m | ECEF Y coordinate |
| 20 | R8 | fixedPosZ | m | ECEF Z coordinate |
| 28 | R4 | fixedPosVar | m² | Position variance |
| 32 | U4 | svinMinDur | s | Survey minimum duration |
| 36 | R4 | svinVarLimit | m² | Survey variance limit |

**Implementation**:
- `--survey`: mode=1, svinMinDur from `--survey-time` (default 2000), svinVarLimit from `--survey-acc²` (default 400)
- `--fixed-pos-ecef X,Y,Z`: mode=2, fixedPosX/Y/Z from args
- `--fixed-pos-acc M`: fixedPosVar = M²
- `--mobile`: mode=0

---

### 4.8 CFG-NAVX (0x06 0x07) - Navigation Engine Configuration

**Purpose**: Configure GNSS constellations and navigation parameters
**Options**: `--gnss`

**Payload (Set, 44 bytes)**:
| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U4 | mask | Parameter mask (which fields to set) |
| 4 | U1 | dyModel | Dynamic model |
| 5 | U1 | fixMode | Fix mode (1=2D, 2=3D, 3=Auto) |
| ... | ... | ... | ... |
| 13 | U1 | navSystem | **GNSS constellation mask** |
| ... | ... | ... | ... |

**navSystem Bits** (for `--gnss`):
| Bit | Constellation |
|-----|---------------|
| B0 | GPS |
| B1 | BDS (BeiDou) |
| B2 | GLONASS |

**Implementation**:
- `--gnss GPS,BDS,GLO`: navSystem = 0x07 (all enabled)
- `--gnss GPS`: navSystem = 0x01
- `--gnss GPS,BDS`: navSystem = 0x03

**Note**: Galileo, QZSS, NAVIC, SBAS are NOT supported by this receiver.

---

### 4.9 CFG-GROUP (0x06 0x08) - GLONASS Group Delay

**Purpose**: Configure GLONASS group delay parameters
**Payload**: 56 bytes (14 x R4 values)

---

## 5. ACK/NAK Handling

All CFG commands must wait for acknowledgment:

**ACK-ACK (0x05 0x01)** - Success
**ACK-NAK (0x05 0x00)** - Failure

**Payload (2 bytes)**:
| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | U1 | clsID | Class of acknowledged message |
| 1 | U1 | msgID | ID of acknowledged message |

---

## 6. Implementation Phases

### Phase 1: Core Infrastructure
1. CASIC message framing (header, checksum)
2. Serial port communication
3. ACK/NAK handling
4. Basic CLI structure with argparse

### Phase 2: Show Config
1. `--show-config` - Query CFG commands and display current settings

### Phase 3: NVM Operations
1. `--save` (CFG-CFG)
2. `--save-all` (CFG-CFG)
3. `--reload` (CFG-CFG)
4. `--reset` (CFG-RST)
5. `--factory-reset` (CFG-RST)

### Phase 4: NMEA Output
1. `--nmea-out` (CFG-MSG with class 0x4E)

### Phase 5: GNSS Configuration
1. `--gnss` (CFG-NAVX)

### Phase 6: Timing Mode
1. `--survey`, `--survey-time`, `--survey-acc` (CFG-TMODE)
2. `--fixed-pos-ecef`, `--fixed-pos-acc` (CFG-TMODE)
3. `--mobile` (CFG-TMODE)

### Phase 7: Time Pulse (PPS)
1. `--pps` (CFG-TP)
2. `--time-gnss` (CFG-TP)

---

## 7. Options Not Implementable

| Option | Reason |
|--------|--------|
| `--band` | CASIC controls constellations, not frequency bands |
| `--rtcm-out` | No RTCM message class in CASIC protocol |
| `--ant-cable-delay` | Only userDelay (seconds) in CFG-TP, not nanosecond precision |
| `--gnss GAL,QZSS,NAVIC,SBAS` | Receiver only supports GPS, BDS, GLONASS |

---

## 8. Data Type Reference

| Type | Size | Description |
|------|------|-------------|
| U1 | 1 byte | Unsigned 8-bit |
| I1 | 1 byte | Signed 8-bit |
| U2 | 2 bytes | Unsigned 16-bit, little-endian |
| I2 | 2 bytes | Signed 16-bit, little-endian |
| U4 | 4 bytes | Unsigned 32-bit, little-endian |
| I4 | 4 bytes | Signed 32-bit, little-endian |
| R4 | 4 bytes | IEEE 754 single-precision float |
| R8 | 8 bytes | IEEE 754 double-precision float |
