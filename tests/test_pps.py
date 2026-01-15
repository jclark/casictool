"""Tests for PPS (time pulse) configuration."""

import struct

import pytest

from casic import CFG_MASK_TP, build_cfg_tp, parse_cfg_tp
from casictool import GNSS, parse_time_gnss_arg
from job import ConfigChanges


class TestBuildCfgTp:
    def test_default_values(self) -> None:
        """Test default 1Hz, 100ms pulse."""
        payload = build_cfg_tp()
        assert len(payload) == 16
        interval, width, enable = struct.unpack("<IIb", payload[:9])
        assert interval == 1000000  # 1 Hz
        assert width == 100000  # 100 ms
        assert enable == 1

    def test_disable_pps(self) -> None:
        """Test disable sets enable=0."""
        payload = build_cfg_tp(enable=0)
        enable = payload[8]
        assert enable == 0

    def test_time_source_gps(self) -> None:
        """Test time_source=0 for GPS."""
        payload = build_cfg_tp(time_source=0)
        time_source = payload[11]
        assert time_source == 0

    def test_time_source_bds(self) -> None:
        """Test time_source=1 for BDS."""
        payload = build_cfg_tp(time_source=1)
        time_source = payload[11]
        assert time_source == 1

    def test_time_source_glonass(self) -> None:
        """Test time_source=2 for GLONASS."""
        payload = build_cfg_tp(time_source=2)
        time_source = payload[11]
        assert time_source == 2

    def test_custom_width(self) -> None:
        """Test custom pulse width."""
        payload = build_cfg_tp(width_us=50000)  # 50ms
        interval, width = struct.unpack("<II", payload[:8])
        assert width == 50000

    def test_custom_interval(self) -> None:
        """Test custom pulse interval."""
        payload = build_cfg_tp(interval_us=500000)  # 2 Hz
        interval, width = struct.unpack("<II", payload[:8])
        assert interval == 500000

    def test_polarity_rising(self) -> None:
        """Test rising edge polarity (default)."""
        payload = build_cfg_tp(polarity=0)
        polarity = payload[9]
        assert polarity == 0

    def test_polarity_falling(self) -> None:
        """Test falling edge polarity."""
        payload = build_cfg_tp(polarity=1)
        polarity = struct.unpack("<b", payload[9:10])[0]
        assert polarity == 1

    def test_time_ref_utc(self) -> None:
        """Test UTC time reference (default)."""
        payload = build_cfg_tp(time_ref=0)
        time_ref = payload[10]
        assert time_ref == 0

    def test_time_ref_satellite(self) -> None:
        """Test satellite time reference."""
        payload = build_cfg_tp(time_ref=1)
        time_ref = struct.unpack("<b", payload[10:11])[0]
        assert time_ref == 1

    def test_user_delay(self) -> None:
        """Test user delay field."""
        payload = build_cfg_tp(user_delay=0.001)  # 1ms delay
        user_delay = struct.unpack("<f", payload[12:16])[0]
        assert abs(user_delay - 0.001) < 1e-6

    def test_roundtrip(self) -> None:
        """Test build -> parse roundtrip."""
        payload = build_cfg_tp(
            interval_us=1000000,
            width_us=100000,
            enable=1,
            polarity=0,
            time_ref=0,
            time_source=2,
            user_delay=0.0,
        )
        parsed = parse_cfg_tp(payload)
        assert parsed.interval_us == 1000000
        assert parsed.width_us == 100000
        assert parsed.enable == 1
        assert parsed.polarity == 0
        assert parsed.time_ref == 0
        assert parsed.time_source == 2
        assert parsed.user_delay == 0.0


class TestParseTimeGnssArg:
    def test_gps(self) -> None:
        """Test GPS is valid."""
        assert parse_time_gnss_arg("GPS") == GNSS.GPS

    def test_bds(self) -> None:
        """Test BDS is valid."""
        assert parse_time_gnss_arg("BDS") == GNSS.BDS

    def test_glo(self) -> None:
        """Test GLO is valid."""
        assert parse_time_gnss_arg("GLO") == GNSS.GLO

    def test_glonass_normalized(self) -> None:
        """Test GLONASS is normalized to GLO."""
        assert parse_time_gnss_arg("GLONASS") == GNSS.GLO

    def test_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert parse_time_gnss_arg("gps") == GNSS.GPS
        assert parse_time_gnss_arg("Bds") == GNSS.BDS
        assert parse_time_gnss_arg("gLo") == GNSS.GLO

    def test_whitespace_trimmed(self) -> None:
        """Test whitespace is trimmed."""
        assert parse_time_gnss_arg(" GPS ") == GNSS.GPS
        assert parse_time_gnss_arg("\tBDS\n") == GNSS.BDS

    def test_invalid_system(self) -> None:
        """Test invalid system raises ValueError."""
        with pytest.raises(ValueError, match="Unknown time source"):
            parse_time_gnss_arg("GAL")

    def test_invalid_galileo(self) -> None:
        """Test Galileo is not valid for time source."""
        with pytest.raises(ValueError, match="Unknown time source.*GAL"):
            parse_time_gnss_arg("GAL")

    def test_empty_string(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="Unknown time source"):
            parse_time_gnss_arg("")


class TestConfigChangesMarkTp:
    def test_mark_tp(self) -> None:
        """Test mark_tp sets CFG_MASK_TP bit."""
        changes = ConfigChanges()
        changes.mark_tp()
        assert changes.mask & CFG_MASK_TP != 0

    def test_mark_tp_multiple_calls(self) -> None:
        """Test mark_tp is idempotent."""
        changes = ConfigChanges()
        changes.mark_tp()
        changes.mark_tp()
        assert changes.mask == CFG_MASK_TP

    def test_mark_tp_with_other_changes(self) -> None:
        """Test mark_tp can be combined with other marks."""
        changes = ConfigChanges()
        changes.mark_nav()
        changes.mark_tp()
        assert changes.mask & CFG_MASK_TP != 0
        assert changes.mask & 0x0008 != 0  # CFG_MASK_NAV
