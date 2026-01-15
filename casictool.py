#!/usr/bin/env python3
"""CASIC GPS receiver configuration tool."""

from __future__ import annotations

import argparse
import sys

import serial

from casic import (
    BBR_ALL,
    BBR_NAV_DATA,
    CFG_CFG,
    CFG_MASK_ALL,
    CFG_MASK_MSG,
    CFG_MASK_RATE,
    CFG_MSG,
    CFG_NAVX,
    CFG_PRT,
    CFG_RATE,
    CFG_RST,
    CFG_TMODE,
    CFG_TP,
    MON_VER,
    NMEA_MESSAGES,
    CasicConnection,
    MessageRatesConfig,
    ReceiverConfig,
    VersionInfo,
    build_cfg_cfg,
    build_cfg_msg_set,
    build_cfg_rst,
    build_cfg_tmode,
    parse_cfg_msg,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
    parse_mon_ver,
)


class ConfigChanges:
    """Track which configuration sections were modified."""

    def __init__(self) -> None:
        self.mask = 0

    def mark_rate(self) -> None:
        """Mark rate/timing mode configuration as changed."""
        self.mask |= CFG_MASK_RATE

    def mark_msg(self) -> None:
        """Mark message output configuration as changed."""
        self.mask |= CFG_MASK_MSG


def save_config(conn: CasicConnection, mask: int) -> bool:
    """Save configuration sections to NVM."""
    payload = build_cfg_cfg(mask, mode=1)  # mode=1 is Save
    return conn.send_and_wait_ack(CFG_CFG.cls, CFG_CFG.id, payload)


def load_config(conn: CasicConnection, mask: int) -> bool:
    """Load configuration sections from NVM."""
    payload = build_cfg_cfg(mask, mode=2)  # mode=2 is Load
    return conn.send_and_wait_ack(CFG_CFG.cls, CFG_CFG.id, payload)


def reset_receiver(conn: CasicConnection, factory: bool = False) -> None:
    """Reset the receiver.

    Args:
        factory: If True, perform factory reset (clears NVM config).
                 If False, perform cold start (preserves NVM config).
    """
    if factory:
        nav_bbr_mask = BBR_ALL  # Clear everything including config
        start_mode = 3  # Factory Start
    else:
        nav_bbr_mask = BBR_NAV_DATA  # Clear nav data, preserve config
        start_mode = 2  # Cold Start

    reset_mode = 1  # Controlled Software Reset
    payload = build_cfg_rst(nav_bbr_mask, reset_mode, start_mode)

    # Note: After reset, receiver may not send ACK before restarting
    # We send the command without waiting for ACK
    conn.send(CFG_RST.cls, CFG_RST.id, payload)


def probe_receiver(conn: CasicConnection) -> tuple[bool, VersionInfo | None]:
    """Probe receiver with MON-VER to verify it's a CASIC device.

    Returns (is_casic, version_info). A NAK response proves it's CASIC
    even if MON-VER isn't supported.
    """
    result = conn.poll(MON_VER.cls, MON_VER.id)
    if result.success:
        return True, parse_mon_ver(result.payload)  # type: ignore[arg-type]
    if result.nak:
        return True, None  # NAK proves it's CASIC
    return False, None  # Timeout - not CASIC


def query_nmea_rates(conn: CasicConnection) -> MessageRatesConfig:
    """Query NMEA message output rates via CFG-MSG.

    CFG-MSG query with empty payload returns all configured message rates.
    Each response is 4 bytes: cls, id, rate (U2).
    """
    # Build lookup from (cls, id) -> name for NMEA messages we care about
    nmea_lookup = {(msg.cls, msg.id): name for name, msg in NMEA_MESSAGES}

    rates: dict[str, int] = {}
    conn.send(CFG_MSG.cls, CFG_MSG.id, b"")

    # Collect all CFG-MSG responses
    while True:
        result = conn.receive(timeout=0.3)
        if result is None:
            break
        recv_id, recv_payload = result
        if recv_id.cls == CFG_MSG.cls and recv_id.id == CFG_MSG.id and len(recv_payload) >= 4:
            msg_cls, msg_id, rate = recv_payload[0], recv_payload[1], parse_cfg_msg(recv_payload)
            name = nmea_lookup.get((msg_cls, msg_id))
            if name:
                rates[name] = rate

    return MessageRatesConfig(rates=rates)


