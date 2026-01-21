# Notes on CASIC Protocol

This document notes points discovered while implementing, where either receiver behaviour differs from the specification or where the specification is unclear.

## Checksum Calculation

**Spec says:**
```
ckSum = (class << 24) + (id << 16) + len;
```

**Receiver actually uses:**
```
ckSum = (id << 24) + (class << 16) + len;
```

The class and id bytes are swapped in the checksum calculation compared to what the spec documents.

## MON-VER Support

The MON-VER (0x0A 0x04) query message is not supported on all receivers. Some receivers respond with ACK-NAK instead of the version information. The tool handles this by accepting a NAK as proof that the device speaks CASIC protocol.

## CFG-PRT Query

**Spec says:**
- Query Message: Length = 0

**Observed behavior:**
- Sending CFG-PRT (0x06 0x00) with an empty payload causes the receiver to respond with multiple CFG-PRT messages, one for each UART port (UART0, UART1)
- Each response is 8 bytes with the standard CFG-PRT format, where portID indicates which port (0 or 1)
- The spec does not document that multiple responses are returned

## CFG-MSG Query

**Spec says:**
- Query Message: Length = 0

**Observed behavior:**
- Sending CFG-MSG (0x06 0x01) with an empty payload causes the receiver to respond with multiple CFG-MSG messages, one for each configured message type
- Each response is 4 bytes: cls (U1), id (U1), rate (U2)
- Sending CFG-MSG with a 2-byte payload (cls, id) to query a specific message results in ACK-NAK
- The spec does not document the query response format or that it returns all message rates at once

## CFG-TP timeSource Field

The timeSource field in CFG-TP has two modes per constellation:

| Value | Description |
|-------|-------------|
| 0 | GPS |
| 1 | BDS |
| 2 | GLONASS |
| 4 | BDS (mainly) - prefer BDS, auto-fallback to others if unavailable |
| 5 | GPS (mainly) - prefer GPS, auto-fallback to others if unavailable |
| 6 | GLONASS (mainly) - prefer GLONASS, auto-fallback to others if unavailable |

## CFG-TMODE Mode Field

**Spec says:**
- mode: U4 (0=Auto, 1=Survey-In, 2=Fixed)

**Observed behavior:**
- The receiver returns unknown values in the upper 2 bytes of the mode field
- Example: Setting mode=2 (Fixed) and reading back gives `02 00 54 e3` instead of `02 00 00 00`
- The lower 2 bytes correctly contain the mode value (0, 1, or 2)
- The upper 2 bytes contain unknown/undocumented data

**Workaround:**
- Parse as U2 mode + U2 reserved instead of U4
- When building the payload, set reserved to 0

## NMEA Message Emission Order

NMEA messages are emitted in a fixed order: GGA, GSV, RMC, ZDA. The order in which messages are enabled does not affect emission order.

## Unimplemented Message Types (ATGM332D-5N31)

The following message types are ACKed when enabled via CFG-MSG but never actually output by the receiver:

- MSG-BDSUTC, MSG-BDSION, MSG-BDSEPH
- MSG-GPSUTC, MSG-GPSION, MSG-GPSEPH
- MSG-GLNEPH
- RXM-MEASX, RXM-SVPOS

RXM-SENSOR is NAKed (not supported at all).

## PCAS06 Query Response Formats

The spec documents what each PCAS06 info value queries but not the response format. Responses are GPTXT sentences with identifier 02 (notification).

| info | Documented As | Response Format | Example |
|------|---------------|-----------------|---------|
| 0 | Firmware version | SW= | `SW=URANUS5,V5.3.0.0` |
| 1 | Hardware model/Serial | HW= | `HW=AT6558D,0000000000000` |
| 2 | Working mode | MO= | `MO=GB` |
| 3 | Customer ID | CI= | `CI=01B94154` |
| 4 | - | (no response) | - |
| 5 | Upgrade code info | BS= | `BS=SOC_BootLoader,V6.2.0.2` |
| 6 | **Undocumented** | IC= | `IC=AT6558D-5N-32-1C520900,AJ03DHL-C1-002138` |

Notes:
- info=6 returns detailed chip variant and serial number (more useful than info=1)
- The chip self-reports as "5N-32" while the module label says "5N-31"
- info=1 HW= serial field may be all zeros; info=6 IC= has the real serial

## NAV-TIMEUTC tAcc Field

**Spec says:**
- tAcc: R4, scale 1/c², unit s²

**Interpretation:**
The scale factor `1/c²` means the raw float value must be divided by the speed of light squared to get the variance in seconds².

c = 299,792,458 m/s

**Worked example:**
Raw packet payload (hex): `757d9a035359814080e749b50000ea070115002a38070003`

tAcc bytes (offset 4-7): `53598140` → float 4.042 (little-endian)

Actual variance: 4.042 / (299792458)² ≈ 4.5 × 10⁻¹⁷ s²

Time accuracy (1σ): √(4.5 × 10⁻¹⁷) ≈ 6.7 ns

## NAV-SOL Week Number with GLONASS Timing

When `timeSrc=2` (GLONASS) in NAV-SOL, the `week` and `tow` fields use a different epoch than GPS time.

**GPS epoch:** January 6, 1980 (Sunday)
**GLONASS epoch used by receiver:** December 31, 1995 (Sunday)

The offset is exactly 834 weeks (16 years).

**Worked example:**
NAV-SOL payload reports: week=1568, tow=262219s, timeSrc=2

Using GLONASS epoch (Dec 31, 1995):
- 1568 weeks + 262219 seconds = January 21, 2026, 00:50:19 UTC ✓

Using GPS epoch (Jan 6, 1980):
- 1568 weeks + 262219 seconds = January 27, 2010 ✗

The NMEA RMC sentence from the same capture confirms the correct date: `$GNRMC,005019.000,A,...,210126,...`

**Note:** Native GLONASS time uses a 4-year cycle (the N₄ parameter) with day numbers (Nₜ), not weeks. The receiver converts this internally to a week/TOW format for consistency with GPS-style output. The December 31, 1995 epoch aligns with the start of the GLONASS N₄ four-year interval counter (defined as starting from 1996 in the GLONASS ICD), adjusted to the preceding Sunday since GPS weeks start on Sunday. This is not a native GLONASS representation but is the most reasonable way to express GLONASS time as week number + TOW.

