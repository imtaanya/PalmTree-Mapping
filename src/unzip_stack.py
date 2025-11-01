
"""
unzip_stack.py — Sentinel-2 L2A extraction and band stacking utility

Description:
------------
This script automates the process of:
  1. Unzipping Sentinel-2 L2A .zip archives.
  2. Extracting specified 10 m resolution bands (e.g., B02, B03, B04, B08).
  3. Stacking them into a single GeoTIFF file.

Outputs:
--------
Each processed ZIP will produce one stacked GeoTIFF file in the output directory.
"""

import os
import glob
import zipfile
import yaml
import rasterio
from rasterio import open as rio_open
import shutil


# ================== CONFIG LOADER ==================
def load_config(config_path: str = "config.yaml") -> dict:
    """Load parameters from YAML configuration file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# ================== BAND LOCATOR ==================
def find_bands(folder: str, bands: list) -> list:
    """
    Locate 10 m JP2 band files within the unzipped Sentinel-2 directory.

    Parameters
    ----------
    folder : str
        Path to unzipped Sentinel-2 product directory.
    bands : list
        List of band IDs to search for (e.g., ["B02", "B03", "B04", "B08"]).

    Returns
    -------
    list
        Ordered list of JP2 file paths matching requested bands.
    """
    found = {b: None for b in bands}

    for root, _, files in os.walk(folder):
        root_up = root.upper()
        for f in files:
            if not f.lower().endswith(".jp2"):
                continue
            fname_up = f.upper()
            for b in bands:
                # Sentinel-2 stores 10 m resolution bands under R10m folder
                if b in fname_up and ("R10M" in root_up or "10M" in fname_up):
                    if found[b] is None:
                        found[b] = os.path.join(root, f)

    # Check if all required bands were found
    missing = [b for b, path in found.items() if path is None]
    if missing:
        raise FileNotFoundError(f"Missing bands in {folder}: {missing}")

    return [found[b] for b in bands]


# ================== STACKING FUNCTION ==================
def stack_bands(jp2_files: list, output_tif: str):
    """
    Stack multiple JP2 band rasters into a single GeoTIFF.

    Parameters
    ----------
    jp2_files : list
        List of band JP2 file paths.
    output_tif : str
        Output file path for stacked GeoTIFF.
    """
    srcs = [rio_open(fp) for fp in jp2_files]

    # Use the first band as spatial reference
    ref = srcs[0]
    height, width = ref.height, ref.width
    crs = ref.crs
    transform = ref.transform

    arrays = [s.read(1) for s in srcs]

    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": len(arrays),
        "crs": crs,
        "transform": transform,
        "dtype": rasterio.uint16,
        "compress": "lzw"
    }

    os.makedirs(os.path.dirname(output_tif), exist_ok=True)

    with rio_open(output_tif, "w", **meta) as dst:
        for i, arr in enumerate(arrays, start=1):
            dst.write(arr.astype(rasterio.uint16), i)

    for s in srcs:
        s.close()

    print(f"Stacked {len(arrays)} bands → {output_tif}")


# ================== ZIP EXTRACTION ==================
def unzip_file(zip_path: str, extract_dir: str):
    """Extract all contents from a Sentinel-2 ZIP archive."""
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)


# ================== MAIN PIPELINE ==================
def main():
    config = load_config("config.yaml")
    downloads_dir = config["paths"]["downloads_dir"]
    output_dir = config["paths"]["output_dir"]
    bands = config["bands"]

    os.makedirs(output_dir, exist_ok=True)
    zip_files = glob.glob(os.path.join(downloads_dir, "*.zip"))

    if not zip_files:
        print(f"No Sentinel-2 ZIP files found in: {downloads_dir}")
        return

    for idx, zip_path in enumerate(zip_files, start=1):
        print(f"\nProcessing {os.path.basename(zip_path)} ...")
        temp_dir = os.path.join(output_dir, f"temp_{idx}")
        os.makedirs(temp_dir, exist_ok=True)

        unzip_file(zip_path, temp_dir)

        try:
            jp2_files = find_bands(temp_dir, bands)
            output_tif = os.path.join(output_dir, f"image_stack_{idx}.tif")
            stack_bands(jp2_files, output_tif)
        except FileNotFoundError as e:
            print(f"Error: {e}")
        finally:
            # Clean up extracted data
            shutil.rmtree(temp_dir, ignore_errors=True)

    print("\nAll Sentinel-2 archives processed successfully.")


if __name__ == "__main__":
    main()
