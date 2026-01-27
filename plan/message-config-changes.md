# Message Configuration Strategy Changes

## Summary

Changed casictool's message configuration approach to stop relying on CFG-MSG polling (which doesn't work universally on all receivers).

## Changes Made

### Phase 1: Track Seen Messages (connection.py)
- Added `_seen_messages` dict to track individual NMEA and CASIC message types
- Modified `_log_event()` to extract and record message types (strips talker ID from NMEA like "GNGGA" → "GGA")
- Added `seen_messages` property to expose tracked messages

### Phase 2: Update --show-config (job.py, casic.py)
- Created new `SeenMessagesConfig` dataclass replacing `MessageRatesConfig`
- Updated `ReceiverConfig` to use `seen_messages` instead of `message_rates`
- Modified `query_config()` to populate seen messages from connection instead of polling CFG-MSG
- Removed `query_nmea_rates()` function (no longer needed)
- Updated `query_config_props()` to remove nmea_out/casic_out querying
- Updated casic_hwtest.py to use seen_messages verification for message tests

### Phase 3: Simplify --nmea-out (job.py)
- Removed rate querying in `set_nmea_output()`
- Now unconditionally sends CFG-MSG SET for all 7 NMEA messages from the fixed list (GGA, GLL, GSA, GSV, RMC, VTG, ZDA)

### Phase 4: Update --casic-out Syntax (casictool.py, job.py)
- Changed `parse_casic_out()` to return `dict[str, bool]` instead of `set[str]`
- Supports `-MSG` prefix to disable messages (e.g., `--casic-out TIM-TP,-NAV-SOL`)
- Removed "none" support
- Only affects explicitly listed messages (others unchanged)
- Updated `ConfigProps` type hint

### Phase 5: Documentation (man/casictool.1.src.md)
- Updated `--show-config` description to mention seen messages
- Updated `--casic-out` description with new prefix syntax
- Added example: `--casic-out TIM-TP,-NAV-SOL`

## New Behavior

### --show-config
Shows messages that have been **seen** during the session, not queried rates:
```
NMEA messages seen: GGA, RMC, GSA
CASIC messages seen: NAV-SOL, TIM-TP
```

### --nmea-out
Works from fixed list of 7 NMEA messages. Messages in the list are enabled, others disabled:
```bash
casictool --nmea-out GGA,RMC  # enables GGA, RMC; disables GLL, GSA, GSV, VTG, ZDA
casictool --nmea-out none     # disables all NMEA messages
```

### --casic-out
Only affects explicitly listed messages. Use `-` prefix to disable:
```bash
casictool --casic-out TIM-TP           # enables TIM-TP only
casictool --casic-out -NAV-SOL         # disables NAV-SOL only
casictool --casic-out TIM-TP,-NAV-SOL  # enables TIM-TP, disables NAV-SOL
```

## Files Modified

- `connection.py` - Added individual message tracking
- `job.py` - Removed rate querying, simplified set_nmea_output, updated casic_out handling
- `casictool.py` - Updated `--casic-out` parser for new syntax
- `casic.py` - Added `SeenMessagesConfig`, updated `ReceiverConfig`
- `casic_hwtest.py` - Updated tests to use seen_messages verification
- `man/casictool.1.src.md` - Updated documentation
