#!/usr/bin/env python3
import argparse
from os import fspath
from pathlib import Path
from typing import List, Optional, Union

import isce3
import numpy as np
from osgeo import gdal
from shapely.geometry import MultiPolygon, Point

import s1reader

def _get_height_from_dem(lon: float, lat: float, dem_file: str):
    """Get the height of the nearest pixel to (lon, lat) in the DEM file."""
    ds = gdal.Open(fspath(dem_file))
    gt = ds.GetGeoTransform()
    px = int((lon - gt[0]) / gt[1])  # x pixel
    py = int((lat - gt[3]) / gt[5])  # y pixel
    band = ds.GetRasterBand(1)
    return band.ReadAsArray(px, py, 1, 1).item()


def s1geo2rdr(lon: float, lat: float, h: float, burst: s1reader.Sentinel1BurstSlc):
    llh_rad = np.array([*np.radians([lon, lat]), h]).reshape((3, 1))
    return isce3.geometry.geo2rdr(
        llh_rad,
        orbit=burst.orbit,
        doppler=isce3.core.LUT2d(),  # Using zero Doppler
        wavelength=burst.wavelength,
        side=isce3.core.LookSide.Right,
    )


def get_cli_parser():
    parser = argparse.ArgumentParser(
        description="Converts a point in lon/lat to azimuth time and range"
    )
    parser.add_argument("lon", type=float, help="longitude of point")
    parser.add_argument("lat", type=float, help="latitude of point")
    parser.add_argument("s1_file", type=Path, help="Sentinel-1 zip/SAFE file")
    parser.add_argument(
        "--orbit-dir",
        type=Path,
        help="Directory containing the orbit files",
    )

    parser.add_argument(
        "-d", "--dem", type=Path, help="DEM file (optional, for height)"
    )
    parser.add_argument(
        "--height", type=float, help="optional: manually specify height"
    )

    parser.add_argument(
        "-p",
        "--pol",
        default="vv",
        choices=["vv", "vh", "hh", "hv"],
        help="Polarization to use.",
    )
    parser.add_argument(
        "-i",
        "--iw",
        type=int,
        choices=[1, 2, 3],
        help="Print only the burst IDs for the given IW.",
    )
    parser.add_argument(
        "-b",
        "--burst-id",
        help="Specific burst_id to use within the zip file",
    )

    # Make an output GTiff of the buffer around the point
    parser.add_argument(
        "--outfile",
        type=Path,
        help="Output file for the buffer around the point",
    )
    parser.add_argument(
        "--buffer",
        type=int,
        default=100,
        help="Buffer (in pixels) around the point to output",
    )

    return parser


def _get_overlapping_bursts(
    *,
    s1_file: str,
    lon: float,
    lat: float,
    orbit_dir: Optional[Path] = None,
    pol: str = "vv",
):
    """Get the burst IDs that overlap with the given lon/lat point."""
    if orbit_dir is not None:
        orb_file = s1reader.get_orbit_file_from_dir(s1_file, orbit_dir=orbit_dir)
    else:
        orb_file = None

    bursts = []
    for iw in range(1, 4):
        for burst in s1reader.load_bursts(
            s1_file, orb_file, iw, pol, flag_apply_eap=False
        ):
            if MultiPolygon(burst.border).contains(Point(lon, lat)):
                bursts.append(burst)
    return bursts


def main():
    parser = get_cli_parser()
    args = parser.parse_args()

    lon, lat = args.lon, args.lat
    dem_file = args.dem

    if args.height is not None:
        h = args.height
    elif dem_file is not None:
        h = _get_height_from_dem(lon, lat, dem_file)
    else:
        raise ValueError("Must specify either --height or --dem")

    # print out like a CSV: lon,lat,az_idx,range_idx,burst_id,tiff_path
    print("lon,lat,az_idx,range_idx,burst_id,tiff_path")
    for burst in _get_overlapping_bursts(
        s1_file=args.s1_file, lon=lon, lat=lat, pol=args.pol, orbit_dir=args.orbit_dir
    ):
        if args.burst_id is not None and args.burst_id != burst.burst_id:
            continue
        if args.iw is not None and args.iw != burst.iw:
            continue

        rg = burst.as_isce3_radargrid()

        az_time, range = s1geo2rdr(lon, lat, h, burst)
        az_idx = round((az_time - rg.sensing_start) / rg.az_time_interval)
        range_idx = round((range - rg.starting_range) / rg.range_pixel_spacing)

        # print(f"burst: {burst.burst_id} at {burst.tiff_path}, az_idx: {az_idx}, range_idx: {range_idx}")
        print(f"{lon},{lat},{az_idx},{range_idx},{burst.burst_id},{burst.tiff_path}")

        if args.outfile is not None:
            buf = args.buffer
            rows = slice(az_idx - buf, az_idx + buf + 1)
            cols = slice(range_idx - buf, range_idx + buf + 1)


if __name__ == "__main__":
    main()
