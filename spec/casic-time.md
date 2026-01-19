# CASIC binary time-related capabilities

The following time-related information is available from CASIC binary messages but not NMEA/PCAS messages:

- TAI time (NAV-SOL: week, tow; TIM-TP: wn, tow)
- Leap seconds for each GNSS (NAV-CLOCK: leaps)
- Nanosecond delta between UTC and GNSS time (NAV-CLOCK: dtUtc)
- Estimated time accuracy (NAV-TIMEUTC: tAcc)
- Time dilution of precision (NAV-DOP: tDop)
- Which GNSS provided time (NAV-SOL: timeSrc; NAV-TIMEUTC: timeSrc)
- Whether time/date is trustworthy (NAV-TIMEUTC: valid, dateValid)

The following time-related capabilities can be configured using CASIC binary messages:

- Time mode: auto, survey-in, or fixed position (CFG-TMODE)
- Which GNSS time should the PPS signal be aligned to (CFG-TP: timeSource)