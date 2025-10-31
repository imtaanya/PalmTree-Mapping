"""
clip.py — Clip and mosaic Sentinel-2 stacked images to AOI

Description:
------------
This script performs the following steps:
  1. Reprojects an Area of Interest (AOI) GeoJSON to match Sentinel-2 CRS.
  2. Clips all stacked GeoTIFFs to that AOI extent.
  3. Creates a mosaic from the clipped rasters.

Configuration:
--------------
Reads parameters from `config.yaml`, including:
  - paths.aoi_path        → AOI file path (GeoJSON or Shapefile)
  - paths.output_dir      → directory with stacked GeoTIFFs
  - paths.clipped_dir     → directory to save clipped rasters
  - paths.mosaic_output   → output path for final mosaic

Outputs:
--------
  - Clipped rasters saved in the `clipped` folder.
  - A single mosaic GeoTIFF saved to `mosaic.tif`.
"""

import os
import glob
import yaml
import rasterio
from rasterio import mask
from rasterio.merge import merge
from shapely.geometry import mapping
import geopandas as gpd


# ================== CONFIG LOADER ==================
def load_config(config_path: str = "config.yaml") -> dict:
    """Load YAML configuration file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# ================== AOI REPROJECTION ==================
def reproject_aoi(aoi_path: str, reference_raster: str):
    """
    Reproject AOI to match CRS of the reference raster.

    Parameters
    ----------
    aoi_path : str
        Path to input AOI GeoJSON or Shapefile.
    reference_raster : str
        Path to a raster whose CRS is the target projection.

    Returns
    -------
    list
        List of AOI geometries in the raster’s CRS.
    """
    with rasterio.open(reference_raster) as src:
        target_crs = src.crs

    gdf = gpd.read_file(aoi_path)
    gdf = gdf.to_crs(target_crs)

    return [mapping(geom) for geom in gdf.geometry]


# ================== RASTER CLIPPING ==================
def clip_raster_to_aoi(raster_path: str, aoi_geom: list, clipped_dir: str):
    """
    Clip a single raster to the AOI extent.

    Parameters
    ----------
    raster_path : str
        Input raster file path.
    aoi_geom : list
        AOI geometry (in same CRS as raster).
    clipped_dir : str
        Output directory for clipped rasters.

    Returns
    -------
    str | None
        Path to clipped raster, or None if raster does not intersect AOI.
    """
    filename = os.path.basename(raster_path)
    out_path = os.path.join(clipped_dir, filename.replace(".tif", "_clipped.tif"))

    with rasterio.open(raster_path) as src:
        try:
            out_image, out_transform = mask.mask(src, aoi_geom, crop=True)
        except ValueError:
            # Raised if AOI and raster do not overlap
            print(f"Skipped (no intersection): {filename}")
            return None

        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        os.makedirs(clipped_dir, exist_ok=True)
        with rasterio.open(out_path, "w", **out_meta) as dest:
            dest.write(out_image)

    print(f"Clipped: {filename}")
    return out_path


# ================== MOSAIC CREATION ==================
def create_mosaic(clipped_files: list, output_path: str):
    """
    Merge multiple clipped rasters into one mosaic.

    Parameters
    ----------
    clipped_files : list
        List of file paths to clipped rasters.
    output_path : str
        Output mosaic file path.
    """
    if not clipped_files:
        print("No clipped files found — mosaic skipped.")
        return

    src_files = [rasterio.open(fp) for fp in clipped_files]
    mosaic, out_trans = merge(src_files)

    out_meta = src_files[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans
    })

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    for src in src_files:
        src.close()

    print(f"Mosaic created: {output_path}")


# ================== MAIN PIPELINE ==================
def main():
    """Main entry point for clipping and mosaicking."""
    config = load_config("config.yaml")

    aoi_path = config["paths"]["aoi_path"]
    input_dir = config["paths"]["output_dir"]
    clipped_dir = config["paths"].get("clipped_dir", "clipped")
    mosaic_output = config["paths"].get("mosaic_output", "mosaic.tif")

    # Collect stacked TIFFs
    tiff_files = glob.glob(os.path.join(input_dir, "*.tif"))
    if not tiff_files:
        print(f"No TIFF files found in input directory: {input_dir}")
        return

    # Reproject AOI
    aoi_geom = reproject_aoi(aoi_path, tiff_files[0])

    # Clip each raster
    clipped_files = []
    for tif in tiff_files:
        result = clip_raster_to_aoi(tif, aoi_geom, clipped_dir)
        if result:
            clipped_files.append(result)

    # Create mosaic
    if clipped_files:
        create_mosaic(clipped_files, mosaic_output)
        print("Processing complete.")
    else:
        print("No valid rasters clipped — mosaic not created.")


if __name__ == "__main__":
    main()
