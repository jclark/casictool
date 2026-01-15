"""CASIC protocol implementation: framing, checksum, messages, and serial communication."""

from __future__ import annotations

import math
import struct
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import serial

if TYPE_CHECKING:
    from serial import Serial

# Sync bytes
SYNC1 = 0xBA
SYNC2 = 0xCE

# Message classes
CLS_NAV = 0x01
CLS_TIM = 0x02
CLS_RXM = 0x03
CLS_ACK = 0x05
CLS_CFG = 0x06
CLS_MSG = 0x08
CLS_MON = 0x0A
CLS_AID = 0x0B
CLS_NMEA = 0x4E


class MsgID:
    """Combined class/id identifier for CASIC messages."""

    def __init__(self, cls: int, id: int) -> None:
        self.cls = cls
        self.id = id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MsgID):
            return NotImplemented
        return self.cls == other.cls and self.id == other.id

    def __hash__(self) -> int:
        return hash((self.cls, self.id))

    def __repr__(self) -> str:
        return f"MsgID(0x{self.cls:02X}, 0x{self.id:02X})"


# ACK messages
ACK_NAK = MsgID(CLS_ACK, 0x00)
ACK_ACK = MsgID(CLS_ACK, 0x01)

# MON messages
MON_VER = MsgID(CLS_MON, 0x04)

# CFG messages
CFG_PRT = MsgID(CLS_CFG, 0x00)
CFG_MSG = MsgID(CLS_CFG, 0x01)
CFG_RST = MsgID(CLS_CFG, 0x02)
CFG_TP = MsgID(CLS_CFG, 0x03)
CFG_RATE = MsgID(CLS_CFG, 0x04)
CFG_CFG = MsgID(CLS_CFG, 0x05)
CFG_TMODE = MsgID(CLS_CFG, 0x06)
CFG_NAVX = MsgID(CLS_CFG, 0x07)

# Mask bits for CFG-CFG (configuration sections)
CFG_MASK_PORT = 0x0001  # B0: CFG-PRT
CFG_MASK_MSG = 0x0002  # B1: CFG-MSG
CFG_MASK_INF = 0x0004  # B2: CFG-INF
CFG_MASK_RATE = 0x0008  # B3: CFG-RATE, CFG-TMODE
CFG_MASK_TP = 0x0010  # B4: CFG-TP
CFG_MASK_GROUP = 0x0020  # B5: CFG-GROUP
CFG_MASK_ALL = 0xFFFF  # All sections

# BBR mask bits for CFG-RST (battery-backed RAM sections)
BBR_EPHEMERIS = 0x0001  # B0
BBR_ALMANAC = 0x0002  # B1
BBR_HEALTH = 0x0004  # B2
BBR_IONOSPHERE = 0x0008  # B3
BBR_POSITION = 0x0010  # B4
BBR_CLOCK_DRIFT = 0x0020  # B5
BBR_OSC_PARAMS = 0x0040  # B6
BBR_UTC_PARAMS = 0x0080  # B7
BBR_RTC = 0x0100  # B8
BBR_CONFIG = 0x0200  # B9

# Composite BBR masks
BBR_NAV_DATA = 0x01FF  # All nav data (for cold start)
BBR_ALL = 0x03FF  # Everything (for factory reset)


def calc_checksum(cls: int, id: int, payload: bytes) -> int:
    """Calculate CASIC checksum (cumulative 32-bit word sum)."""
    length = len(payload)
    ck_sum = (id << 24) + (cls << 16) + length

    # Pad payload to multiple of 4 bytes
    pad_len = (4 - len(payload) % 4) % 4
    padded = payload + b"\x00" * pad_len

    # Sum 32-bit little-endian words
    for i in range(0, len(padded), 4):
        word = int.from_bytes(padded[i : i + 4], "little")
        ck_sum = (ck_sum + word) & 0xFFFFFFFF

    return ck_sum


def pack_msg(cls: int, id: int, payload: bytes) -> bytes:
    """Pack a complete CASIC message with header and checksum."""
    length = len(payload)
    checksum = calc_checksum(cls, id, payload)

    msg = bytearray()
    msg.append(SYNC1)
    msg.append(SYNC2)
    msg.extend(length.to_bytes(2, "little"))
    msg.append(cls)
    msg.append(id)
    msg.extend(payload)
    msg.extend(checksum.to_bytes(4, "little"))

    return bytes(msg)


