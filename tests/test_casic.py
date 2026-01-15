"""Tests for CASIC protocol implementation."""

import struct

import pytest

from casic import (
    ACK_ACK,
    ACK_NAK,
    BBR_ALL,
    BBR_ALMANAC,
    BBR_CLOCK_DRIFT,
    BBR_CONFIG,
    BBR_EPHEMERIS,
    BBR_HEALTH,
    BBR_IONOSPHERE,
    BBR_NAV_DATA,
    BBR_OSC_PARAMS,
    BBR_POSITION,
    BBR_RTC,
    BBR_UTC_PARAMS,
    CFG_CFG,
    CFG_MASK_ALL,
    CFG_MASK_GROUP,
    CFG_MASK_INF,
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
    CLS_ACK,
    CLS_CFG,
    MsgID,
    NavEngineConfig,
    PortConfig,
    RateConfig,
    ReceiverConfig,
    TimePulseConfig,
    TimingModeConfig,
    build_cfg_cfg,
    build_cfg_msg_set,
    build_cfg_navx,
    build_cfg_rst,
    calc_checksum,
    pack_msg,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
    parse_msg,
)
from casictool import GNSS, parse_gnss_arg, parse_nmea_out
from job import ConfigChanges


class TestMsgID:
    def test_equality(self) -> None:
        a = MsgID(0x05, 0x01)
        b = MsgID(0x05, 0x01)
        c = MsgID(0x05, 0x00)
        assert a == b
        assert a != c

    def test_hash(self) -> None:
        a = MsgID(0x05, 0x01)
        b = MsgID(0x05, 0x01)
        assert hash(a) == hash(b)
        d = {a: "ack"}
        assert d[b] == "ack"

    def test_repr(self) -> None:
        a = MsgID(0x05, 0x01)
        assert "05" in repr(a) and "01" in repr(a)

    def test_inequality_with_other_types(self) -> None:
        a = MsgID(0x05, 0x01)
        assert a != (0x05, 0x01)
        assert a != "MsgID(0x05, 0x01)"


class TestChecksum:
    def test_empty_payload(self) -> None:
        # ckSum = (id << 24) + (class << 16) + len = (0x00 << 24) + (0x06 << 16) + 0
        ck = calc_checksum(0x06, 0x00, b"")
        assert ck == 0x00060000

    def test_4byte_payload(self) -> None:
        # ckSum = (0x05 << 24) + (0x06 << 16) + 4 + 0x04030201 = 0x09090205
        ck = calc_checksum(0x06, 0x05, bytes([0x01, 0x02, 0x03, 0x04]))
        assert ck == 0x09090205

    def test_partial_word_payload(self) -> None:
        # ckSum = (0x01 << 24) + (0x06 << 16) + 2 + 0x0000CDAB = 0x0106CDAD
        ck = calc_checksum(0x06, 0x01, bytes([0xAB, 0xCD]))
        assert ck == 0x0106CDAD


class TestPackMsg:
    def test_pack_empty_payload(self) -> None:
        msg = pack_msg(0x06, 0x00, b"")
        assert msg[:2] == bytes([0xBA, 0xCE])
        assert msg[2:4] == bytes([0x00, 0x00])
        assert msg[4] == 0x06
        assert msg[5] == 0x00
        assert len(msg) == 10

    def test_pack_with_payload(self) -> None:
        payload = bytes([0x01, 0x02, 0x03, 0x04])
        msg = pack_msg(0x06, 0x05, payload)
        assert msg[:2] == bytes([0xBA, 0xCE])
        assert msg[2:4] == bytes([0x04, 0x00])
        assert msg[4:6] == bytes([0x06, 0x05])
        assert msg[6:10] == payload
        assert len(msg) == 14

    def test_pack_checksum_placement(self) -> None:
        msg = pack_msg(0x06, 0x00, b"")
        # 0x00060000 in little-endian
        expected_checksum = bytes([0x00, 0x00, 0x06, 0x00])
        assert msg[6:10] == expected_checksum


