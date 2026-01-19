"""CASIC protocol implementation: framing, checksum, messages, and payload parsing."""

from __future__ import annotations

import math
import struct
from collections import deque
from dataclasses import dataclass

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

# Class number to name prefix
CLS_NAMES: dict[int, str] = {
    CLS_NAV: "NAV",
    CLS_TIM: "TIM",
    CLS_RXM: "RXM",
    CLS_ACK: "ACK",
    CLS_CFG: "CFG",
    CLS_MSG: "MSG",
    CLS_MON: "MON",
    CLS_AID: "AID",
    CLS_NMEA: "NMEA",
}


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
CFG_GROUP = MsgID(CLS_CFG, 0x08)
CFG_INS = MsgID(CLS_CFG, 0x10)

# NAV messages
NAV_STATUS = MsgID(CLS_NAV, 0x00)
NAV_DOP = MsgID(CLS_NAV, 0x01)
NAV_SOL = MsgID(CLS_NAV, 0x02)
NAV_PV = MsgID(CLS_NAV, 0x03)
NAV_IMUATT = MsgID(CLS_NAV, 0x06)
NAV_TIMEUTC = MsgID(CLS_NAV, 0x10)
NAV_CLOCK = MsgID(CLS_NAV, 0x11)
NAV_GPSINFO = MsgID(CLS_NAV, 0x20)
NAV_BDSINFO = MsgID(CLS_NAV, 0x21)
NAV_GLNINFO = MsgID(CLS_NAV, 0x22)

# TIM messages
TIM_TP = MsgID(CLS_TIM, 0x00)

# RXM messages
RXM_SENSOR = MsgID(CLS_RXM, 0x07)
RXM_MEASX = MsgID(CLS_RXM, 0x10)
RXM_SVPOS = MsgID(CLS_RXM, 0x11)

# MSG messages (satellite navigation data)
MSG_BDSUTC = MsgID(CLS_MSG, 0x00)
MSG_BDSION = MsgID(CLS_MSG, 0x01)
MSG_BDSEPH = MsgID(CLS_MSG, 0x02)
MSG_GPSUTC = MsgID(CLS_MSG, 0x05)
MSG_GPSION = MsgID(CLS_MSG, 0x06)
MSG_GPSEPH = MsgID(CLS_MSG, 0x07)
MSG_GLNEPH = MsgID(CLS_MSG, 0x08)

# AID messages
AID_INI = MsgID(CLS_AID, 0x01)
AID_HUI = MsgID(CLS_AID, 0x03)

# MON messages (MON_VER already defined above)
MON_HW = MsgID(CLS_MON, 0x09)

# NMEA message IDs (Class 0x4E)
NMEA_GGA = MsgID(CLS_NMEA, 0x00)
NMEA_GLL = MsgID(CLS_NMEA, 0x01)
NMEA_GSA = MsgID(CLS_NMEA, 0x02)
NMEA_GSV = MsgID(CLS_NMEA, 0x03)
NMEA_RMC = MsgID(CLS_NMEA, 0x04)
NMEA_VTG = MsgID(CLS_NMEA, 0x05)
NMEA_ZDA = MsgID(CLS_NMEA, 0x08)

# List of standard NMEA messages to query
NMEA_MESSAGES: list[tuple[str, MsgID]] = [
    ("GGA", NMEA_GGA),
    ("GLL", NMEA_GLL),
    ("GSA", NMEA_GSA),
    ("GSV", NMEA_GSV),
    ("RMC", NMEA_RMC),
    ("VTG", NMEA_VTG),
    ("ZDA", NMEA_ZDA),
]


def _build_msg_names() -> dict[tuple[int, int], str]:
    """Build message name lookup from MsgID constants."""
    names: dict[tuple[int, int], str] = {}
    for name, obj in globals().items():
        if isinstance(obj, MsgID) and "_" in name:
            # Convert ACK_ACK -> "ACK-ACK", CFG_TP -> "CFG-TP"
            msg_name = name.replace("_", "-")
            names[(obj.cls, obj.id)] = msg_name
    return names


MSG_NAMES: dict[tuple[int, int], str] = _build_msg_names()

# Reverse lookup: message name -> (cls, id)
MSG_IDS: dict[str, tuple[int, int]] = {name: key for key, name in MSG_NAMES.items()}


