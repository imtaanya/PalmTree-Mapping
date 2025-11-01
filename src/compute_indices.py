
"""
indices.py — Calculate NDVI, GNDVI, and EVI2 from Sentinel-2 stacked imagery

Description:
------------
This script computes three vegetation indices (NDVI, GNDVI, and EVI2) from a
stacked Sentinel-2 raster (bands: B02, B03, B04, B08).

It saves each index as an individual GeoTIFF file in the configured output
directory.


Outputs:
--------
  - NDVI.tif
  - GNDVI.tif
  - EVI2.tif
"""

import os
import yaml
import rasterio
import numpy as np


# =================== CONFIG LOADER ===================
def load_config(config_path: str = "config.yaml") -> dict:
    """Load YAML configuration file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# =================== INDEX CALCULATOR ===================
def calculate_indices(input_tif: str, output_dir: str):
    """
    Compute NDVI, GNDVI, and EVI2 from stacked Sentinel-2 imagery.

    Parameters
    ----------
    input_tif : str
        Path to input raster (stacked or mosaicked image containing B02, B03, B04, B08).
    output_dir : str
        Directory to save the resulting index rasters.
    """
    os.makedirs(output_dir, exist_ok=True)

    with rasterio.open(input_tif) as src:
        # Read spectral bands
        blue = src.read(1).astype("float32")   # B02
        green = src.read(2).astype("float32")  # B03
        red = src.read(3).astype("float32")    # B04
        nir = src.read(4).astype("float32")    # B08

        np.seterr(divide="ignore", invalid="ignore")

        # ========== NDVI ==========
        ndvi = (nir - red) / (nir + red)
        ndvi = np.clip(ndvi, -1, 1)

        # ========== GNDVI ==========
        gndvi = (nir - green) / (nir + green)
        gndvi = np.clip(gndvi, -1, 1)

        # ========== EVI2 ==========
        evi2 = 2.5 * (nir - red) / (nir + 2.4 * red + 1)
        evi2 = np.clip(evi2, -1, 1)

        # ========== Save Outputs ==========
        meta = src.meta.copy()
        meta.update(driver="GTiff", dtype=rasterio.float32, count=1, compress="lzw")

        def save_raster(array: np.ndarray, name: str):
            """Write index array to GeoTIFF."""
            out_path = os.path.join(output_dir, f"{name}.tif")
            with rasterio.open(out_path, "w", **meta) as dst:
                dst.write(array, 1)
            print(f"Saved {name}: {out_path}")

        save_raster(ndvi, "NDVI")
        save_raster(gndvi, "GNDVI")
        save_raster(evi2, "EVI2")


# =================== MAIN ===================
def main():
    """Main entry point for vegetation index generation."""
    config = load_config("config.yaml")

    input_tif = config["paths"].get("mosaic_output", "mosaic.tif")
    output_dir = os.path.join(config["paths"]["output_dir"], "indices")

    calculate_indices(input_tif, output_dir)
    print("Vegetation indices successfully generated.")


if __name__ == "__main__":
    main()
