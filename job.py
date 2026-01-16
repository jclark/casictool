"""CASIC receiver command implementations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

from casic import (
    BBR_ALL,
    BBR_NAV_DATA,
    CFG_CFG,
    CFG_MASK_ALL,
    CFG_MASK_MSG,
    CFG_MASK_NAV,
    CFG_MASK_TP,
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
    build_cfg_tp,
    parse_cfg_msg,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
    parse_mon_ver,
)

# ============================================================================
# Enums
# ============================================================================


class GNSS(Enum):
    """GNSS constellation identifiers."""

    GPS = "GPS"
    GAL = "GAL"
    BDS = "BDS"
    GLO = "GLO"


class NMEA(Enum):
    """NMEA sentence types. Values are indices into NMEARates list."""

    GGA = 0
    GLL = 1
    GSA = 2
    GSV = 3
    RMC = 4
    VTG = 5
    ZDA = 6


class SaveMode(Enum):
    """What to save to NVM."""

    NONE = "none"  # don't save
    CHANGES = "changes"  # save only what was changed by this job
    ALL = "all"  # save all current configuration


class ResetMode(Enum):
    """What kind of reset to perform."""

    NONE = "none"  # no reset
    RELOAD = "reload"  # reload config from NVM (discard unsaved changes)
    COLD = "cold"  # reload from NVM + cold start (clear nav data)
    FACTORY = "factory"  # restore NVM to factory defaults + cold start


# ============================================================================
# Property Value Dataclasses
# ============================================================================


@dataclass(frozen=True)
class TimePulse:
    """PPS/time pulse configuration."""

    period: float  # pulse period in seconds (1.0 = 1Hz PPS)
    width: float  # pulse width in seconds
    time_gnss: GNSS  # time source for PPS alignment


@dataclass(frozen=True)
class MobileMode:
    """Mobile/auto mode - antenna position may change."""

    pass


@dataclass(frozen=True)
class SurveyMode:
    """Survey-in mode - determine fixed position by surveying."""

    min_dur: int  # minimum duration in seconds
    acc: float  # target accuracy in meters


@dataclass(frozen=True)
class FixedMode:
    """Fixed position mode - use known antenna position."""

    ecef: tuple[float, float, float]  # ECEF coordinates in meters
    acc: float  # position accuracy in meters


# Union of time modes (use isinstance() or match/case to check which)
TimeMode = MobileMode | SurveyMode | FixedMode

# NMEA output rates: list indexed by NMEA.value (0 = disabled, 1 = every fix)
NMEARates = list[int]  # Always length len(NMEA)


def nmea_rates(**kwargs: int) -> NMEARates:
    """Create NMEARates list with specified messages enabled, rest disabled.

    Example: nmea_rates(GGA=1, RMC=1) -> [1, 0, 0, 0, 1, 0, 0]
    """
    rates = [0] * len(NMEA)
    for name, rate in kwargs.items():
        rates[NMEA[name].value] = rate
    return rates


# ============================================================================
# ConfigProps TypedDict
# ============================================================================


class ConfigProps(TypedDict, total=False):
    """Properties that can be set/queried on the receiver."""

    gnss: set[GNSS]  # enabled constellations
    time_mode: TimeMode  # mobile, survey, or fixed position mode
    time_pulse: TimePulse  # PPS configuration
    nmea_out: NMEARates  # NMEA message output rates


# ============================================================================
# Result Types
# ============================================================================


@dataclass
class CommandResult:
    """Result of command operations."""

    config_before: ReceiverConfig | None = None
    config_after: ReceiverConfig | None = None
    version: VersionInfo | None = None
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

    def mark_tp(self) -> None:
        """Mark time pulse configuration as changed (CFG-TP)."""
        self.mask |= CFG_MASK_TP


# ============================================================================
# Query Functions
# ============================================================================


def probe_receiver(
    conn: CasicConnection, timeout: float = 5.0
) -> tuple[bool, VersionInfo | None]:
    """Probe receiver with MON-VER to verify it's a CASIC device.

    Returns (is_casic, version_info). A NAK response proves it's CASIC
    even if MON-VER isn't supported.

    Args:
        conn: CasicConnection to the receiver
        timeout: How long to wait for response (default 5s for slow baud rates)
    """
    result = conn.poll(MON_VER.cls, MON_VER.id, timeout=timeout)
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


# ============================================================================
# PPS Command Functions
# ============================================================================


def set_pps(conn: CasicConnection, width_seconds: float) -> bool:
    """Configure PPS output using read-modify-write.

    Args:
        conn: Active CASIC connection
        width_seconds: Pulse width in seconds (0 to disable)

    Returns:
        True if ACK received, False on NAK or timeout
    """
    # Query current config to preserve other settings
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if not result.success:
        return False

    current = parse_cfg_tp(result.payload)  # type: ignore[arg-type]

    if width_seconds == 0:
        enable = 0
        width_us = current.width_us  # Preserve existing width
    else:
        enable = 1
        width_us = int(width_seconds * 1_000_000)

    payload = build_cfg_tp(
        interval_us=current.interval_us,
        width_us=width_us,
        enable=enable,
        polarity=current.polarity,
        time_ref=current.time_ref,
        time_source=current.time_source,
        user_delay=current.user_delay,
    )
    return conn.send_and_wait_ack(CFG_TP.cls, CFG_TP.id, payload)


def set_time_gnss(conn: CasicConnection, system: str) -> bool:
    """Set PPS time source constellation using read-modify-write.

    Args:
        conn: Active CASIC connection
        system: "GPS", "BDS", or "GLO"

    Returns:
        True if ACK received, False on NAK or timeout
    """
    time_source_map = {
        "GPS": 0,
        "BDS": 1,
        "GLO": 2,
    }

    time_source = time_source_map.get(system.upper())
    if time_source is None:
        return False

    # Query current config
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if not result.success:
        return False

    current = parse_cfg_tp(result.payload)  # type: ignore[arg-type]

    payload = build_cfg_tp(
        interval_us=current.interval_us,
        width_us=current.width_us,
        enable=current.enable,
        polarity=current.polarity,
        time_ref=current.time_ref,
        time_source=time_source,
        user_delay=current.user_delay,
    )
    return conn.send_and_wait_ack(CFG_TP.cls, CFG_TP.id, payload)


# ============================================================================
# ConfigJob and execute_job
# ============================================================================


@dataclass
class ConfigJob:
    """Complete specification of what casictool should do."""

    props: ConfigProps | None = None  # Properties to set
    save: SaveMode = SaveMode.NONE  # What to save to NVM
    reset: ResetMode = ResetMode.NONE  # What kind of reset to perform
    show_config: bool = False  # Query and return current config


def gnss_set_to_mask(gnss: set[GNSS]) -> int:
    """Convert set of GNSS enums to navSystem bitmask."""
    mask = 0
    if GNSS.GPS in gnss:
        mask |= 0x01
    if GNSS.BDS in gnss:
        mask |= 0x02
    if GNSS.GLO in gnss:
        mask |= 0x04
    return mask


def gnss_mask_to_set(mask: int) -> set[GNSS]:
    """Convert navSystem bitmask to set of GNSS enums."""
    result: set[GNSS] = set()
    if mask & 0x01:
        result.add(GNSS.GPS)
    if mask & 0x02:
        result.add(GNSS.BDS)
    if mask & 0x04:
        result.add(GNSS.GLO)
    return result


def gnss_to_time_source(gnss: GNSS) -> int:
    """Convert GNSS enum to time source code for CFG-TP."""
    return {"GPS": 0, "BDS": 1, "GLO": 2}.get(gnss.value, 0)


def time_source_to_gnss(time_source: int) -> GNSS:
    """Convert time source code from CFG-TP to GNSS enum."""
    return {0: GNSS.GPS, 1: GNSS.BDS, 2: GNSS.GLO}.get(time_source, GNSS.GPS)


def query_config_props(conn: CasicConnection) -> ConfigProps:
    """Query receiver and return ConfigProps representation."""
    props: ConfigProps = {}

    # Query GNSS constellations (CFG-NAVX)
    result = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if result.success:
        navx = parse_cfg_navx(result.payload)  # type: ignore[arg-type]
        props["gnss"] = gnss_mask_to_set(navx.nav_system)

    # Query timing mode (CFG-TMODE)
    result = conn.poll(CFG_TMODE.cls, CFG_TMODE.id)
    if result.success:
        tmode = parse_cfg_tmode(result.payload)  # type: ignore[arg-type]
        if tmode.mode == 0:
            props["time_mode"] = MobileMode()
        elif tmode.mode == 1:
            import math

            acc = math.sqrt(tmode.svin_var_limit) if tmode.svin_var_limit >= 0 else 0
            props["time_mode"] = SurveyMode(min_dur=tmode.svin_min_dur, acc=acc)
        elif tmode.mode == 2:
            import math

            acc = math.sqrt(tmode.fixed_pos_var) if tmode.fixed_pos_var >= 0 else 0
            props["time_mode"] = FixedMode(
                ecef=(tmode.fixed_pos_x, tmode.fixed_pos_y, tmode.fixed_pos_z),
                acc=acc,
            )

    # Query time pulse (CFG-TP)
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if result.success:
        tp = parse_cfg_tp(result.payload)  # type: ignore[arg-type]
        if tp.enabled:
            props["time_pulse"] = TimePulse(
                period=tp.interval_us / 1_000_000.0,
                width=tp.width_us / 1_000_000.0,
                time_gnss=time_source_to_gnss(tp.time_source),
            )

    # Query NMEA message rates
    rates = query_nmea_rates(conn)
    if rates.rates:
        nmea_out: NMEARates = [0] * len(NMEA)
        for name, rate in rates.rates.items():
            try:
                nmea_out[NMEA[name].value] = rate
            except KeyError:
                pass  # Skip unknown NMEA types
        props["nmea_out"] = nmea_out

    return props


def check_config(target: ConfigProps, actual: ConfigProps) -> dict[str, dict[str, object]]:
    """Return properties that don't match.

    Args:
        target: Expected properties
        actual: Actual properties from receiver

    Returns:
        Dict of {property_name: {'expected': value, 'actual': value}} for mismatches
    """
    mismatches: dict[str, dict[str, object]] = {}
    for key, expected in target.items():
        actual_val = actual.get(key)
        if actual_val != expected:
            mismatches[key] = {"expected": expected, "actual": actual_val}
    return mismatches


def execute_job(
    conn: CasicConnection,
    job: ConfigJob,
    log: logging.Logger,
) -> CommandResult:
    """Execute configuration job and return structured result.

    This is the main programmatic entry point for other tools.
    """
    result = CommandResult()
    changes = ConfigChanges()

    # Apply properties if specified
    if job.props is not None:
        # Apply GNSS constellation configuration
        if "gnss" in job.props:
            mask = gnss_set_to_mask(job.props["gnss"])
            if set_gnss(conn, mask):
                systems = sorted(g.value for g in job.props["gnss"])
                log.info(f"GNSS set: {', '.join(systems)}")
                changes.mark_nav()
            else:
                log.error("error: failed to set GNSS")
                result.success = False
                result.error = "Failed to set GNSS constellations"
                return result

        # Apply timing mode configuration
        if "time_mode" in job.props:
            time_mode = job.props["time_mode"]
            if isinstance(time_mode, MobileMode):
                if set_mobile_mode(conn):
                    log.info("mobile mode enabled")
                    changes.mark_nav()
                else:
                    log.error("error: failed to set mobile mode")
                    result.success = False
                    result.error = "Failed to set mobile mode"
                    return result
            elif isinstance(time_mode, SurveyMode):
                if set_survey_mode(conn, time_mode.min_dur, time_mode.acc):
                    log.info(f"survey-in mode: {time_mode.min_dur}s, {time_mode.acc}m")
                    changes.mark_nav()
                else:
                    log.error("error: failed to set survey-in mode")
                    result.success = False
                    result.error = "Failed to set survey-in mode"
                    return result
            elif isinstance(time_mode, FixedMode):
                if set_fixed_position(conn, time_mode.ecef, time_mode.acc):
                    ecef = time_mode.ecef
                    log.info(f"fixed position: ECEF ({ecef[0]:.3f}, {ecef[1]:.3f}, {ecef[2]:.3f})")
                    changes.mark_nav()
                else:
                    log.error("error: failed to set fixed position")
                    result.success = False
                    result.error = "Failed to set fixed position"
                    return result

        # Apply time pulse configuration
        if "time_pulse" in job.props:
            tp = job.props["time_pulse"]
            # Set pulse width
            if set_pps(conn, tp.width):
                if tp.width == 0:
                    log.info("PPS disabled")
                else:
                    log.info(f"PPS: {tp.width}s width")
                changes.mark_tp()
            else:
                log.error("error: failed to configure PPS")
                result.success = False
                result.error = "Failed to configure PPS"
                return result
            # Set time source
            if set_time_gnss(conn, tp.time_gnss.value):
                log.info(f"PPS time source: {tp.time_gnss.value}")
                changes.mark_tp()
            else:
                log.error("error: failed to set PPS time source")
                result.success = False
                result.error = "Failed to set PPS time source"
                return result

        # Apply NMEA output configuration
        if "nmea_out" in job.props:
            nmea_out = job.props["nmea_out"]
            # Set rate for each NMEA message type
            for nmea in NMEA:
                target_rate = nmea_out[nmea.value]
                if set_nmea_message_rate(conn, nmea.name, target_rate):
                    if target_rate > 0:
                        log.info(f"NMEA {nmea.name} enabled")
                    else:
                        log.info(f"NMEA {nmea.name} disabled")
                    changes.mark_msg()
                else:
                    log.error(f"error: failed to set NMEA {nmea.name}")
                    result.success = False
                    result.error = f"Failed to {'enable' if target_rate > 0 else 'disable'} {nmea.name}"
                    return result

    # Execute NVM save operations (after configuration changes)
    if job.save == SaveMode.ALL:
        if save_config(conn, CFG_MASK_ALL):
            log.info("config saved to NVM")
        else:
            log.error("error: failed to save config")
            result.success = False
            result.error = "Failed to save configuration"
            return result
    elif job.save == SaveMode.CHANGES:
        if changes.mask == 0:
            log.warning("warning: no config changes to save")
        else:
            if save_config(conn, changes.mask):
                log.info("config saved to NVM")
            else:
                log.error("error: failed to save config")
                result.success = False
                result.error = "Failed to save configuration"
                return result

    # Execute reset operations (after save)
    if job.reset == ResetMode.RELOAD:
        if load_config(conn, CFG_MASK_ALL):
            log.info("config reloaded from NVM")
        else:
            log.error("error: failed to reload config")
            result.success = False
            result.error = "Failed to reload configuration"
            return result
    elif job.reset == ResetMode.COLD:
        reset_receiver(conn, factory=False)
        log.info("cold start initiated")
    elif job.reset == ResetMode.FACTORY:
        reset_receiver(conn, factory=True)
        log.info("factory reset initiated")

    # Query config after operations (unless reset was performed)
    if job.reset not in (ResetMode.FACTORY, ResetMode.COLD):
        result.config_after = query_config(conn)

    return result
