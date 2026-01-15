"""Tests for Phase 6: Timing mode configuration."""

import struct

import pytest

from casic import build_cfg_tmode


class TestBuildCfgTmode:
    def test_auto_mode(self) -> None:
        """Mode 0 (auto) sets all position fields to zero."""
        payload = build_cfg_tmode(mode=0)
        assert len(payload) == 40
        (mode,) = struct.unpack("<I", payload[:4])
        assert mode == 0

    def test_survey_mode(self) -> None:
        """Mode 1 (survey) sets duration and variance limit."""
        payload = build_cfg_tmode(
            mode=1,
            survey_min_dur=3600,
            survey_acc=10.0,
        )
        assert len(payload) == 40
        mode, _, _, _, _, svin_dur, svin_var = struct.unpack("<IdddfIf", payload)
        assert mode == 1
        assert svin_dur == 3600
        assert svin_var == pytest.approx(100.0)  # 10^2

    def test_fixed_mode(self) -> None:
        """Mode 2 (fixed) sets ECEF coordinates and variance."""
        payload = build_cfg_tmode(
            mode=2,
            fixed_pos=(4000000.0, 1000000.0, 5000000.0),
            fixed_pos_acc=0.5,
        )
        assert len(payload) == 40
        mode, x, y, z, var, _, _ = struct.unpack("<IdddfIf", payload)
        assert mode == 2
        assert x == pytest.approx(4000000.0)
        assert y == pytest.approx(1000000.0)
        assert z == pytest.approx(5000000.0)
        assert var == pytest.approx(0.25)  # 0.5^2

    def test_default_values(self) -> None:
        """Default values are applied when not specified."""
        payload = build_cfg_tmode(mode=1)
        mode, _, _, _, pos_var, svin_dur, svin_var = struct.unpack("<IdddfIf", payload)
        assert mode == 1
        assert pos_var == pytest.approx(1.0)  # default fixed_pos_acc=1.0 -> 1.0^2
        assert svin_dur == 2000  # default survey_min_dur
        assert svin_var == pytest.approx(400.0)  # default survey_acc=20.0 -> 20.0^2


class TestParseEcefCoords:
    def test_valid_coords(self) -> None:
        from casictool import parse_ecef_coords

        result = parse_ecef_coords("4000000,1000000,5000000")
        assert result == (4000000.0, 1000000.0, 5000000.0)

    def test_with_spaces(self) -> None:
        from casictool import parse_ecef_coords

        result = parse_ecef_coords("4000000, 1000000, 5000000")
        assert result == (4000000.0, 1000000.0, 5000000.0)

    def test_negative_coords(self) -> None:
        from casictool import parse_ecef_coords

        result = parse_ecef_coords("-1144698.0455,6090335.4099,1504171.3914")
        assert result[0] == pytest.approx(-1144698.0455)
        assert result[1] == pytest.approx(6090335.4099)
        assert result[2] == pytest.approx(1504171.3914)

    def test_invalid_count_too_few(self) -> None:
        from casictool import parse_ecef_coords

        with pytest.raises(ValueError, match="3 values"):
            parse_ecef_coords("4000000,1000000")

    def test_invalid_count_too_many(self) -> None:
        from casictool import parse_ecef_coords

        with pytest.raises(ValueError, match="3 values"):
            parse_ecef_coords("4000000,1000000,5000000,6000000")

    def test_invalid_number(self) -> None:
        from casictool import parse_ecef_coords

        with pytest.raises(ValueError):
            parse_ecef_coords("4000000,abc,5000000")
