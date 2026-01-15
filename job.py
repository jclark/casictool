"""CASIC receiver command implementations."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TextIO

from casic import (
    BBR_ALL,
    BBR_NAV_DATA,
    CFG_CFG,
    CFG_MASK_ALL,
    CFG_MASK_MSG,
    CFG_MASK_NAV,
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
    build_cfg_navx,
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

# ============================================================================
# Result Types
# ============================================================================


@dataclass
class CommandResult:
    """Result of command operations."""

    config_before: ReceiverConfig | None = None
    config_after: ReceiverConfig | None = None
    version: VersionInfo | None = None
    operations: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None


# ============================================================================
# Configuration Change Tracking
# ============================================================================


class ConfigChanges:
    """Track which configuration sections were modified."""

    def __init__(self) -> None:
        self.mask = 0

    def mark_nav(self) -> None:
        """Mark navigation configuration as changed (CFG-RATE, CFG-TMODE, CFG-NAVX)."""
        self.mask |= CFG_MASK_NAV

    def mark_msg(self) -> None:
        """Mark message output configuration as changed."""
        self.mask |= CFG_MASK_MSG


# ============================================================================
# Query Functions
# ============================================================================


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


def query_config(conn: CasicConnection) -> ReceiverConfig:
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


# ============================================================================
# Command Functions
# ============================================================================


def set_gnss(conn: CasicConnection, nav_system: int) -> bool:
    """Configure GNSS constellation selection using read-modify-write.

    Steps:
    1. Query current CFG-NAVX configuration
    2. Modify nav_system field only
    3. Send complete payload back to receiver
    4. Wait for ACK

    Args:
        conn: Active CASIC connection
        nav_system: Bitmask (B0=GPS, B1=BDS, B2=GLONASS)

    Returns:
        True if ACK received, False on NAK or timeout
    """
    # Query current config
    result = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if not result.success:
        return False

    # Parse and modify
    config = parse_cfg_navx(result.payload)  # type: ignore[arg-type]
    payload = build_cfg_navx(config, nav_system=nav_system)

    # Send and wait for ACK
    return conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload)


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


# ============================================================================
# Argument Parsing Helpers
# ============================================================================


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


# GNSS constellation names and aliases
VALID_GNSS = {"GPS", "BDS", "GLO", "GLN", "GLONASS"}
UNSUPPORTED_GNSS = {"GAL", "GALILEO", "QZSS", "NAVIC", "SBAS"}


def parse_gnss_arg(gnss_str: str) -> int:
    """Parse --gnss argument into navSystem bitmask.

    Args:
        gnss_str: Comma-separated list (e.g., "GPS,BDS,GLO")

    Returns:
        Bitmask: B0=GPS, B1=BDS, B2=GLONASS

    Raises:
        ValueError: If unknown or unsupported constellation specified
    """
    mask = 0

    for item in gnss_str.split(","):
        item = item.strip().upper()
        if not item:
            continue
        if item in UNSUPPORTED_GNSS:
            raise ValueError(
                f"Unsupported constellation: {item}. "
                "This receiver only supports GPS, BDS, and GLONASS."
            )
        if item not in VALID_GNSS:
            raise ValueError(f"Unknown constellation: {item}")

        if item == "GPS":
            mask |= 0x01
        elif item == "BDS":
            mask |= 0x02
        elif item in ("GLO", "GLN", "GLONASS"):
            mask |= 0x04

    return mask


# ============================================================================
# ConfigJob and execute_job
# ============================================================================


@dataclass
class ConfigJob:
    """Specification of configuration operations to perform."""

    # Timing mode (mutually exclusive)
    survey: tuple[int, float] | None = None  # (min_dur_secs, acc_meters)
    fixed_pos: tuple[tuple[float, float, float], float] | None = None  # (ecef, acc)
    mobile: bool = False

    # GNSS selection
    gnss: int | None = None  # Bitmask: B0=GPS, B1=BDS, B2=GLO

    # NMEA output
    nmea_enable: list[str] | None = None  # Messages to enable (others disabled)

    # NVM operations (mutually exclusive)
    save_mask: int | None = None  # Save these sections to NVM
    save_changes: bool = False  # Save only changed sections
    reload: bool = False  # Load from NVM
    reset: bool = False  # Cold start
    factory_reset: bool = False  # Factory reset

    # Query only
    show_config: bool = False  # Show current configuration


def execute_job(
    conn: CasicConnection,
    job: ConfigJob,
    log_file: TextIO = sys.stderr,
) -> CommandResult:
    """Execute configuration job and return structured result.

    This is the main programmatic entry point for other tools.
    Always queries config before and after operations.
    """
    result = CommandResult()
    changes = ConfigChanges()

    # Probe receiver first (except for reset operations which don't need it)
    if not (job.factory_reset or job.reset):
        is_casic, version = probe_receiver(conn)
        if not is_casic:
            result.success = False
            result.error = "No response from receiver. Not a CASIC device?"
            return result
        result.version = version

    # Execute timing mode configuration
    if job.survey is not None:
        min_dur, acc = job.survey
        if set_survey_mode(conn, min_dur, acc):
            result.operations.append(f"Survey-in mode enabled: {min_dur}s, {acc}m accuracy")
            changes.mark_nav()
        else:
            result.success = False
            result.error = "Failed to set survey-in mode"
            return result

    if job.fixed_pos is not None:
        ecef, acc = job.fixed_pos
        if set_fixed_position(conn, ecef, acc):
            result.operations.append(
                f"Fixed position set: ECEF ({ecef[0]:.3f}, {ecef[1]:.3f}, {ecef[2]:.3f})"
            )
            changes.mark_nav()
        else:
            result.success = False
            result.error = "Failed to set fixed position"
            return result

    if job.mobile:
        if set_mobile_mode(conn):
            result.operations.append("Mobile/auto mode enabled")
            changes.mark_nav()
        else:
            result.success = False
            result.error = "Failed to set mobile mode"
            return result

    # Execute NMEA message output configuration
    if job.nmea_enable is not None:
        enable_set = set(job.nmea_enable)
        # Enable specified messages, disable all others
        for msg_name in VALID_NMEA_MESSAGES:
            if msg_name in enable_set:
                if set_nmea_message_rate(conn, msg_name, 1):
                    result.operations.append(f"Enabled {msg_name}")
                    changes.mark_msg()
                else:
                    result.success = False
                    result.error = f"Failed to enable {msg_name}"
                    return result
            else:
                if set_nmea_message_rate(conn, msg_name, 0):
                    result.operations.append(f"Disabled {msg_name}")
                    changes.mark_msg()
                else:
                    result.success = False
                    result.error = f"Failed to disable {msg_name}"
                    return result

    # Execute GNSS constellation configuration
    if job.gnss is not None:
        if set_gnss(conn, job.gnss):
            systems = []
            if job.gnss & 0x01:
                systems.append("GPS")
            if job.gnss & 0x02:
                systems.append("BDS")
            if job.gnss & 0x04:
                systems.append("GLONASS")
            result.operations.append(f"GNSS constellations set: {', '.join(systems)}")
            changes.mark_nav()
        else:
            result.success = False
            result.error = "Failed to set GNSS constellations"
            return result

    # Execute NVM save operations (after configuration changes)
    if job.save_mask is not None:
        if save_config(conn, job.save_mask):
            result.operations.append("All configuration saved to NVM")
        else:
            result.success = False
            result.error = "Failed to save configuration"
            return result
    elif job.save_changes:
        if changes.mask == 0:
            result.operations.append("Warning: No configuration changes to save")
        else:
            if save_config(conn, changes.mask):
                result.operations.append("Configuration saved to NVM")
            else:
                result.success = False
                result.error = "Failed to save configuration"
                return result

    # Execute reload/reset operations (after save)
    if job.reload:
        if load_config(conn, CFG_MASK_ALL):
            result.operations.append("Configuration reloaded from NVM")
        else:
            result.success = False
            result.error = "Failed to reload configuration"
            return result

    if job.factory_reset:
        reset_receiver(conn, factory=True)
        result.operations.append("Factory reset initiated")

    if job.reset:
        reset_receiver(conn, factory=False)
        result.operations.append("Cold start reset initiated")

    # Query config after operations (unless reset was performed)
    if not (job.factory_reset or job.reset):
        result.config_after = query_config(conn)

    return result