class TestParseMsg:
    def test_parse_valid_message(self) -> None:
        payload = bytes([0x06, 0x00])
        msg = pack_msg(0x05, 0x01, payload)
        result = parse_msg(msg)
        assert result is not None
        mid, data = result
        assert mid == MsgID(0x05, 0x01)
        assert data == payload

    def test_parse_bad_sync(self) -> None:
        msg = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        result = parse_msg(msg)
        assert result is None

    def test_parse_bad_checksum(self) -> None:
        msg = pack_msg(0x05, 0x01, bytes([0x06, 0x00]))
        corrupted = msg[:-1] + bytes([msg[-1] ^ 0xFF])
        result = parse_msg(corrupted)
        assert result is None

    def test_parse_too_short(self) -> None:
        result = parse_msg(bytes([0xBA, 0xCE, 0x00]))
        assert result is None

    def test_parse_truncated_payload(self) -> None:
        msg = pack_msg(0x05, 0x01, bytes([0x06, 0x00]))
        result = parse_msg(msg[:-2])
        assert result is None

    def test_roundtrip(self) -> None:
        test_cases = [
            (0x05, 0x00, bytes([0x06, 0x01])),
            (0x05, 0x01, bytes([0x06, 0x00])),
            (0x06, 0x00, b""),
            (0x06, 0x05, bytes([0xFF, 0x00, 0x01, 0x00])),
        ]
        for cls, id, payload in test_cases:
            msg = pack_msg(cls, id, payload)
            result = parse_msg(msg)
            assert result is not None
            mid, data = result
            assert mid.cls == cls
            assert mid.id == id
            assert data == payload


class TestMessageConstants:
    def test_class_values(self) -> None:
        assert CLS_ACK == 0x05
        assert CLS_CFG == 0x06

    def test_ack_ids(self) -> None:
        assert ACK_NAK == MsgID(CLS_ACK, 0x00)
        assert ACK_ACK == MsgID(CLS_ACK, 0x01)

    def test_cfg_ids(self) -> None:
        assert CFG_PRT == MsgID(CLS_CFG, 0x00)
        assert CFG_MSG == MsgID(CLS_CFG, 0x01)
        assert CFG_RST == MsgID(CLS_CFG, 0x02)
        assert CFG_TP == MsgID(CLS_CFG, 0x03)
        assert CFG_RATE == MsgID(CLS_CFG, 0x04)
        assert CFG_CFG == MsgID(CLS_CFG, 0x05)
        assert CFG_TMODE == MsgID(CLS_CFG, 0x06)
        assert CFG_NAVX == MsgID(CLS_CFG, 0x07)

    def test_ack_hashable(self) -> None:
        d = {ACK_ACK: "acknowledged", ACK_NAK: "not acknowledged"}
        assert d[MsgID(CLS_ACK, 0x01)] == "acknowledged"
        assert d[MsgID(CLS_ACK, 0x00)] == "not acknowledged"


class TestPortConfig:
    def test_protocol_mask_flags(self) -> None:
        cfg = PortConfig(port_id=0, proto_mask=0x33, mode=0x0800, baud_rate=9600)
        assert cfg.binary_input is True
        assert cfg.text_input is True
        assert cfg.binary_output is True
        assert cfg.text_output is True
        assert cfg.baud_rate == 9600

    def test_data_format_8n1(self) -> None:
        # 8 bits = 0b11 << 6 = 0xC0, no parity = 0b100 << 9 = 0x800, 1 stop = 0b00 << 12
        mode = 0xC0 | 0x800
        cfg = PortConfig(port_id=0, proto_mask=0x33, mode=mode, baud_rate=9600)
        assert cfg.data_format == "8N1"

    def test_parse_cfg_prt(self) -> None:
        payload = struct.pack("<BBHI", 0, 0x33, 0x08C0, 9600)
        cfg = parse_cfg_prt(payload)
        assert cfg.baud_rate == 9600
        assert cfg.port_id == 0
        assert cfg.proto_mask == 0x33

    def test_format(self) -> None:
        cfg = PortConfig(port_id=0, proto_mask=0x33, mode=0x08C0, baud_rate=9600)
        output = cfg.format()
        assert "9600" in output
        assert "8N1" in output


class TestRateConfig:
    def test_update_rate_hz(self) -> None:
        cfg = RateConfig(interval_ms=1000)
        assert cfg.update_rate_hz == 1.0

    def test_update_rate_hz_zero(self) -> None:
        cfg = RateConfig(interval_ms=0)
        assert cfg.update_rate_hz == 0.0

    def test_parse_cfg_rate(self) -> None:
        payload = struct.pack("<HH", 1000, 0)
        cfg = parse_cfg_rate(payload)
        assert cfg.interval_ms == 1000

    def test_format(self) -> None:
        cfg = RateConfig(interval_ms=1000)
        assert "1.0 Hz" in cfg.format()