def msg_name(cls: int, id: int) -> str:
    """Get human-readable name for a message class/id pair.

    Returns known name (e.g., "CFG-TP"), or class prefix with hex ID if class
    is known (e.g., "NAV-0x17"), or both as hex (e.g., "0x01-0x17").
    """
    name = MSG_NAMES.get((cls, id))
    if name:
        return name
    cls_prefix = CLS_NAMES.get(cls)
    if cls_prefix:
        return f"{cls_prefix}-0x{id:02X}"
    return f"0x{cls:02X}-0x{id:02X}"


# Mask bits for CFG-CFG (configuration sections)
CFG_MASK_PORT = 0x0001  # B0: CFG-PRT
CFG_MASK_MSG = 0x0002  # B1: CFG-MSG
CFG_MASK_INF = 0x0004  # B2: CFG-INF
CFG_MASK_NAV = 0x0008  # B3: CFG-RATE, CFG-TMODE, CFG-NAVX (navigation config)
CFG_MASK_TP = 0x0010  # B4: CFG-TP
CFG_MASK_GROUP = 0x0020  # B5: CFG-GROUP
CFG_MASK_ALL = 0xFFFF  # All sections

# Port IDs for CFG-PRT
PORT_UART0 = 0x00
PORT_UART1 = 0x01
PORT_CURRENT = 0xFF

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

# Reset mask: clear all except clock drift and osc params (learned, not from satellites)
BBR_RESET = (
    BBR_EPHEMERIS | BBR_ALMANAC | BBR_HEALTH | BBR_IONOSPHERE |
    BBR_POSITION | BBR_UTC_PARAMS | BBR_RTC | BBR_CONFIG
)  # 0x039F

# Start modes for CFG-RST
START_HOT = 0
START_WARM = 1
START_COLD = 2
START_FACTORY = 3

# Reset modes for CFG-RST
RESET_HW_IMMEDIATE = 0
RESET_SW_CONTROLLED = 1
RESET_SW_GPS_ONLY = 2
RESET_HW_AFTER_SHUTDOWN = 4


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


MAX_CASIC_PAYLOAD = 4096
MAX_NMEA_LEN = 1024


@dataclass(frozen=True)
class CasicPacket:
    """Parsed CASIC packet."""

    msg_id: MsgID
    payload: bytes
    timestamp: float
    raw: bytes


@dataclass(frozen=True)
class NmeaSentence:
    """Parsed NMEA sentence."""

    data: bytes
    timestamp: float


@dataclass(frozen=True)
class UnknownBytes:
    """Unrecognized bytes from the stream."""

    data: bytes
    timestamp: float


StreamEvent = CasicPacket | NmeaSentence | UnknownBytes


