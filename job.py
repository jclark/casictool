"""CASIC receiver command implementations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

from casic import (
    ACK_ACK,
    ACK_NAK,
    BBR_RESET,
    CFG_CFG,
    CFG_MASK_ALL,
    CFG_MASK_MSG,
    CFG_MASK_NAV,
    CFG_MASK_PORT,
    CFG_MASK_TP,
    CFG_MSG,
    CFG_NAVX,
    CFG_PRT,
    CFG_RATE,
    CFG_RST,
    CFG_TMODE,
    CFG_TP,
    CLS_NMEA,
    DYN_MODEL_PORTABLE,
    DYN_MODEL_STATIONARY,
    MON_VER,
    MSG_IDS,
    MSG_NAMES,
    NMEA_MESSAGES,
    RESET_HW_IMMEDIATE,
    START_COLD,
    START_FACTORY,
    TIME_REF_SAT,
    TP_OFF,
    MessageRatesConfig,
    PortConfig,
    ReceiverConfig,
    VersionInfo,
    build_cfg_cfg,
    build_cfg_msg_set,
    build_cfg_navx,
    build_cfg_prt,
    build_cfg_rst,
    build_cfg_tmode,
    build_cfg_tp,
    msg_name,
    parse_cfg_msg,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
    parse_mon_ver,
)
from connection import INITIAL_TIMEOUT, SUBSEQUENT_TIMEOUT, CasicConnection

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
    """NMEA sentence types in alphabetical order."""

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
    """PPS/time pulse configuration. None fields mean 'preserve current'."""

    width: float | None = None  # pulse width in seconds (0 to disable)
    time_gnss: GNSS | None = None  # time source constellation
    time_ref: int | None = None  # TIME_REF_UTC or TIME_REF_SAT
    enable: int | None = None  # TP_OFF, TP_ON, TP_MAINTAIN, or TP_FIX_ONLY
    period: float = 1.0  # pulse period (always 1.0 for now)


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
    min_elev: int  # minimum satellite elevation angle in degrees (-90 to 90)
    dyn_model: int  # dynamic model (0=Portable, 1=Stationary, etc.) - internal use only
    time_mode: TimeMode  # mobile, survey, or fixed position mode
    time_pulse: TimePulse  # PPS configuration
    nmea_out: NMEARates  # NMEA message output rates
    casic_out: set[str]  # CASIC binary message names to enable


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

    def mark_prt(self) -> None:
        """Mark port configuration as changed (CFG-PRT)."""
        self.mask |= CFG_MASK_PORT


# ============================================================================
# Query Functions
# ============================================================================


def probe_receiver(
    conn: CasicConnection, log: logging.Logger
) -> tuple[bool, VersionInfo | None]:
    """Probe receiver with MON-VER to verify it's a CASIC device.

    Returns (is_casic, version_info). A NAK response proves it's CASIC
    even if MON-VER isn't supported.

    Waits for receiver to start sending data, then retries MON-VER up to 5 times.
    """
    # Wait for any packet before sending query (receiver may need time to start)
    log.debug("waiting for receiver data...")
    first_packet = conn.receive_packet(timeout=2.0)
    if first_packet is None:
        log.warning("no data being received (wrong device or speed?); querying anyway")
    else:
        log.info("receiving data from receiver")

    # Retry MON-VER query up to 5 times
    for attempt in range(5):
        log.debug(f"sending MON-VER query (attempt {attempt + 1}/5)")
        result = conn.poll(MON_VER.cls, MON_VER.id, timeout=2.0)
        if result.success:
            log.info("CASIC receiver detected")
            return True, parse_mon_ver(result.payload)  # type: ignore[arg-type]
        if result.nak:
            log.info("CASIC receiver detected (MON-VER not supported)")
            return True, None  # NAK proves it's CASIC
        # Timeout - retry
        log.debug(f"MON-VER timeout after attempt {attempt + 1}")

    log.debug("all MON-VER attempts failed")
    if conn.seen_casic_packet:
        log.warning("received CASIC packets but no response to probe; TX may not be working")
    return False, None


def query_port_config(conn: CasicConnection) -> PortConfig | None:
    """Query CFG-PRT for the current UART's port configuration.

    Returns the PortConfig for conn.uart, or None if query fails.
    """
    conn.send(CFG_PRT.cls, CFG_PRT.id, b"")
    got_response = False
    while True:
        timeout = SUBSEQUENT_TIMEOUT if got_response else INITIAL_TIMEOUT
        result = conn.receive(timeout=timeout)
        if result is None:
            break
        recv_id, recv_payload = result
        # Check for ACK/NAK
        if recv_id == ACK_ACK or recv_id == ACK_NAK:
            if len(recv_payload) >= 2 and recv_payload[0] == CFG_PRT.cls and recv_payload[1] == CFG_PRT.id:
                if recv_id == ACK_NAK:
                    break  # NAK means query not supported
                continue  # ACK means keep waiting for actual response
        # Check for actual CFG-PRT response
        if recv_id.cls == CFG_PRT.cls and recv_id.id == CFG_PRT.id and len(recv_payload) >= 8:
            port = parse_cfg_prt(recv_payload)
            got_response = True
            if port.port_id == conn.uart:
                return port
    return None


def query_nmea_rates(
    conn: CasicConnection, log: logging.Logger | None = None
) -> MessageRatesConfig | None:
    """Query NMEA message output rates via CFG-MSG.

    CFG-MSG query with empty payload returns all configured message rates.
    Each response is 4 bytes: cls, id, rate (U2).
    """
    # Build lookup from (cls, id) -> name for NMEA messages we care about
    nmea_lookup = {(msg.cls, msg.id): name for name, msg in NMEA_MESSAGES}

    rates: dict[str, int] = {}
    binary_rates: dict[str, int] = {}
    conn.send(CFG_MSG.cls, CFG_MSG.id, b"")

    # Collect all CFG-MSG responses (two-tier timeouts)
    # Wait for responses - use long timeout until we get a real CFG-MSG response
    got_response = False
    while True:
        timeout = SUBSEQUENT_TIMEOUT if got_response else INITIAL_TIMEOUT
        result = conn.receive(timeout=timeout)
        if result is None:
            break
        recv_id, recv_payload = result
        # Check for ACK/NAK - if it's for our query, keep waiting
        if recv_id == ACK_ACK or recv_id == ACK_NAK:
            if len(recv_payload) >= 2 and recv_payload[0] == CFG_MSG.cls and recv_payload[1] == CFG_MSG.id:
                if recv_id == ACK_NAK:
                    break  # NAK means query not supported
                continue  # ACK means keep waiting for actual response
        # Check for actual CFG-MSG response
        if recv_id.cls == CFG_MSG.cls and recv_id.id == CFG_MSG.id and len(recv_payload) >= 4:
            msg_cls, msg_id, rate = recv_payload[0], recv_payload[1], parse_cfg_msg(recv_payload)
            if msg_cls == CLS_NMEA:
                # NMEA message - track rate
                name = nmea_lookup.get((msg_cls, msg_id))
                if name:
                    rates[name] = rate
                    if log:
                        log.debug(f"CFG-MSG {name}: rate={rate}")
            else:
                # Binary CASIC message - track rate
                known_name = MSG_NAMES.get((msg_cls, msg_id))
                if known_name:
                    binary_rates[known_name] = rate
                if log:
                    log.debug(f"CFG-MSG {msg_name(msg_cls, msg_id)}: rate={rate}")
            got_response = True

    if not rates and not binary_rates:
        if log:
            log.warning("no response to NMEA message rate configuration (CFG-MSG) query")
        return None

    if log:
        log.info("got NMEA message rate configuration")
    return MessageRatesConfig(rates=rates, binary_rates=binary_rates or None)


def query_config(conn: CasicConnection, log: logging.Logger | None = None) -> ReceiverConfig:
    """Query all CFG messages and return receiver configuration."""
    config = ReceiverConfig()

    def _log_failure(feature: str, msg_name: str, nak: bool) -> None:
        if log:
            if nak:
                log.warning(f"{feature} ({msg_name}) not supported by receiver")
            else:
                log.warning(f"no response to {feature} ({msg_name}) query")

    # Single-response queries first (use INITIAL_TIMEOUT via poll default)

    # Query CFG-RATE
    result = conn.poll(CFG_RATE.cls, CFG_RATE.id)
    if result.success:
        config.rate = parse_cfg_rate(result.payload)  # type: ignore[arg-type]
        if log:
            log.info("got navigation solution rate configuration")
    else:
        _log_failure("navigation solution rate configuration", "CFG-RATE", result.nak)

    # Query CFG-TP
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if result.success:
        config.time_pulse = parse_cfg_tp(result.payload)  # type: ignore[arg-type]
        if log:
            log.info("got time pulse configuration")
    else:
        _log_failure("time pulse configuration", "CFG-TP", result.nak)

    # Query CFG-TMODE
    result = conn.poll(CFG_TMODE.cls, CFG_TMODE.id)
    if result.success:
        config.time_mode = parse_cfg_tmode(result.payload)  # type: ignore[arg-type]
        if log:
            log.info("got time mode configuration")
    else:
        _log_failure("time mode configuration", "CFG-TMODE", result.nak)

    # Query CFG-NAVX
    result = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if result.success:
        config.nav_engine = parse_cfg_navx(result.payload)  # type: ignore[arg-type]
        if log:
            log.info("got GNSS configuration")
    else:
        _log_failure("GNSS configuration", "CFG-NAVX", result.nak)

    # Multi-response queries last (two-tier timeouts)

    # Query CFG-PRT (may return multiple responses, one per port)
    # We only care about the UART specified in conn.uart
    target_port: PortConfig | None = None
    conn.send(CFG_PRT.cls, CFG_PRT.id, b"")
    # Wait for responses - use long timeout until we get a real CFG-PRT response
    got_response = False
    while True:
        timeout = SUBSEQUENT_TIMEOUT if got_response else INITIAL_TIMEOUT
        prt_result = conn.receive(timeout=timeout)
        if prt_result is None:
            break
        recv_id, recv_payload = prt_result
        # Check for ACK/NAK - if it's for our query, keep waiting
        if recv_id == ACK_ACK or recv_id == ACK_NAK:
            if len(recv_payload) >= 2 and recv_payload[0] == CFG_PRT.cls and recv_payload[1] == CFG_PRT.id:
                if recv_id == ACK_NAK:
                    break  # NAK means query not supported
                continue  # ACK means keep waiting for actual response
        # Check for actual CFG-PRT response
        if recv_id.cls == CFG_PRT.cls and recv_id.id == CFG_PRT.id and len(recv_payload) >= 8:
            port = parse_cfg_prt(recv_payload)
            got_response = True
            if port.port_id == conn.uart:
                target_port = port
                break  # Got the port we want, stop waiting
    if target_port:
        config.ports = [target_port]
        if log:
            log.info("got serial port configuration")
    elif log:
        log.warning("no response to serial port configuration (CFG-PRT) query")

    # Query NMEA message rates via CFG-MSG
    config.message_rates = query_nmea_rates(conn, log)

    return config


# ============================================================================
# Command Functions
# ============================================================================


def set_gnss(conn: CasicConnection, nav_system: int) -> bool:
    """Configure GNSS constellation selection.

    Args:
        conn: Active CASIC connection
        nav_system: Bitmask (B0=GPS, B1=BDS, B2=GLONASS)

    Returns:
        True if ACK received, False on NAK or timeout
    """
    payload = build_cfg_navx(nav_system=nav_system)
    return conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload)


def set_min_elev(conn: CasicConnection, min_elev: int) -> bool:
    """Configure minimum satellite elevation angle.

    Args:
        conn: Active CASIC connection
        min_elev: Minimum elevation angle in degrees (-90 to 90)

    Returns:
        True if ACK received, False on NAK or timeout
    """
    payload = build_cfg_navx(min_elev=min_elev)
    return conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload)


def set_survey_mode(conn: CasicConnection, min_dur: int, acc: float) -> bool:
    """Configure receiver for survey-in mode.

    Also sets dyn_model to Stationary for optimal time mode performance.
    """
    payload = build_cfg_tmode(
        mode=1,  # Survey-In
        survey_min_dur=min_dur,
        survey_acc=acc,
    )
    if not conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload):
        return False
    # Set dyn_model to Stationary
    payload = build_cfg_navx(dyn_model=DYN_MODEL_STATIONARY)
    return conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload)


def set_fixed_position(
    conn: CasicConnection,
    ecef: tuple[float, float, float],
    acc: float,
) -> bool:
    """Configure receiver with fixed ECEF position.

    Also sets dyn_model to Stationary for optimal time mode performance.
    """
    payload = build_cfg_tmode(
        mode=2,  # Fixed
        fixed_pos=ecef,
        fixed_pos_acc=acc,
    )
    if not conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload):
        return False
    # Set dyn_model to Stationary
    payload = build_cfg_navx(dyn_model=DYN_MODEL_STATIONARY)
    return conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload)


def set_mobile_mode(conn: CasicConnection) -> bool:
    """Configure receiver for mobile/auto mode.

    Also sets dyn_model to Portable for mobile operation.
    """
    payload = build_cfg_tmode(mode=0)  # Auto
    if not conn.send_and_wait_ack(CFG_TMODE.cls, CFG_TMODE.id, payload):
        return False
    # Set dyn_model to Portable
    payload = build_cfg_navx(dyn_model=DYN_MODEL_PORTABLE)
    return conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload)


def set_port_text_output(conn: CasicConnection, port: PortConfig, enable: bool) -> bool:
    """Enable or disable text (NMEA) output on a port.

    Uses read-modify-write: preserves existing mode and baud_rate,
    only changes the text output bit (B5) in protoMask.

    Args:
        conn: Active CASIC connection
        port: Current port configuration from CFG-PRT query
        enable: True to enable text output, False to disable

    Returns:
        True if acknowledged, False on failure
    """
    if enable:
        new_proto_mask = port.proto_mask | 0x20  # Set B5
    else:
        new_proto_mask = port.proto_mask & ~0x20  # Clear B5

    payload = build_cfg_prt(port.port_id, new_proto_mask, port.mode, port.baud_rate)
    return conn.send_and_wait_ack(CFG_PRT.cls, CFG_PRT.id, payload)


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


def set_casic_message_rate(conn: CasicConnection, msg_cls: int, msg_id: int, rate: int) -> bool:
    """Set output rate for a specific CASIC binary message.

    Args:
        conn: Active CASIC connection
        msg_cls: Message class
        msg_id: Message ID
        rate: Output rate (0=disable, 1=enable)

    Returns:
        True if acknowledged, False on failure
    """
    payload = build_cfg_msg_set(msg_cls, msg_id, rate)
    return conn.send_and_wait_ack(CFG_MSG.cls, CFG_MSG.id, payload)


def set_nmea_output(
    conn: CasicConnection,
    nmea_out: NMEARates,
    port_config: PortConfig,
    changes: ConfigChanges,
    log: logging.Logger,
) -> tuple[bool, str | None]:
    """Configure NMEA output using protoMask optimization.

    For --nmea-out none: disables text output at port level (single CFG-PRT).
    For --nmea-out <msgs>: ensures text output enabled, then configures
    individual messages, skipping any already at the correct rate.

    Args:
        conn: Active CASIC connection
        nmea_out: Desired NMEA rates (all zeros = disable all)
        port_config: Current port configuration from CFG-PRT query
        changes: Tracks which config sections changed
        log: Logger for status messages

    Returns:
        (True, None) on success, (False, error_message) on failure
    """
    all_disabled = all(r == 0 for r in nmea_out)

    if all_disabled:
        # Disable text output at port level (skip individual CFG-MSG)
        if port_config.text_output:
            if not set_port_text_output(conn, port_config, False):
                return False, "failed to disable text output on port"
            log.info("NMEA output disabled")
            changes.mark_prt()
        return True, None

    # Ensure text output is enabled
    if not port_config.text_output:
        if not set_port_text_output(conn, port_config, True):
            return False, "failed to enable text output on port"
        log.info("NMEA output enabled")
        changes.mark_prt()

    # Query current rates and only change what's needed
    current_rates = query_nmea_rates(conn, log)

    # Configure individual messages (GSV first - most traffic)
    for nmea in [NMEA.GSV] + [n for n in NMEA if n != NMEA.GSV]:
        target = nmea_out[nmea.value]
        current = current_rates.rates.get(nmea.name, -1) if current_rates else -1

        if target == current:
            # "already enabled" at info: user explicitly requested this message
            # "already disabled" at debug: avoid spam when using --nmea-out=none
            if target:
                log.info(f"NMEA {nmea.name} already enabled")
            else:
                log.debug(f"NMEA {nmea.name} already disabled")
            continue

        if not set_nmea_message_rate(conn, nmea.name, target):
            return False, f"failed to {'enable' if target else 'disable'} NMEA {nmea.name}"
        log.info(f"NMEA {nmea.name} {'enabled' if target else 'disabled'}")
        changes.mark_msg()

    return True, None


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
    nav_bbr_mask = BBR_RESET
    if factory:
        start_mode = START_FACTORY
    else:
        start_mode = START_COLD
    payload = build_cfg_rst(nav_bbr_mask, RESET_HW_IMMEDIATE, start_mode)

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


def set_time_pulse(
    conn: CasicConnection,
    *,
    width_seconds: float | None = None,
    enable: int | None = None,
    time_source: int | None = None,
    time_ref: int | None = None,
) -> bool:
    """Configure time pulse using read-modify-write.

    All parameters are optional - only provided values are modified,
    others are preserved from current config.

    Args:
        conn: Active CASIC connection
        width_seconds: Pulse width in seconds (0 to disable)
        enable: Enable mode (TP_OFF, TP_ON, TP_MAINTAIN, TP_FIX_ONLY)
        time_source: 0=GPS, 1=BDS, 2=GLO
        time_ref: TIME_REF_UTC or TIME_REF_SAT

    Returns:
        True if ACK received, False on NAK or timeout
    """
    # Query current config
    result = conn.poll(CFG_TP.cls, CFG_TP.id)
    if not result.success:
        return False

    current = parse_cfg_tp(result.payload)  # type: ignore[arg-type]

    # Compute new values, preserving current where not specified
    new_enable = enable if enable is not None else current.enable
    if width_seconds is not None:
        if width_seconds == 0:
            new_enable = TP_OFF
            new_width_us = current.width_us  # preserve
        else:
            new_width_us = int(width_seconds * 1_000_000)
    else:
        new_width_us = current.width_us

    payload = build_cfg_tp(
        interval_us=current.interval_us,
        width_us=new_width_us,
        enable=new_enable,
        polarity=current.polarity,
        time_ref=time_ref if time_ref is not None else current.time_ref,
        time_source=time_source if time_source is not None else current.time_source,
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

    # Query GNSS constellations, min elevation, and dyn_model (CFG-NAVX)
    result = conn.poll(CFG_NAVX.cls, CFG_NAVX.id)
    if result.success:
        navx = parse_cfg_navx(result.payload)  # type: ignore[arg-type]
        props["gnss"] = gnss_mask_to_set(navx.nav_system)
        props["min_elev"] = navx.min_elev
        props["dyn_model"] = navx.dyn_model

    # Query time mode (CFG-TMODE)
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
        props["time_pulse"] = TimePulse(
            width=0.0 if not tp.enabled else tp.width_us / 1_000_000.0,
            time_gnss=time_source_to_gnss(tp.time_source),
            time_ref=tp.time_ref,
            enable=tp.enable,
            period=tp.interval_us / 1_000_000.0,
        )

    # Query port config to check if text output is enabled
    port_config = query_port_config(conn)

    # Query NMEA message rates - but if text output is disabled at port level,
    # effective NMEA output is all zeros regardless of individual message rates
    if port_config is not None and not port_config.text_output:
        # Text output disabled at port level - all NMEA effectively off
        props["nmea_out"] = [0] * len(NMEA)
        # Still need to query for CASIC binary rates
        rates = query_nmea_rates(conn)
    else:
        # Text output enabled (or port query failed) - check individual rates
        rates = query_nmea_rates(conn)
        if rates is not None and rates.rates:
            nmea_out: NMEARates = [0] * len(NMEA)
            for name, rate in rates.rates.items():
                try:
                    nmea_out[NMEA[name].value] = rate
                except KeyError:
                    pass  # Skip unknown NMEA types
            props["nmea_out"] = nmea_out

    # Query CASIC binary message rates (always, independent of text output)
    if rates is not None and rates.binary_rates is not None:
        casic_out: set[str] = set()
        for name, rate in rates.binary_rates.items():
            if rate > 0:
                casic_out.add(name)
        props["casic_out"] = casic_out

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
                result.success = False
                result.error = "failed to set GNSS constellations"
                return result

        # Apply minimum elevation configuration
        if "min_elev" in job.props:
            elev = job.props["min_elev"]
            if set_min_elev(conn, elev):
                log.info(f"minimum elevation: {elev}°")
                changes.mark_nav()
            else:
                result.success = False
                result.error = "failed to set minimum elevation"
                return result

        # Apply time mode configuration
        if "time_mode" in job.props:
            time_mode = job.props["time_mode"]
            if isinstance(time_mode, MobileMode):
                if set_mobile_mode(conn):
                    log.info("mobile mode enabled")
                    changes.mark_nav()
                else:
                    result.success = False
                    result.error = "failed to set mobile mode"
                    return result
            elif isinstance(time_mode, SurveyMode):
                if set_survey_mode(conn, time_mode.min_dur, time_mode.acc):
                    log.info(f"survey-in mode: {time_mode.min_dur}s, {time_mode.acc}m")
                    changes.mark_nav()
                else:
                    result.success = False
                    result.error = "failed to set survey-in mode"
                    return result
            elif isinstance(time_mode, FixedMode):
                if set_fixed_position(conn, time_mode.ecef, time_mode.acc):
                    ecef = time_mode.ecef
                    log.info(f"fixed position: ECEF ({ecef[0]:.3f}, {ecef[1]:.3f}, {ecef[2]:.3f})")
                    changes.mark_nav()
                else:
                    result.success = False
                    result.error = "failed to set fixed position"
                    return result

        # Apply time pulse configuration
        if "time_pulse" in job.props:
            tp = job.props["time_pulse"]
            time_source_map = {"GPS": 0, "BDS": 1, "GLO": 2}
            time_source = time_source_map[tp.time_gnss.value] if tp.time_gnss else None

            if set_time_pulse(
                conn,
                width_seconds=tp.width,
                enable=tp.enable,
                time_source=time_source,
                time_ref=tp.time_ref,
            ):
                if tp.width is not None:
                    if tp.width == 0:
                        log.info("PPS disabled")
                    else:
                        log.info(f"PPS: {tp.width}s width")
                if tp.time_gnss is not None:
                    time_gnss_str = tp.time_gnss.value if tp.time_ref == TIME_REF_SAT else f"{tp.time_gnss.value}/UTC"
                    log.info(f"PPS time GNSS: {time_gnss_str}")
                changes.mark_tp()
            else:
                result.success = False
                result.error = "failed to configure time pulse"
                return result

        # Apply NMEA output configuration
        if "nmea_out" in job.props:
            # Query port config to manage protoMask
            port_config = query_port_config(conn)
            if port_config is None:
                result.success = False
                result.error = "failed to query port configuration"
                return result

            success, error = set_nmea_output(
                conn, job.props["nmea_out"], port_config, changes, log
            )
            if not success:
                result.success = False
                result.error = error
                return result

        # Apply CASIC binary output configuration
        if "casic_out" in job.props:
            casic_out = job.props["casic_out"]
            # Query current rates to get list of known CASIC messages
            current_rates = query_nmea_rates(conn, log)
            if current_rates is None or current_rates.binary_rates is None:
                result.success = False
                result.error = "failed to query current CASIC message configuration"
                return result

            # For each known binary message, enable or disable as needed
            for msg_name_str, current_rate in current_rates.binary_rates.items():
                msg_key = MSG_IDS.get(msg_name_str)
                if msg_key is None:
                    continue  # Skip unknown messages
                msg_cls, msg_id = msg_key
                target_rate = 1 if msg_name_str in casic_out else 0

                # Skip if already at the desired rate
                # "already enabled" at info: user explicitly requested this message
                # "already disabled" at debug: avoid spam when using --casic-out=none
                if current_rate == target_rate:
                    if target_rate:
                        log.info(f"CASIC {msg_name_str} already enabled")
                    else:
                        log.debug(f"CASIC {msg_name_str} already disabled")
                    continue

                if set_casic_message_rate(conn, msg_cls, msg_id, target_rate):
                    if target_rate > 0:
                        log.info(f"CASIC {msg_name_str} enabled")
                    else:
                        log.info(f"CASIC {msg_name_str} disabled")
                    changes.mark_msg()
                else:
                    result.success = False
                    result.error = f"failed to {'enable' if target_rate > 0 else 'disable'} CASIC {msg_name_str}"
                    return result

    # Execute NVM save operations (after configuration changes)
    if job.save == SaveMode.ALL:
        if save_config(conn, CFG_MASK_ALL):
            log.info("config saved to NVM")
        else:
            result.success = False
            result.error = "failed to save configuration"
            return result
    elif job.save == SaveMode.CHANGES:
        if changes.mask == 0:
            result.success = False
            result.error = "no config changes to save (did you mean --save-all?)"
            return result
        else:
            if save_config(conn, changes.mask):
                log.info("config saved to NVM")
            else:
                result.success = False
                result.error = "failed to save configuration"
                return result

    # Execute reset operations (after save)
    if job.reset == ResetMode.RELOAD:
        if load_config(conn, CFG_MASK_ALL):
            log.info("config reloaded from NVM")
        else:
            result.success = False
            result.error = "failed to reload configuration"
            return result
    elif job.reset == ResetMode.COLD:
        reset_receiver(conn, factory=False)
        log.info("cold start initiated")
    elif job.reset == ResetMode.FACTORY:
        reset_receiver(conn, factory=True)
        log.info("factory reset initiated")

    # Query config if requested (and no reset was performed)
    if job.show_config and job.reset not in (ResetMode.FACTORY, ResetMode.COLD):
        result.config_after = query_config(conn, log)

    return result