class TestTimePulseConfig:
    def test_enabled(self) -> None:
        cfg = TimePulseConfig(
            interval_us=1000000, width_us=100000, enable=1,
            polarity=0, time_ref=0, time_source=0, user_delay=0.0
        )
        assert cfg.enabled is True

    def test_disabled(self) -> None:
        cfg = TimePulseConfig(
            interval_us=1000000, width_us=100000, enable=0,
            polarity=0, time_ref=0, time_source=0, user_delay=0.0
        )
        assert cfg.enabled is False

    def test_parse_cfg_tp(self) -> None:
        payload = struct.pack("<IIbbbBf", 1000000, 100000, 1, 0, 0, 0, 0.0)
        cfg = parse_cfg_tp(payload)
        assert cfg.interval_us == 1000000
        assert cfg.width_us == 100000
        assert cfg.enable == 1

    def test_format_enabled(self) -> None:
        cfg = TimePulseConfig(
            interval_us=1000000, width_us=100000, enable=1,
            polarity=0, time_ref=0, time_source=0, user_delay=0.0
        )
        output = cfg.format()
        assert "enabled" in output
        assert "rising" in output

    def test_format_disabled(self) -> None:
        cfg = TimePulseConfig(
            interval_us=1000000, width_us=100000, enable=0,
            polarity=0, time_ref=0, time_source=0, user_delay=0.0
        )
        assert "disabled" in cfg.format()


class TestTimingModeConfig:
    def test_mode_str(self) -> None:
        cfg = TimingModeConfig(
            mode=0, fixed_pos_x=0, fixed_pos_y=0, fixed_pos_z=0,
            fixed_pos_var=0, svin_min_dur=0, svin_var_limit=0
        )
        assert cfg.mode_str == "Auto"

    def test_parse_cfg_tmode(self) -> None:
        payload = struct.pack("<IdddfIf", 0, 1.0, 2.0, 3.0, 4.0, 100, 5.0)
        cfg = parse_cfg_tmode(payload)
        assert cfg.mode == 0
        assert cfg.fixed_pos_x == 1.0
        assert cfg.fixed_pos_y == 2.0
        assert cfg.fixed_pos_z == 3.0

    def test_format_auto(self) -> None:
        cfg = TimingModeConfig(
            mode=0, fixed_pos_x=0, fixed_pos_y=0, fixed_pos_z=0,
            fixed_pos_var=0, svin_min_dur=0, svin_var_limit=0
        )
        assert "auto" in cfg.format()


class TestNavEngineConfig:
    def test_gnss_list(self) -> None:
        cfg = NavEngineConfig(
            mask=0, dyn_model=0, fix_mode=3, min_svs=0, max_svs=0,
            min_cno=0, ini_fix_3d=0, min_elev=0, dr_limit=0,
            nav_system=0x07, wn_rollover=0, fixed_alt=0, fixed_alt_var=0,
            p_dop=0, t_dop=0, p_acc=0, t_acc=0, static_hold_th=0
        )
        assert cfg.gnss_list == ["GPS", "BDS", "GLONASS"]

    def test_gnss_list_gps_only(self) -> None:
        cfg = NavEngineConfig(
            mask=0, dyn_model=0, fix_mode=3, min_svs=0, max_svs=0,
            min_cno=0, ini_fix_3d=0, min_elev=0, dr_limit=0,
            nav_system=0x01, wn_rollover=0, fixed_alt=0, fixed_alt_var=0,
            p_dop=0, t_dop=0, p_acc=0, t_acc=0, static_hold_th=0
        )
        assert cfg.gnss_list == ["GPS"]

    def test_parse_cfg_navx(self) -> None:
        # Format: mask(I), dyn_model(b), fix_mode(B), min_svs(b), max_svs(b),
        #         min_cno(B), res1(B), ini_fix_3d(b), min_elev(b), dr_limit(b),
        #         nav_system(B), wn_rollover(H), then 7 floats
        payload = struct.pack(
            "<IbBbbBBbbbBHfffffff",
            0xFFFF, 0, 3, 4, 12, 6, 0, 1, 5, 60, 0x07, 2000,
            0.0, 0.0, 25.0, 25.0, 100.0, 100.0, 0.0
        )
        cfg = parse_cfg_navx(payload)
        assert cfg.nav_system == 0x07
        assert cfg.fix_mode == 3

    def test_format(self) -> None:
        cfg = NavEngineConfig(
            mask=0, dyn_model=0, fix_mode=3, min_svs=0, max_svs=0,
            min_cno=0, ini_fix_3d=0, min_elev=0, dr_limit=0,
            nav_system=0x07, wn_rollover=0, fixed_alt=0, fixed_alt_var=0,
            p_dop=0, t_dop=0, p_acc=0, t_acc=0, static_hold_th=0
        )
        output = cfg.format()
        assert "GPS" in output
        assert "BDS" in output
        assert "GLONASS" in output


