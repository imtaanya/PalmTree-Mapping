#!/usr/bin/env python3
"""
Master pipeline runner for Palm Plantation Detection
Executes all modules in sequence:
1. Unzip + stack Sentinel-2 bands
2. Clip rasters to AOI
3. Compute vegetation indices
4. Polygonize palm plantation areas
"""

from src.unzip_stack import main as unzip_run
from src.clip_aoi import main as clip_run
from src.compute_indices import main as indices_run
from src.polygonize_indices import run as poly_run
from src.generate_report import generate_report


def main():
    #print(" Step 1: Unzipping and stacking Sentinel-2 bands...")
    #unzip_run()

    print("\n Step 2: Clipping rasters to AOI...")
    clip_run()

    print("\n  Step 3: Calculating vegetation indices (NDVI, GNDVI, EVI2)...")
    indices_run()

    print("\n Step 4: Polygonizing plantation areas...")
    poly_run()

    print("\n Step 5: Generate report....")
    generate_report("config.yaml", "outputs")

    print("\n  Pipeline completed successfully!")


if __name__ == "__main__":
    main()