class CasicStreamParser:
    """Incremental stream parser for CASIC binary and NMEA sentences."""

    _STATE_IDLE = 0
    _STATE_SYNC2 = 1
    _STATE_LEN1 = 2
    _STATE_LEN2 = 3
    _STATE_BODY = 4
    _STATE_NMEA = 5

    def __init__(self) -> None:
        self._state = self._STATE_IDLE
        self._casic_buf = bytearray()
        self._nmea_buf = bytearray()
        self._unknown_buf = bytearray()
        self._casic_ts = 0.0
        self._nmea_ts = 0.0
        self._unknown_ts = 0.0
        self._length_lo = 0
        self._remaining = 0
        self._queue: deque[StreamEvent] = deque()

    def _reset_casic(self) -> None:
        self._casic_buf.clear()
        self._length_lo = 0
        self._remaining = 0

    def _reset_nmea(self) -> None:
        self._nmea_buf.clear()

    def _reset_unknown(self) -> None:
        self._unknown_buf.clear()
        self._unknown_ts = 0.0

    def _queue_unknown(self, data: bytes, ts: float) -> None:
        if data:
            self._queue.append(UnknownBytes(data=data, timestamp=ts))

    def _note_unknown(self, b: int, ts: float) -> None:
        if not self._unknown_buf:
            self._unknown_ts = ts
        self._unknown_buf.append(b)

    def _flush_unknown(self) -> None:
        if self._unknown_buf:
            self._queue_unknown(bytes(self._unknown_buf), self._unknown_ts)
            self._reset_unknown()

    def pop_event(self) -> StreamEvent | None:
        """Return next parsed event, if any."""
        if self._queue:
            return self._queue.popleft()
        return None

    def feed(self, data: bytes, ts: float) -> None:
        """Feed raw bytes into the parser."""
        for b in data:
            if self._state == self._STATE_IDLE:
                if b == SYNC1:
                    self._flush_unknown()
                    self._casic_ts = ts
                    self._casic_buf.append(b)
                    self._state = self._STATE_SYNC2
                elif b == 0x24:  # '$'
                    self._flush_unknown()
                    self._nmea_ts = ts
                    self._nmea_buf.append(b)
                    self._state = self._STATE_NMEA
                else:
                    self._note_unknown(b, ts)
                continue

            if self._state == self._STATE_SYNC2:
                if b == SYNC2:
                    self._casic_buf.append(b)
                    self._state = self._STATE_LEN1
                else:
                    self._queue_unknown(bytes(self._casic_buf), self._casic_ts)
                    self._reset_casic()
                    self._state = self._STATE_IDLE
                    if b == SYNC1:
                        self._flush_unknown()
                        self._casic_ts = ts
                        self._casic_buf.append(b)
                        self._state = self._STATE_SYNC2
                    elif b == 0x24:  # '$'
                        self._flush_unknown()
                        self._nmea_ts = ts
                        self._nmea_buf.append(b)
                        self._state = self._STATE_NMEA
                    else:
                        self._note_unknown(b, ts)
                continue

            if self._state == self._STATE_LEN1:
                self._casic_buf.append(b)
                self._length_lo = b
                self._state = self._STATE_LEN2
                continue

            if self._state == self._STATE_LEN2:
                self._casic_buf.append(b)
                length = self._length_lo | (b << 8)
                if length > MAX_CASIC_PAYLOAD:
                    self._queue_unknown(bytes(self._casic_buf), self._casic_ts)
                    self._reset_casic()
                    self._state = self._STATE_IDLE
                    continue
                self._remaining = length + 2 + 4
                self._state = self._STATE_BODY
                continue

            if self._state == self._STATE_BODY:
                self._casic_buf.append(b)
                self._remaining -= 1
                if self._remaining == 0:
                    full_msg = bytes(self._casic_buf)
                    parsed = parse_msg(full_msg)
                    if parsed is None:
                        self._queue_unknown(full_msg, self._casic_ts)
                    else:
                        msg_id, payload = parsed
                        self._queue.append(
                            CasicPacket(
                                msg_id=msg_id,
                                payload=payload,
                                timestamp=self._casic_ts,
                                raw=full_msg,
                            )
                        )
                    self._reset_casic()
                    self._state = self._STATE_IDLE
                continue

            if self._state == self._STATE_NMEA:
                self._nmea_buf.append(b)
                if b == 0x0A:  # '\n'
                    self._queue.append(
                        NmeaSentence(data=bytes(self._nmea_buf), timestamp=self._nmea_ts)
                    )
                    self._reset_nmea()
                    self._state = self._STATE_IDLE
                    continue
                if len(self._nmea_buf) > MAX_NMEA_LEN:
                    self._queue_unknown(bytes(self._nmea_buf), self._nmea_ts)
                    self._reset_nmea()
                    self._state = self._STATE_IDLE
                continue

        self._flush_unknown()


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
        return f"Serial speed: {self.baud_rate}"


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
class MessageRatesConfig:
    """CFG-MSG responses: NMEA and binary message output rates."""

    rates: dict[str, int]  # NMEA message name -> rate (0=off, 1=every fix, N=every N fixes)
    binary_rates: dict[str, int] | None = None  # CASIC binary message name -> rate

    def format(self) -> str:
        lines = []
        nmea_enabled = [name for name, rate in self.rates.items() if rate > 0]
        lines.append(f"NMEA messages enabled: {', '.join(nmea_enabled) if nmea_enabled else 'none'}")

        if self.binary_rates:
            casic_enabled = [name for name, rate in self.binary_rates.items() if rate > 0]
            lines.append(f"CASIC messages enabled: {', '.join(casic_enabled) if casic_enabled else 'none'}")
        else:
            lines.append("CASIC messages enabled: none")
        return "\n".join(lines)


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
        lines = [
            f"Constellations enabled: {gnss_str}",
            f"Minimum elevation: {self.min_elev}°",
        ]
        return "\n".join(lines)


@dataclass
class ReceiverConfig:
    """Container for all receiver configuration sections."""

    ports: list[PortConfig] | None = None
    rate: RateConfig | None = None
    message_rates: MessageRatesConfig | None = None
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
        if self.message_rates is not None:
            sections.append(self.message_rates.format())
        if self.ports:
            for port in self.ports:
                sections.append(port.format())
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


