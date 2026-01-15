#!/usr/bin/env python3
"""CASIC GPS receiver configuration tool."""

from __future__ import annotations

import argparse
import sys

import serial

from casic import (
    CFG_NAVX,
    CFG_PRT,
    CFG_RATE,
    CFG_TMODE,
    CFG_TP,
    MON_VER,
    CasicConnection,
    ReceiverConfig,
    VersionInfo,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
    parse_mon_ver,
)


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

    args = parser.parse_args()

    if args.show_config:
        try:
            with CasicConnection(args.device, baudrate=args.speed) as conn:
                # Probe receiver first
                is_casic, version = probe_receiver(conn)
                if not is_casic:
                    print("Error: No response from receiver. Not a CASIC device?", file=sys.stderr)
                    return 1
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

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
