"""Tests for Sentinel-1 stripmap mode support"""

from datetime import datetime
from pathlib import Path

import s1reader

DATA_DIR = Path(__file__).parent / "data"


def test_load_stripmap_s1c():
    """Test loading S1C stripmap S3 mode data"""
    safe_path = (
        DATA_DIR
        / "S1C_S3_SLC__1SDV_20250809T044136_20250809T044157_003591_007305_E501.SAFE"
    )

    orbit_path = (
        DATA_DIR
        / "S1C_OPER_AUX_POEORB_OPOD_20250829T070946_V20250808T225942_20250810T005942.EOF"
    )

    # Load stripmap data (S3 beam = swath 3)
    bursts = s1reader.load_bursts(safe_path, orbit_path, swath_num=3, pol="vv")

    # Stripmap should return a single "burst" object representing entire swath
    assert len(bursts) == 1

    burst = bursts[0]

    # Check basic metadata
    assert burst.polarization == "VV"
    assert burst.platform_id == "S1C"

    # Check that dimensions are correct (from imageInformation)
    assert burst.shape == (39169, 19118)

    # For stripmap, burst_id should be None (no ESA burst ID scheme)
    assert burst.burst_id is None

    # Check that geometry was calculated
    assert burst.center is not None
    assert burst.border is not None

    # Check that orbit was loaded
    assert burst.orbit is not None

    print(f"  Sensing start: {burst.sensing_start}")
    assert burst.center.x == -157.1537150259895
    assert burst.center.y == 1.9785111829891613
    assert burst.shape == (39169, 19118)
    assert burst.sensing_start == datetime.fromisoformat("2025-08-09T04:41:36.791272")


def test_load_stripmap_s1b():
    """Test loading S1B stripmap S3 mode data"""
    safe_path = (
        DATA_DIR
        / "S1B_S3_SLC__1SDV_20170710T044132_20170710T044156_006421_00B498_815E.SAFE"
    )

    orbit_path = (
        DATA_DIR
        / "S1B_OPER_AUX_POEORB_OPOD_20210308T154835_V20170709T225942_20170711T005942.EOF"
    )

    # Load stripmap data
    bursts = s1reader.load_bursts(safe_path, orbit_path, swath_num=3, pol="vv")

    # Stripmap should return a single object
    assert len(bursts) == 1

    burst = bursts[0]

    # Check basic metadata
    assert burst.polarization == "VV"
    assert burst.platform_id == "S1B"

    # Check that geometry was calculated
    assert burst.center is not None
    assert burst.border is not None

    # Check orbit
    assert burst.orbit is not None

    assert burst.center.x == -157.17638961512185
    assert burst.center.y == 2.0873675822728304
    assert burst.shape == (45658, 19118)


def test_stripmap_both_pols():
    """Test loading both polarizations for stripmap"""
    safe_path = (
        DATA_DIR
        / "S1C_S3_SLC__1SDV_20250809T044136_20250809T044157_003591_007305_E501.SAFE"
    )

    orbit_path = (
        DATA_DIR
        / "S1C_OPER_AUX_POEORB_OPOD_20250829T070946_V20250808T225942_20250810T005942.EOF"
    )

    # Load VV
    bursts_vv = s1reader.load_bursts(safe_path, orbit_path, swath_num=3, pol="vv")
    assert len(bursts_vv) == 1
    assert bursts_vv[0].polarization == "VV"

    # Load VH
    bursts_vh = s1reader.load_bursts(safe_path, orbit_path, swath_num=3, pol="vh")
    assert len(bursts_vh) == 1
    assert bursts_vh[0].polarization == "VH"


if __name__ == "__main__":
    print("Testing S1 stripmap support...")
    print()

    try:
        test_load_stripmap_s1c()
        print()
        test_load_stripmap_s1b()
        print()
        test_stripmap_both_pols()
        print()
        print("=" * 50)
        print("All stripmap tests passed! ✓")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