def set_nmea_message_rate(conn: CasicConnection, message_name: str, rate: int) -> bool:
    """Set output rate for a specific NMEA message.

    Args:
        conn: Active CASIC connection
        message_name: NMEA message name (GGA, RMC, etc.)
        rate: Output rate (0=disable, 1+=enable at rate)

    Returns:
        True if acknowledged, False on failure
    """
    # Lookup message ID from name
    nmea_lookup = {name: msg for name, msg in NMEA_MESSAGES}
    msg = nmea_lookup.get(message_name.upper())
    if msg is None:
        return False

    payload = build_cfg_msg_set(msg.cls, msg.id, rate)
    return conn.send_and_wait_ack(CFG_MSG.cls, CFG_MSG.id, payload)


def show_config(conn: CasicConnection) -> ReceiverConfig:
    """Query all CFG messages and return receiver configuration."""
    config = ReceiverConfig()

    # Query CFG-PRT
    result = conn.poll(CFG_PRT.cls, CFG_PRT.id)
    if result.success:
        config.port = parse_cfg_prt(result.payload)  # type: ignore[arg-type]

    # Query CFG-RATE
    result = conn.poll(CFG_RATE.cls, CFG_RATE.id)
    if result.success:
        config.rate = parse_cfg_rate(result.payload)  # type: ignore[arg-type]

    # Query NMEA message rates via CFG-MSG
    config.message_rates = query_nmea_rates(conn)

    # Query CFG-TP
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if result.success:
        config.time_pulse = parse_cfg_tp(result.payload)  # type: ignore[arg-type]

    # Query CFG-TMODE
    result = conn.poll(CFG_TMODE.cls, CFG_TMODE.id)
    if result.success:
        config.timing_mode = parse_cfg_tmode(result.payload)  # type: ignore[arg-type]

    # Query CFG-NAVX
    result = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if result.success:
        config.nav_engine = parse_cfg_navx(result.payload)  # type: ignore[arg-type]

    return config


def parse_ecef_coords(coord_str: str) -> tuple[float, float, float]:
    """Parse comma-separated ECEF coordinates."""
    parts = coord_str.split(",")
    if len(parts) != 3:
        raise ValueError("ECEF coordinates must be X,Y,Z (3 values)")
    return (float(parts[0].strip()), float(parts[1].strip()), float(parts[2].strip()))


VALID_NMEA_MESSAGES = {"GGA", "GLL", "GSA", "GSV", "RMC", "VTG", "ZDA"}


def parse_nmea_out(nmea_str: str) -> list[str]:
    """Parse --nmea-out argument into list of messages to enable.

    Args:
        nmea_str: Comma-separated message list (e.g., "GGA,RMC,ZDA")

    Returns:
        List of message names to enable (all others will be disabled)
    """
    enable = []

    for item in nmea_str.split(","):
        item = item.strip().upper()
        if not item:
            continue
        if item in VALID_NMEA_MESSAGES:
            enable.append(item)
        else:
            raise ValueError(f"Unknown NMEA message: {item}")

    return enable


def set_survey_mode(conn: CasicConnection, min_dur: int, acc: float) -> bool:
    """Configure receiver for survey-in mode."""
    payload = build_cfg_tmode(
        mode=1,  # Survey-In
        survey_min_dur=min_dur,
        survey_acc=acc,
    )
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def set_fixed_position(
    conn: CasicConnection,
    ecef: tuple[float, float, float],
    acc: float,
) -> bool:
    """Configure receiver with fixed ECEF position."""
    payload = build_cfg_tmode(
        mode=2,  # Fixed
        fixed_pos=ecef,
        fixed_pos_acc=acc,
    )
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def set_mobile_mode(conn: CasicConnection) -> bool:
    """Configure receiver for mobile/auto mode."""
    payload = build_cfg_tmode(mode=0)  # Auto
    return conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload)


