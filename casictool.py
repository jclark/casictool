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
    CasicConnection,
    ReceiverConfig,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
)


def show_config(conn: CasicConnection) -> ReceiverConfig:
    """Query all CFG messages and return receiver configuration."""
    config = ReceiverConfig()

    # Query CFG-PRT
    payload = conn.poll(CFG_PRT.cls, CFG_PRT.id)
    if payload is not None:
        config.port = parse_cfg_prt(payload)
    else:
        print("Warning: CFG-PRT query timed out", file=sys.stderr)

    # Query CFG-RATE
    payload = conn.poll(CFG_RATE.cls, CFG_RATE.id)
    if payload is not None:
        config.rate = parse_cfg_rate(payload)
    else:
        print("Warning: CFG-RATE query timed out", file=sys.stderr)

    # Query CFG-TP
    payload = conn.poll(CFG_TP.cls, CFG_TP.id)
    if payload is not None:
        config.time_pulse = parse_cfg_tp(payload)
    else:
        print("Warning: CFG-TP query timed out", file=sys.stderr)

    # Query CFG-TMODE
    payload = conn.poll(CFG_TMODE.cls, CFG_TMODE.id)
    if payload is not None:
        config.timing_mode = parse_cfg_tmode(payload)
    else:
        print("Warning: CFG-TMODE query timed out", file=sys.stderr)

    # Query CFG-NAVX
    payload = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if payload is not None:
        config.nav_engine = parse_cfg_navx(payload)
    else:
        print("Warning: CFG-NAVX query timed out", file=sys.stderr)

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
