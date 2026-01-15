"""Tests for CASIC protocol implementation."""

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
    calc_checksum,
    pack_msg,
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
        ck = calc_checksum(0x06, 0x00, b"")
        assert ck == 0x00060000

    def test_4byte_payload(self) -> None:
        ck = calc_checksum(0x06, 0x05, bytes([0x01, 0x02, 0x03, 0x04]))
        assert ck == 0x09090205

    def test_partial_word_payload(self) -> None:
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