def main() -> int:
    """Main entry point for casictool CLI."""
    parser = argparse.ArgumentParser(
        description="CASIC GPS receiver configuration tool",
        prog="casictool",
    )

    parser.add_argument(
        "-d", "--device", default="/dev/ttyUSB0", help="Serial device (default: /dev/ttyUSB0)"
    )
    parser.add_argument(
        "-s", "--speed", type=int, default=9600, help="Baud rate (default: 9600)"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Show current configuration"
    )

    # Timing mode group
    timing_group = parser.add_argument_group("Timing Mode")
    timing_group.add_argument(
        "--survey", action="store_true", help="Enable survey-in mode"
    )
    timing_group.add_argument(
        "--survey-time",
        type=int,
        default=2000,
        metavar="SECS",
        help="Survey-in minimum duration in seconds (default: 2000)",
    )
    timing_group.add_argument(
        "--survey-acc",
        type=float,
        default=20.0,
        metavar="METERS",
        help="Survey-in target accuracy in meters (default: 20)",
    )
    timing_group.add_argument(
        "--fixed-pos-ecef",
        type=str,
        metavar="X,Y,Z",
        help="Set fixed ECEF position (meters, comma-separated)",
    )
    timing_group.add_argument(
        "--fixed-pos-acc",
        type=float,
        default=1.0,
        metavar="METERS",
        help="Fixed position accuracy in meters (default: 1)",
    )
    timing_group.add_argument(
        "--mobile", action="store_true", help="Enable mobile/auto mode (disable timing mode)"
    )

    # NMEA message output group
    nmea_group = parser.add_argument_group("NMEA Message Output")
    nmea_group.add_argument(
        "--nmea-out",
        type=str,
        metavar="MSGS",
        help="Set NMEA message output. Comma-separated list of messages to enable "
        "(GGA,GLL,GSA,GSV,RMC,VTG,ZDA). Messages not listed will be disabled.",
    )

    # NVM operations group
    nvm_group = parser.add_argument_group("Configuration Storage")
    nvm_group.add_argument(
        "--save",
        action="store_true",
        help="Save configuration changed by this command to NVM",
    )
    nvm_group.add_argument(
        "--save-all",
        action="store_true",
        help="Save all current configuration to NVM",
    )
    nvm_group.add_argument(
        "--reload",
        action="store_true",
        help="Reload configuration from NVM (discard unsaved changes)",
    )
    nvm_group.add_argument(
        "--reset",
        action="store_true",
        help="Cold start: reload from NVM and clear navigation data",
    )
    nvm_group.add_argument(
        "--factory-reset",
        action="store_true",
        help="Factory reset: restore NVM to defaults and reset receiver",
    )

    args = parser.parse_args()

    # Check mutual exclusivity of timing mode options
    mode_options = [args.survey, args.fixed_pos_ecef, args.mobile]
    if sum(bool(x) for x in mode_options) > 1:
        print(
            "Error: --survey, --fixed-pos-ecef, and --mobile are mutually exclusive",
            file=sys.stderr,
        )
        return 1

    # Check mutual exclusivity of save options
    if args.save and args.save_all:
        print("Error: --save and --save-all are mutually exclusive", file=sys.stderr)
        return 1

    # Check mutual exclusivity of reset options
    reset_options = [args.reload, args.reset, args.factory_reset]
    if sum(bool(x) for x in reset_options) > 1:
        print(
            "Error: --reload, --reset, and --factory-reset are mutually exclusive",
            file=sys.stderr,
        )
        return 1

    # Parse fixed position before opening connection
    ecef = None
    if args.fixed_pos_ecef:
        try:
            ecef = parse_ecef_coords(args.fixed_pos_ecef)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Parse NMEA output configuration before opening connection
    nmea_enable: list[str] = []
    if args.nmea_out:
        try:
            nmea_enable = parse_nmea_out(args.nmea_out)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Track configuration changes for --save
    changes = ConfigChanges()

    # Determine if any operation requires a connection
    has_timing_op = args.survey or args.fixed_pos_ecef or args.mobile
    has_nmea_op = args.nmea_out is not None
    has_nvm_op = args.save or args.save_all or args.reload or args.reset or args.factory_reset
    has_any_op = has_timing_op or has_nmea_op or has_nvm_op or args.show_config

    if not has_any_op:
        parser.print_help()
        return 0

    try:
        with CasicConnection(args.device, baudrate=args.speed) as conn:
            # Probe receiver first (except for reset operations which don't need it)
            version = None
            if not (args.factory_reset or args.reset):
                is_casic, version = probe_receiver(conn)
                if not is_casic:
                    print(
                        "Error: No response from receiver. Not a CASIC device?",
                        file=sys.stderr,
                    )
                    return 1

            # Execute timing mode configuration (and track changes)
            if args.survey:
                if set_survey_mode(conn, args.survey_time, args.survey_acc):
                    print(
                        f"Survey-in mode enabled: {args.survey_time}s, "
                        f"{args.survey_acc}m accuracy"
                    )
                    changes.mark_rate()
                else:
                    print("Error: Failed to set survey-in mode", file=sys.stderr)
                    return 1

            if ecef is not None:
                if set_fixed_position(conn, ecef, args.fixed_pos_acc):
                    print(
                        f"Fixed position set: ECEF ({ecef[0]:.3f}, {ecef[1]:.3f}, {ecef[2]:.3f})"
                    )
                    changes.mark_rate()
                else:
                    print("Error: Failed to set fixed position", file=sys.stderr)
                    return 1

            if args.mobile:
                if set_mobile_mode(conn):
                    print("Mobile/auto mode enabled")
                    changes.mark_rate()
                else:
                    print("Error: Failed to set mobile mode", file=sys.stderr)
                    return 1

            # Execute NMEA message output configuration
            if args.nmea_out is not None:
                enable_set = set(nmea_enable)
                # Enable specified messages, disable all others
                for msg_name in VALID_NMEA_MESSAGES:
                    if msg_name in enable_set:
                        if set_nmea_message_rate(conn, msg_name, 1):
                            print(f"Enabled {msg_name}")
                            changes.mark_msg()
                        else:
                            print(f"Error: Failed to enable {msg_name}", file=sys.stderr)
                            return 1
                    else:
                        if set_nmea_message_rate(conn, msg_name, 0):
                            print(f"Disabled {msg_name}")
                            changes.mark_msg()
                        else:
                            print(f"Error: Failed to disable {msg_name}", file=sys.stderr)
                            return 1

            # Execute NVM save operations (after configuration changes)
            if args.save_all:
                if save_config(conn, CFG_MASK_ALL):
                    print("All configuration saved to NVM")
                else:
                    print("Error: Failed to save configuration", file=sys.stderr)
                    return 1
            elif args.save:
                if changes.mask == 0:
                    print("Warning: No configuration changes to save")
                else:
                    if save_config(conn, changes.mask):
                        print("Configuration saved to NVM")
                    else:
                        print("Error: Failed to save configuration", file=sys.stderr)
                        return 1

            # Execute reload/reset operations (after save)
            if args.reload:
                if load_config(conn, CFG_MASK_ALL):
                    print("Configuration reloaded from NVM")
                else:
                    print("Error: Failed to reload configuration", file=sys.stderr)
                    return 1

            if args.factory_reset:
                reset_receiver(conn, factory=True)
                print("Factory reset initiated")

            if args.reset:
                reset_receiver(conn, factory=False)
                print("Cold start reset initiated")

            # Show configuration (only if no other operations)
            if args.show_config and not has_timing_op and not has_nmea_op and not has_nvm_op:
                if version:
                    print(f"CASIC receiver: {version.sw_version} / {version.hw_version}")
                else:
                    print("CASIC receiver detected (MON-VER not supported)")
                print()
                config = show_config(conn)
                print(config.format())

    except serial.SerialException as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