class TestReceiverConfig:
    def test_format_complete(self) -> None:
        config = ReceiverConfig(
            port=PortConfig(port_id=0, proto_mask=0x33, mode=0x08C0, baud_rate=9600),
            rate=RateConfig(interval_ms=1000),
        )
        output = config.format()
        assert "9600" in output
        assert "1.0 Hz" in output


class TestCfgMaskConstants:
    def test_cfg_mask_bits(self) -> None:
        assert CFG_MASK_PORT == 0x0001
        assert CFG_MASK_MSG == 0x0002
        assert CFG_MASK_INF == 0x0004
        assert CFG_MASK_NAV == 0x0008
        assert CFG_MASK_TP == 0x0010
        assert CFG_MASK_GROUP == 0x0020
        assert CFG_MASK_ALL == 0xFFFF

    def test_cfg_masks_are_distinct_bits(self) -> None:
        masks = [CFG_MASK_PORT, CFG_MASK_MSG, CFG_MASK_INF, CFG_MASK_NAV, CFG_MASK_TP, CFG_MASK_GROUP]
        # Each mask should be a single bit
        for mask in masks:
            assert bin(mask).count("1") == 1
        # All masks combined should have no overlap
        combined = 0
        for mask in masks:
            assert (combined & mask) == 0
            combined |= mask


class TestBbrMaskConstants:
    def test_bbr_mask_bits(self) -> None:
        assert BBR_EPHEMERIS == 0x0001
        assert BBR_ALMANAC == 0x0002
        assert BBR_HEALTH == 0x0004
        assert BBR_IONOSPHERE == 0x0008
        assert BBR_POSITION == 0x0010
        assert BBR_CLOCK_DRIFT == 0x0020
        assert BBR_OSC_PARAMS == 0x0040
        assert BBR_UTC_PARAMS == 0x0080
        assert BBR_RTC == 0x0100
        assert BBR_CONFIG == 0x0200

    def test_bbr_nav_data_composite(self) -> None:
        # BBR_NAV_DATA should be bits 0-8 (all nav data, no config)
        expected = (
            BBR_EPHEMERIS | BBR_ALMANAC | BBR_HEALTH | BBR_IONOSPHERE |
            BBR_POSITION | BBR_CLOCK_DRIFT | BBR_OSC_PARAMS | BBR_UTC_PARAMS | BBR_RTC
        )
        assert BBR_NAV_DATA == expected
        assert BBR_NAV_DATA == 0x01FF

    def test_bbr_all_composite(self) -> None:
        # BBR_ALL should be bits 0-9 (everything including config)
        expected = BBR_NAV_DATA | BBR_CONFIG
        assert BBR_ALL == expected
        assert BBR_ALL == 0x03FF


class TestBuildCfgCfg:
    def test_save_all_config(self) -> None:
        payload = build_cfg_cfg(CFG_MASK_ALL, mode=1)
        assert len(payload) == 4
        mask, mode, reserved = struct.unpack("<HBB", payload)
        assert mask == 0xFFFF
        assert mode == 1  # Save
        assert reserved == 0

    def test_load_all_config(self) -> None:
        payload = build_cfg_cfg(CFG_MASK_ALL, mode=2)
        mask, mode, reserved = struct.unpack("<HBB", payload)
        assert mask == 0xFFFF
        assert mode == 2  # Load

    def test_clear_all_config(self) -> None:
        payload = build_cfg_cfg(CFG_MASK_ALL, mode=0)
        mask, mode, reserved = struct.unpack("<HBB", payload)
        assert mask == 0xFFFF
        assert mode == 0  # Clear

    def test_save_nav_only(self) -> None:
        payload = build_cfg_cfg(CFG_MASK_NAV, mode=1)
        mask, mode, reserved = struct.unpack("<HBB", payload)
        assert mask == 0x0008  # CFG_MASK_NAV
        assert mode == 1


