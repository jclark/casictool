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
