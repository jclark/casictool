"""Tests for CASIC protocol implementation."""

import struct

from casic import (
    ACK_ACK,
    ACK_NAK,
    CFG_CFG,
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
    calc_checksum,
    pack_msg,
    parse_cfg_navx,
    parse_cfg_prt,
    parse_cfg_rate,
    parse_cfg_tmode,
    parse_cfg_tp,
    parse_msg,
)


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
