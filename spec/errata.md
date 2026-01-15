# CASIC Protocol Errata

This document records differences between the CASIC protocol specification and observed receiver behavior.

## Tested Hardware

- SR1612Z1

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

