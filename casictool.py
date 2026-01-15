#!/usr/bin/env python3
"""CASIC GPS receiver configuration tool."""

from __future__ import annotations

import argparse
import sys


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
        print(f"Would show config from {args.device} at {args.speed} baud")
        print("(Not yet implemented)")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
