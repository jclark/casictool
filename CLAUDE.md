# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

casictool is a CLI tool for configuring CASIC GPS receivers, modeled on satpulsetool-gps. CASIC receivers support GPS, BeiDou, and GLONASS constellations (no Galileo, QZSS, NAVIC, or SBAS). The protocol has two layers: text-based NMEA commands and binary CASIC messages.

## Development Commands

```bash
make dev-deps     # Install package in editable mode with dev dependencies
make lint         # Run ruff linter
make typecheck    # Run mypy type checker
make test         # Run pytest with parallel execution
make check        # Run all checks (lint + typecheck + test)
```

The virtual environment is in `.venv/`. Use `.venv/bin/python` or `.venv/bin/pip` directly when needed.

## Testing Hardware

A GPS receiver is available for testing:
- Device: `/dev/ttyUSB0`
- Baud rate: 38400

## Documentation

- `spec/casic1.md` - NMEA text protocol (standard sentences + PCAS custom commands)
- `spec/casic2.md` - Binary CASIC protocol (CFG, NAV, TIM, ACK messages)
- `plan/casictool.md` - Implementation plan with command mappings and payload specifications

## Architecture

The tool uses binary CASIC messages (0xBA 0xCE header) for configuration. Key message classes:
- CFG (0x06): Configuration commands (PRT, MSG, RST, TP, RATE, CFG, TMODE, NAVX)
- ACK (0x05): Acknowledgment responses
- NAV (0x01): Navigation data
- TIM (0x02): Timing/PPS data

## Code Style

Error message style (applies to both log messages and exceptions):
- No sentence capitalization (acronyms like PPS, GNSS, CASIC are OK)
- No terminating periods
- Use semicolons to join related clauses