def build_cfg_prt(port_id: int, proto_mask: int, mode: int, baud_rate: int) -> bytes:
    """Build CFG-PRT SET payload (8 bytes)."""
    return struct.pack("<BBHI", port_id, proto_mask, mode, baud_rate)


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
    """Parse CFG-TMODE response payload (40 bytes).

    Note: The mode field is documented as U4 but the receiver returns
    unknown values in the upper 2 bytes. We parse as U2 mode + U2 reserved.
    """
    if len(payload) < 40:
        raise ValueError(f"CFG-TMODE payload too short: {len(payload)} bytes, expected 40")
    mode, _reserved, pos_x, pos_y, pos_z, pos_var, svin_dur, svin_var = struct.unpack(
        "<HHdddfIf", payload[:40]
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

    Note: The mode field is documented as U4 but we use U2 mode + U2 reserved
    to match receiver behavior (upper 2 bytes contain unknown values on read).
    """
    if fixed_pos is None:
        fixed_pos = (0.0, 0.0, 0.0)

    # Variance = accuracy squared
    fixed_pos_var = fixed_pos_acc**2
    survey_var_limit = survey_acc**2

    return struct.pack(
        "<HHdddfIf",
        mode,  # U2: mode
        0,  # U2: reserved
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


def build_cfg_msg_query(msg_cls: int, msg_id: int) -> bytes:
    """Build CFG-MSG query payload to query a specific message's rate.

    Args:
        msg_cls: Class ID of the message to query
        msg_id: Message ID of the message to query
    """
    return struct.pack("<BB", msg_cls, msg_id)


def build_cfg_msg_set(msg_cls: int, msg_id: int, rate: int) -> bytes:
    """Build CFG-MSG SET payload (4 bytes).

    Args:
        msg_cls: Message class to configure
        msg_id: Message ID within class
        rate: Output rate (0=off, 1=every fix, N=every N fixes)

    Returns:
        4-byte payload: [cls(U1)][id(U1)][rate(U2)]
    """
    return struct.pack("<BBH", msg_cls, msg_id, rate)


def parse_cfg_msg(payload: bytes) -> int:
    """Parse CFG-MSG response payload (4 bytes).

    Returns the output rate for the queried message.
    """
    if len(payload) < 4:
        raise ValueError(f"CFG-MSG payload too short: {len(payload)} bytes, expected 4")
    _cls_id, _msg_id, rate = struct.unpack("<BBH", payload[:4])
    return int(rate)


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


def build_cfg_tp(
    interval_us: int = 1000000,
    width_us: int = 100000,
    enable: int = 1,
    polarity: int = 0,
    time_ref: int = 0,
    time_source: int = 0,
    user_delay: float = 0.0,
) -> bytes:
    """Build CFG-TP payload (16 bytes).

    Args:
        interval_us: Pulse interval in microseconds (1000000 = 1Hz)
        width_us: Pulse width in microseconds
        enable: 0=Off, 1=On, 2=Auto, 3=FixOnly
        polarity: 0=Rising edge, 1=Falling edge
        time_ref: 0=UTC, 1=Satellite time
        time_source: 0=GPS, 1=BDS, 2=GLONASS
        user_delay: User delay compensation in seconds
    """
    return struct.pack(
        "<IIbbbBf",
        interval_us,
        width_us,
        enable,
        polarity,
        time_ref,
        time_source,
        user_delay,
    )


def build_cfg_navx(
    config: NavEngineConfig,
    nav_system: int | None = None,
    min_elev: int | None = None,
) -> bytes:
    """Build CFG-NAVX payload (44 bytes) from existing config.

    Uses read-modify-write approach: takes current config and optionally
    overrides nav_system and/or min_elev fields.

    Args:
        config: Current NavEngineConfig from parse_cfg_navx()
        nav_system: New constellation mask, or None to keep existing
            (B0=GPS, B1=BDS, B2=GLONASS)
        min_elev: New minimum elevation angle in degrees, or None to keep existing

    Returns:
        44-byte payload ready for CFG-NAVX SET command
    """
    system = nav_system if nav_system is not None else config.nav_system
    elev = min_elev if min_elev is not None else config.min_elev

    return struct.pack(
        "<IbBbbBBbbbBHfffffff",
        0xFFFFFFFF,  # mask: apply all fields
        config.dyn_model,
        config.fix_mode,
        config.min_svs,
        config.max_svs,
        config.min_cno,
        0,  # res1
        config.ini_fix_3d,
        elev,
        config.dr_limit,
        system,
        config.wn_rollover,
        config.fixed_alt,
        config.fixed_alt_var,
        config.p_dop,
        config.t_dop,
        config.p_acc,
        config.t_acc,
        config.static_hold_th,
    )