class TestBuildCfgRst:
    def test_cold_start(self) -> None:
        payload = build_cfg_rst(BBR_NAV_DATA, reset_mode=1, start_mode=2)
        assert len(payload) == 4
        nav_bbr_mask, reset_mode, start_mode = struct.unpack("<HBB", payload)
        assert nav_bbr_mask == 0x01FF  # BBR_NAV_DATA
        assert reset_mode == 1  # SW controlled
        assert start_mode == 2  # Cold start

    def test_factory_start(self) -> None:
        payload = build_cfg_rst(BBR_ALL, reset_mode=1, start_mode=3)
        nav_bbr_mask, reset_mode, start_mode = struct.unpack("<HBB", payload)
        assert nav_bbr_mask == 0x03FF  # BBR_ALL
        assert reset_mode == 1  # SW controlled
        assert start_mode == 3  # Factory start

    def test_hot_start(self) -> None:
        payload = build_cfg_rst(0, reset_mode=1, start_mode=0)
        nav_bbr_mask, reset_mode, start_mode = struct.unpack("<HBB", payload)
        assert nav_bbr_mask == 0
        assert start_mode == 0  # Hot start

    def test_hw_reset(self) -> None:
        payload = build_cfg_rst(BBR_NAV_DATA, reset_mode=0, start_mode=2)
        nav_bbr_mask, reset_mode, start_mode = struct.unpack("<HBB", payload)
        assert reset_mode == 0  # HW immediate


class TestBuildCfgMsgSet:
    def test_enable_gga_rate_1(self) -> None:
        """Test CFG-MSG SET payload for enabling GGA at rate 1."""
        payload = build_cfg_msg_set(0x4E, 0x00, 1)
        assert payload == bytes([0x4E, 0x00, 0x01, 0x00])

    def test_disable_rmc(self) -> None:
        """Test CFG-MSG SET payload for disabling RMC."""
        payload = build_cfg_msg_set(0x4E, 0x04, 0)
        assert payload == bytes([0x4E, 0x04, 0x00, 0x00])

    def test_enable_gsv_rate_5(self) -> None:
        """Test CFG-MSG SET payload for enabling GSV at rate 5."""
        payload = build_cfg_msg_set(0x4E, 0x03, 5)
        assert payload == bytes([0x4E, 0x03, 0x05, 0x00])

    def test_payload_structure(self) -> None:
        """Test payload is correctly structured as [cls][id][rate(U2)]."""
        payload = build_cfg_msg_set(0x4E, 0x08, 10)
        assert len(payload) == 4
        cls_id, msg_id, rate = struct.unpack("<BBH", payload)
        assert cls_id == 0x4E
        assert msg_id == 0x08
        assert rate == 10