def parse_msg(data: bytes) -> tuple[MsgID, bytes] | None:
    """Parse a CASIC message, returning (MsgID, payload) or None on error."""
    if len(data) < 10:
        return None

    if data[0] != SYNC1 or data[1] != SYNC2:
        return None

    length = int.from_bytes(data[2:4], "little")
    expected_size = 6 + length + 4
    if len(data) < expected_size:
        return None

    cls = data[4]
    id = data[5]
    payload = data[6 : 6 + length]

    received_checksum = int.from_bytes(data[6 + length : 6 + length + 4], "little")
    calculated_checksum = calc_checksum(cls, id, payload)

    if received_checksum != calculated_checksum:
        return None

    return MsgID(cls, id), payload


@dataclass
class PollResult:
    """Result of a poll operation."""

    payload: bytes | None
    nak: bool = False

    @property
    def success(self) -> bool:
        return self.payload is not None

    @property
    def timeout(self) -> bool:
        return self.payload is None and not self.nak


class CasicConnection:
    """Serial connection with CASIC protocol handling."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        self._serial.reset_input_buffer()

    def close(self) -> None:
        self._serial.close()

    def __enter__(self) -> CasicConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.close()

    def send(self, cls: int, id: int, payload: bytes = b"") -> None:
        """Send a CASIC message."""
        msg = pack_msg(cls, id, payload)
        self._serial.write(msg)
        self._serial.flush()

    def receive(self, timeout: float | None = None) -> tuple[MsgID, bytes] | None:
        """Receive and parse a CASIC message."""
        if timeout is None:
            timeout = self.timeout

        start_time = time.monotonic()
        old_timeout = self._serial.timeout
        self._serial.timeout = min(0.1, timeout)

        try:
            while time.monotonic() - start_time < timeout:
                byte1 = self._serial.read(1)
                if not byte1 or byte1[0] != SYNC1:
                    continue

                byte2 = self._serial.read(1)
                if not byte2 or byte2[0] != SYNC2:
                    continue

                length_bytes = self._serial.read(2)
                if len(length_bytes) < 2:
                    continue

                length = int.from_bytes(length_bytes, "little")
                remaining = 2 + length + 4
                rest = self._serial.read(remaining)
                if len(rest) < remaining:
                    continue

                full_msg = bytes([SYNC1, SYNC2]) + length_bytes + rest
                result = parse_msg(full_msg)
                if result is not None:
                    return result

            return None
        finally:
            self._serial.timeout = old_timeout

    def send_and_wait_ack(
        self, cls: int, id: int, payload: bytes, timeout: float = 2.0
    ) -> bool:
        """Send CFG message and wait for ACK/NAK response."""
        self.send(cls, id, payload)

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            result = self.receive(timeout=timeout - (time.monotonic() - start_time))
            if result is None:
                continue

            msg_id, ack_payload = result

            if msg_id == ACK_ACK and len(ack_payload) >= 2:
                if ack_payload[0] == cls and ack_payload[1] == id:
                    return True

            if msg_id == ACK_NAK and len(ack_payload) >= 2:
                if ack_payload[0] == cls and ack_payload[1] == id:
                    return False

        return False

    def poll(self, cls: int, id: int, timeout: float = 2.0) -> PollResult:
        """Send query (empty payload) and wait for response.

        Returns PollResult with:
        - payload set on success
        - nak=True if receiver rejected the query
        - both None/False on timeout
        """
        self.send(cls, id, b"")

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            result = self.receive(timeout=timeout - (time.monotonic() - start_time))
            if result is None:
                continue

            msg_id, payload = result

            # Check for NAK response to our query
            if msg_id == ACK_NAK and len(payload) >= 2:
                if payload[0] == cls and payload[1] == id:
                    return PollResult(None, nak=True)

            # Check for the actual response
            if msg_id.cls == cls and msg_id.id == id:
                return PollResult(payload)

        return PollResult(None)


# ============================================================================
# Monitor Dataclasses
# ============================================================================


@dataclass
class VersionInfo:
    """MON-VER response: software and hardware version."""

    sw_version: str
    hw_version: str


def parse_mon_ver(payload: bytes) -> VersionInfo:
    """Parse MON-VER response payload (64 bytes)."""
    if len(payload) < 64:
        raise ValueError(f"MON-VER payload too short: {len(payload)} bytes, expected 64")
    sw_version = payload[0:32].rstrip(b"\x00").decode("ascii", errors="replace")
    hw_version = payload[32:64].rstrip(b"\x00").decode("ascii", errors="replace")
    return VersionInfo(sw_version=sw_version, hw_version=hw_version)


# ============================================================================
# Configuration Dataclasses
# ============================================================================


@dataclass
class PortConfig:
    """CFG-PRT response: serial port configuration."""

    port_id: int
    proto_mask: int
    mode: int
    baud_rate: int

    @property
    def binary_input(self) -> bool:
        return bool(self.proto_mask & 0x01)

    @property
    def text_input(self) -> bool:
        return bool(self.proto_mask & 0x02)

    @property
    def binary_output(self) -> bool:
        return bool(self.proto_mask & 0x10)

    @property
    def text_output(self) -> bool:
        return bool(self.proto_mask & 0x20)

    @property
    def data_bits(self) -> int:
        bits_code = (self.mode >> 6) & 0x03
        return 5 + bits_code

    @property
    def parity(self) -> str:
        parity_code = (self.mode >> 9) & 0x07
        if parity_code & 0x04:  # Bit 2 set = no parity
            return "N"
        elif parity_code & 0x01:  # Bit 0 set = odd
            return "O"
        else:
            return "E"

    @property
    def stop_bits(self) -> str:
        stop_code = (self.mode >> 12) & 0x03
        if stop_code == 0:
            return "1"
        elif stop_code == 1:
            return "1.5"
        else:
            return "2"

    @property
    def data_format(self) -> str:
        return f"{self.data_bits}{self.parity}{self.stop_bits}"

    def format(self) -> str:
        return f"Baud rate: {self.baud_rate}\nData format: {self.data_format}"


@dataclass
class RateConfig:
    """CFG-RATE response: navigation update rate."""

    interval_ms: int

    @property
    def update_rate_hz(self) -> float:
        if self.interval_ms == 0:
            return 0.0
        return 1000.0 / self.interval_ms

    def format(self) -> str:
        return f"Navigation rate: {self.update_rate_hz:.1f} Hz"


@dataclass
class TimePulseConfig:
    """CFG-TP response: PPS/time pulse configuration."""

    interval_us: int
    width_us: int
    enable: int
    polarity: int
    time_ref: int
    time_source: int
    user_delay: float

    @property
    def enabled(self) -> bool:
        return self.enable != 0

    @property
    def enable_mode(self) -> str:
        modes = {0: "Off", 1: "On", 2: "Auto Maintain", 3: "Fix Only"}
        return modes.get(self.enable, f"Unknown ({self.enable})")

    @property
    def polarity_str(self) -> str:
        return "Falling edge" if self.polarity else "Rising edge"

    @property
    def time_ref_str(self) -> str:
        return "Satellite Time" if self.time_ref else "UTC"

    @property
    def time_source_str(self) -> str:
        sources = {
            0: "GPS",
            1: "BDS",
            2: "GLONASS",
            4: "BDS (Main)",
            5: "GPS (Main)",
            6: "GLONASS (Main)",
        }
        return sources.get(self.time_source, f"Unknown ({self.time_source})")

    @property
    def interval_s(self) -> float:
        return self.interval_us / 1_000_000.0

    @property
    def width_ms(self) -> float:
        return self.width_us / 1000.0

    def format(self) -> str:
        if not self.enabled:
            return "Time pulse: disabled"
        polarity = "falling" if self.polarity else "rising"
        return (
            f"Time pulse: enabled; width {self.width_ms / 1000:.3g} s; "
            f"period {self.interval_s:.3g} s; polarity {polarity}"
        )


@dataclass
class TimingModeConfig:
    """CFG-TMODE response: timing mode configuration."""

    mode: int
    fixed_pos_x: float
    fixed_pos_y: float
    fixed_pos_z: float
    fixed_pos_var: float
    svin_min_dur: int
    svin_var_limit: float

    @property
    def mode_str(self) -> str:
        modes = {0: "Auto", 1: "Survey-In", 2: "Fixed"}
        return modes.get(self.mode, f"Unknown ({self.mode})")

    def format(self) -> str:
        lines = [f"Mode: {self.mode_str.lower()}"]
        if self.mode == 2:  # Fixed position
            lines.append(
                f"Fixed position ECEF: {self.fixed_pos_x:.3f}, "
                f"{self.fixed_pos_y:.3f}, {self.fixed_pos_z:.3f}"
            )
            acc = math.sqrt(self.fixed_pos_var) if self.fixed_pos_var >= 0 else 0
            lines.append(f"Fixed position accuracy: {acc:.3g} m")
        return "\n".join(lines)


@dataclass
class NavEngineConfig:
    """CFG-NAVX response: navigation engine configuration."""

    mask: int
    dyn_model: int
    fix_mode: int
    min_svs: int
    max_svs: int
    min_cno: int
    ini_fix_3d: int
    min_elev: int
    dr_limit: int
    nav_system: int
    wn_rollover: int
    fixed_alt: float
    fixed_alt_var: float
    p_dop: float
    t_dop: float
    p_acc: float
    t_acc: float
    static_hold_th: float

    @property
    def dyn_model_str(self) -> str:
        models = {
            0: "Portable",
            1: "Stationary",
            2: "Pedestrian",
            3: "Automotive",
            4: "Sea",
            5: "Air 1g",
            6: "Air 2g",
            7: "Air 4g",
        }
        return models.get(self.dyn_model, f"Unknown ({self.dyn_model})")

    @property
    def fix_mode_str(self) -> str:
        modes = {1: "2D", 2: "3D", 3: "Auto"}
        return modes.get(self.fix_mode, f"Unknown ({self.fix_mode})")

    @property
    def gnss_list(self) -> list[str]:
        systems = []
        if self.nav_system & 0x01:
            systems.append("GPS")
        if self.nav_system & 0x02:
            systems.append("BDS")
        if self.nav_system & 0x04:
            systems.append("GLONASS")
        return systems

    def format(self) -> str:
        gnss_str = ", ".join(self.gnss_list) if self.gnss_list else "None"
        return f"Constellations enabled: {gnss_str}"


@dataclass
class ReceiverConfig:
    """Container for all receiver configuration sections."""

    port: PortConfig | None = None
    rate: RateConfig | None = None
    time_pulse: TimePulseConfig | None = None
    timing_mode: TimingModeConfig | None = None
    nav_engine: NavEngineConfig | None = None

    def format(self) -> str:
        sections = []
        if self.nav_engine is not None:
            sections.append(self.nav_engine.format())
        if self.time_pulse is not None:
            sections.append(self.time_pulse.format())
        if self.timing_mode is not None:
            sections.append(self.timing_mode.format())
        if self.rate is not None:
            sections.append(self.rate.format())
        if self.port is not None:
            sections.append(self.port.format())
        return "\n".join(sections)


# ============================================================================
# Payload Parsers
# ============================================================================


def parse_cfg_prt(payload: bytes) -> PortConfig:
    """Parse CFG-PRT response payload (8 bytes)."""
    if len(payload) < 8:
        raise ValueError(f"CFG-PRT payload too short: {len(payload)} bytes, expected 8")
    port_id, proto_mask, mode, baud_rate = struct.unpack("<BBHI", payload[:8])
    return PortConfig(port_id=port_id, proto_mask=proto_mask, mode=mode, baud_rate=baud_rate)


def parse_cfg_rate(payload: bytes) -> RateConfig:
    """Parse CFG-RATE response payload (4 bytes)."""
    if len(payload) < 4:
        raise ValueError(f"CFG-RATE payload too short: {len(payload)} bytes, expected 4")
    interval_ms, _reserved = struct.unpack("<HH", payload[:4])
    return RateConfig(interval_ms=interval_ms)


def parse_cfg_tp(payload: bytes) -> TimePulseConfig:
    """Parse CFG-TP response payload (16 bytes)."""
    if len(payload) < 16:
        raise ValueError(f"CFG-TP payload too short: {len(payload)} bytes, expected 16")
    interval, width, enable, polar, time_ref, time_source, user_delay = struct.unpack(
        "<IIbbbBf", payload[:16]
    )
    return TimePulseConfig(
        interval_us=interval,
        width_us=width,
        enable=enable,
        polarity=polar,
        time_ref=time_ref,
        time_source=time_source,
        user_delay=user_delay,
    )


def parse_cfg_tmode(payload: bytes) -> TimingModeConfig:
    """Parse CFG-TMODE response payload (40 bytes)."""
    if len(payload) < 40:
        raise ValueError(f"CFG-TMODE payload too short: {len(payload)} bytes, expected 40")
    mode, pos_x, pos_y, pos_z, pos_var, svin_dur, svin_var = struct.unpack(
        "<IdddIfI", payload[:40]
    )
    # svin_var is actually R4 (float), but packed after U4
    # Re-parse with correct format
    mode, pos_x, pos_y, pos_z, pos_var, svin_dur, svin_var = struct.unpack(
        "<IdddfIf", payload[:40]
    )
    return TimingModeConfig(
        mode=mode,
        fixed_pos_x=pos_x,
        fixed_pos_y=pos_y,
        fixed_pos_z=pos_z,
        fixed_pos_var=pos_var,
        svin_min_dur=svin_dur,
        svin_var_limit=svin_var,
    )


def build_cfg_tmode(
    mode: int,
    fixed_pos: tuple[float, float, float] | None = None,
    fixed_pos_acc: float = 1.0,
    survey_min_dur: int = 2000,
    survey_acc: float = 20.0,
) -> bytes:
    """Build CFG-TMODE payload (40 bytes).

    Args:
        mode: 0=Auto, 1=Survey-In, 2=Fixed
        fixed_pos: (X, Y, Z) ECEF coordinates in meters (required for mode=2)
        fixed_pos_acc: Position accuracy in meters (for mode=2)
        survey_min_dur: Survey minimum duration in seconds (for mode=1)
        survey_acc: Survey target accuracy in meters (for mode=1)
    """
    if fixed_pos is None:
        fixed_pos = (0.0, 0.0, 0.0)

    # Variance = accuracy squared
    fixed_pos_var = fixed_pos_acc**2
    survey_var_limit = survey_acc**2

    return struct.pack(
        "<IdddfIf",
        mode,  # U4: mode
        fixed_pos[0],  # R8: fixedPosX
        fixed_pos[1],  # R8: fixedPosY
        fixed_pos[2],  # R8: fixedPosZ
        fixed_pos_var,  # R4: fixedPosVar
        survey_min_dur,  # U4: svinMinDur
        survey_var_limit,  # R4: svinVarLimit
    )


def parse_cfg_navx(payload: bytes) -> NavEngineConfig:
    """Parse CFG-NAVX response payload (44 bytes)."""
    if len(payload) < 44:
        raise ValueError(f"CFG-NAVX payload too short: {len(payload)} bytes, expected 44")
    # Unpack the structure according to spec
    (
        mask,
        dyn_model,
        fix_mode,
        min_svs,
        max_svs,
        min_cno,
        res1,
        ini_fix_3d,
        min_elev,
        dr_limit,
        nav_system,
        wn_rollover,
        fixed_alt,
        fixed_alt_var,
        p_dop,
        t_dop,
        p_acc,
        t_acc,
        static_hold_th,
    ) = struct.unpack("<IbBbbBBbbbBHfffffff", payload[:44])
    return NavEngineConfig(
        mask=mask,
        dyn_model=dyn_model,
        fix_mode=fix_mode,
        min_svs=min_svs,
        max_svs=max_svs,
        min_cno=min_cno,
        ini_fix_3d=ini_fix_3d,
        min_elev=min_elev,
        dr_limit=dr_limit,
        nav_system=nav_system,
        wn_rollover=wn_rollover,
        fixed_alt=fixed_alt,
        fixed_alt_var=fixed_alt_var,
        p_dop=p_dop,
        t_dop=t_dop,
        p_acc=p_acc,
        t_acc=t_acc,
        static_hold_th=static_hold_th,
    )


def build_cfg_cfg(mask: int, mode: int) -> bytes:
    """Build CFG-CFG payload (4 bytes).

    Args:
        mask: Configuration sections to affect (bitmask, use CFG_MASK_* constants)
        mode: 0=Clear (reset to defaults), 1=Save (RAM to NVM), 2=Load (NVM to RAM)
    """
    return struct.pack("<HBB", mask, mode, 0)


def build_cfg_rst(nav_bbr_mask: int, reset_mode: int, start_mode: int) -> bytes:
    """Build CFG-RST payload (4 bytes).

    Args:
        nav_bbr_mask: BBR sections to clear (bitmask, use BBR_* constants)
        reset_mode: 0=HW immediate, 1=SW controlled, 2=SW GPS only, 4=HW after shutdown
        start_mode: 0=Hot, 1=Warm, 2=Cold, 3=Factory
    """
    return struct.pack("<HBB", nav_bbr_mask, reset_mode, start_mode)
