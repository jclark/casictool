# CFG-NAVX Parameter Mask

## Problem

The current `build_cfg_navx()` uses read-modify-write with `mask=0xFFFFFFFF`, but CFG-NAVX has a parameter mask that controls which fields get applied. We can set only the specific mask bits for fields we're changing, eliminating the need to query first.

## NAVX Mask Constants (casic.py)

Add all mask bit constants:

```python
# CFG-NAVX parameter mask bits
NAVX_MASK_DYN_MODEL = 0x0001    # B0: Apply dynamic model setting
NAVX_MASK_FIX_MODE = 0x0002     # B1: Apply fix mode setting
NAVX_MASK_SV_COUNT = 0x0004     # B2: Apply min/max satellite count
NAVX_MASK_MIN_CNO = 0x0008      # B3: Apply min CNO setting
# B4 reserved
NAVX_MASK_INI_FIX_3D = 0x0020   # B5: Apply initial 3D fix setting
NAVX_MASK_MIN_ELEV = 0x0040     # B6: Apply min elevation setting
NAVX_MASK_DR_LIMIT = 0x0080     # B7: Apply DR limit setting
NAVX_MASK_NAV_SYSTEM = 0x0100   # B8: Apply navigation system enable
NAVX_MASK_WN_ROLLOVER = 0x0200  # B9: Apply GPS week rollover setting
NAVX_MASK_ALT_ASSIST = 0x0400   # B10: Apply altitude assist
NAVX_MASK_P_DOP = 0x0800        # B11: Apply position DOP limit
NAVX_MASK_T_DOP = 0x1000        # B12: Apply time DOP limit
NAVX_MASK_STATIC_HOLD = 0x2000  # B13: Apply static hold setting
```

## Updated build_cfg_navx() Signature

```python
def build_cfg_navx(
    nav_system: int | None = None,
    min_elev: int | None = None,
) -> bytes:
    """Build CFG-NAVX payload with targeted mask bits.

    Only fields with non-None values are applied; others are ignored
    by the receiver based on the mask.

    Args:
        nav_system: Constellation mask (B0=GPS, B1=BDS, B2=GLO)
        min_elev: Minimum satellite elevation in degrees

    Returns:
        44-byte CFG-NAVX payload
    """
    mask = 0
    if nav_system is not None:
        mask |= NAVX_MASK_NAV_SYSTEM
    if min_elev is not None:
        mask |= NAVX_MASK_MIN_ELEV

    return struct.pack(
        "<IBBBBBBbbbBHfffffff",
        mask,
        0,  # dyn_model
        0,  # fix_mode
        0,  # min_svs
        0,  # max_svs
        0,  # min_cno
        0,  # res1
        0,  # ini_fix_3d
        min_elev or 0,
        0,  # dr_limit
        nav_system or 0,
        0,  # wn_rollover
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    )
```

## job.py Changes

Remove query step from `set_gnss()` and `set_min_elev()`:

```python
def set_gnss(conn: CasicConnection, nav_system: int, changes: ConfigChanges) -> bool:
    payload = build_cfg_navx(nav_system=nav_system)
    if not conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload):
        return False
    changes.mark_navx()
    return True

def set_min_elev(conn: CasicConnection, min_elev: int, changes: ConfigChanges) -> bool:
    payload = build_cfg_navx(min_elev=min_elev)
    if not conn.send_and_wait_ack(CFG_NAVX.cls, CFG_NAVX.id, payload):
        return False
    changes.mark_navx()
    return True
```

## Test Updates

Update tests to use new signature (no config parameter required).

## Benefits

- Simpler code (no query step needed)
- Faster execution (one round-trip instead of two)
- Clearer intent (explicit about which fields are being set)
- Extensible (easy to add more NAVX options using existing mask constants)