class TestParseNmeaOut:
    def test_basic(self) -> None:
        """Test parsing messages to enable."""
        enable = parse_nmea_out("GGA,RMC,ZDA")
        # GGA=0, RMC=4, ZDA=6
        assert enable == [1, 0, 0, 0, 1, 0, 1]

    def test_case_insensitive(self) -> None:
        """Test case insensitivity."""
        enable = parse_nmea_out("gga,Rmc,zda")
        assert enable == [1, 0, 0, 0, 1, 0, 1]

    def test_whitespace_handling(self) -> None:
        """Test whitespace is trimmed."""
        enable = parse_nmea_out(" GGA , RMC , ZDA ")
        assert enable == [1, 0, 0, 0, 1, 0, 1]

    def test_empty_items_ignored(self) -> None:
        """Test empty items in comma list are ignored."""
        enable = parse_nmea_out("GGA,,RMC,")
        # GGA=0, RMC=4
        assert enable == [1, 0, 0, 0, 1, 0, 0]

    def test_invalid_message(self) -> None:
        """Test invalid message name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown NMEA message: INVALID"):
            parse_nmea_out("GGA,INVALID")

    def test_all_valid_messages(self) -> None:
        """Test all valid message names are accepted."""
        enable = parse_nmea_out("GGA,GLL,GSA,GSV,RMC,VTG,ZDA")
        assert enable == [1, 1, 1, 1, 1, 1, 1]


class TestBuildCfgNavx:
    def test_gps_only(self) -> None:
        """Test building payload with GPS only."""
        config = NavEngineConfig(
            mask=0xFFFF, dyn_model=0, fix_mode=3, min_svs=4, max_svs=12,
            min_cno=6, ini_fix_3d=1, min_elev=5, dr_limit=60,
            nav_system=0x07, wn_rollover=2000, fixed_alt=0.0, fixed_alt_var=0.0,
            p_dop=25.0, t_dop=25.0, p_acc=100.0, t_acc=100.0, static_hold_th=0.0
        )
        payload = build_cfg_navx(config, nav_system=0x01)
        assert len(payload) == 44
        # Check nav_system is at offset 13
        assert payload[13] == 0x01

    def test_all_constellations(self) -> None:
        """Test building payload with all constellations enabled."""
        config = NavEngineConfig(
            mask=0xFFFF, dyn_model=0, fix_mode=3, min_svs=4, max_svs=12,
            min_cno=6, ini_fix_3d=1, min_elev=5, dr_limit=60,
            nav_system=0x01, wn_rollover=2000, fixed_alt=0.0, fixed_alt_var=0.0,
            p_dop=25.0, t_dop=25.0, p_acc=100.0, t_acc=100.0, static_hold_th=0.0
        )
        payload = build_cfg_navx(config, nav_system=0x07)
        assert payload[13] == 0x07

    def test_preserves_other_fields(self) -> None:
        """Test that other fields are preserved when only changing nav_system."""
        config = NavEngineConfig(
            mask=0xFFFF, dyn_model=3, fix_mode=2, min_svs=4, max_svs=12,
            min_cno=6, ini_fix_3d=1, min_elev=10, dr_limit=60,
            nav_system=0x07, wn_rollover=2000, fixed_alt=100.0, fixed_alt_var=1.0,
            p_dop=25.0, t_dop=25.0, p_acc=100.0, t_acc=100.0, static_hold_th=0.5
        )
        payload = build_cfg_navx(config, nav_system=0x01)
        # Parse the payload back to verify fields preserved
        parsed = parse_cfg_navx(payload)
        assert parsed.dyn_model == 3
        assert parsed.fix_mode == 2
        assert parsed.min_elev == 10
        assert parsed.nav_system == 0x01  # Changed
        assert parsed.fixed_alt == 100.0

    def test_none_nav_system_keeps_existing(self) -> None:
        """Test that nav_system=None keeps existing value."""
        config = NavEngineConfig(
            mask=0xFFFF, dyn_model=0, fix_mode=3, min_svs=4, max_svs=12,
            min_cno=6, ini_fix_3d=1, min_elev=5, dr_limit=60,
            nav_system=0x05, wn_rollover=2000, fixed_alt=0.0, fixed_alt_var=0.0,
            p_dop=25.0, t_dop=25.0, p_acc=100.0, t_acc=100.0, static_hold_th=0.0
        )
        payload = build_cfg_navx(config, nav_system=None)
        assert payload[13] == 0x05

    def test_payload_structure(self) -> None:
        """Test payload has correct structure."""
        config = NavEngineConfig(
            mask=0xFFFF, dyn_model=0, fix_mode=3, min_svs=4, max_svs=12,
            min_cno=6, ini_fix_3d=1, min_elev=5, dr_limit=60,
            nav_system=0x07, wn_rollover=2000, fixed_alt=0.0, fixed_alt_var=0.0,
            p_dop=25.0, t_dop=25.0, p_acc=100.0, t_acc=100.0, static_hold_th=0.0
        )
        payload = build_cfg_navx(config)
        # Mask should be 0xFFFFFFFF (apply all)
        mask = struct.unpack("<I", payload[0:4])[0]
        assert mask == 0xFFFFFFFF

    def test_roundtrip(self) -> None:
        """Test parse -> build -> parse roundtrip."""
        original = struct.pack(
            "<IbBbbBBbbbBHfffffff",
            0xFFFF, 0, 3, 4, 12, 6, 0, 1, 5, 60, 0x07, 2000,
            0.0, 0.0, 25.0, 25.0, 100.0, 100.0, 0.0
        )
        config = parse_cfg_navx(original)
        rebuilt = build_cfg_navx(config)
        reparsed = parse_cfg_navx(rebuilt)
        assert reparsed.nav_system == config.nav_system
        assert reparsed.dyn_model == config.dyn_model
        assert reparsed.fix_mode == config.fix_mode


class TestParseGnssArg:
    def test_single_gps(self) -> None:
        """Test parsing GPS only."""
        assert parse_gnss_arg("GPS") == {GNSS.GPS}

    def test_single_bds(self) -> None:
        """Test parsing BDS only."""
        assert parse_gnss_arg("BDS") == {GNSS.BDS}

    def test_single_glo(self) -> None:
        """Test parsing GLO only."""
        assert parse_gnss_arg("GLO") == {GNSS.GLO}

    def test_multiple_constellations(self) -> None:
        """Test parsing multiple constellations."""
        assert parse_gnss_arg("GPS,BDS") == {GNSS.GPS, GNSS.BDS}
        assert parse_gnss_arg("GPS,GLO") == {GNSS.GPS, GNSS.GLO}
        assert parse_gnss_arg("BDS,GLO") == {GNSS.BDS, GNSS.GLO}
        assert parse_gnss_arg("GPS,BDS,GLO") == {GNSS.GPS, GNSS.BDS, GNSS.GLO}

    def test_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert parse_gnss_arg("gps") == {GNSS.GPS}
        assert parse_gnss_arg("Gps,bds") == {GNSS.GPS, GNSS.BDS}

    def test_glonass_aliases(self) -> None:
        """Test GLO, GLN, GLONASS all map to GLO."""
        assert parse_gnss_arg("GLO") == {GNSS.GLO}
        assert parse_gnss_arg("GLN") == {GNSS.GLO}
        assert parse_gnss_arg("GLONASS") == {GNSS.GLO}

    def test_whitespace_handling(self) -> None:
        """Test whitespace is trimmed."""
        assert parse_gnss_arg(" GPS , BDS ") == {GNSS.GPS, GNSS.BDS}

    def test_empty_items_ignored(self) -> None:
        """Test empty items in comma list are ignored."""
        assert parse_gnss_arg("GPS,,BDS,") == {GNSS.GPS, GNSS.BDS}

    def test_invalid_constellation(self) -> None:
        """Test invalid constellation raises ValueError."""
        with pytest.raises(ValueError, match="Unknown constellation"):
            parse_gnss_arg("INVALID")

    def test_unsupported_galileo(self) -> None:
        """Test Galileo raises specific unsupported error."""
        with pytest.raises(ValueError, match="Unsupported constellation.*GAL"):
            parse_gnss_arg("GAL")

    def test_unsupported_qzss(self) -> None:
        """Test QZSS raises specific unsupported error."""
        with pytest.raises(ValueError, match="Unsupported constellation.*QZSS"):
            parse_gnss_arg("QZSS")

    def test_empty_string(self) -> None:
        """Test empty string returns empty set."""
        assert parse_gnss_arg("") == set()


class TestConfigChangesMarkMsg:
    def test_initial_mask_zero(self) -> None:
        """Test ConfigChanges starts with zero mask."""
        changes = ConfigChanges()
        assert changes.mask == 0

    def test_mark_msg(self) -> None:
        """Test mark_msg sets CFG_MASK_MSG bit."""
        changes = ConfigChanges()
        changes.mark_msg()
        assert changes.mask & CFG_MASK_MSG != 0

    def test_mark_msg_multiple_calls(self) -> None:
        """Test mark_msg is idempotent."""
        changes = ConfigChanges()
        changes.mark_msg()
        changes.mark_msg()
        assert changes.mask == CFG_MASK_MSG

    def test_mark_msg_and_nav(self) -> None:
        """Test mark_msg and mark_nav can both be set."""
        changes = ConfigChanges()
        changes.mark_nav()
        changes.mark_msg()
        assert changes.mask & CFG_MASK_MSG != 0
        assert changes.mask & CFG_MASK_NAV != 0
        assert changes.mask == (CFG_MASK_MSG | CFG_MASK_NAV)
