"""
polygonize_indices.py
Create polygonized vector layers for NDVI, GNDVI, EVI2 ranges and combined intersection.
Saves vectors in GPKG and computes area in hectares.
"""

import os
import yaml
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
import geopandas as gpd
from scipy import ndimage as ndi
from pyproj import CRS


def load_config(config_path="config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def read_raster(path):
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        meta = src.meta.copy()
    return arr, meta


def disk(radius):
    L = 2 * radius + 1
    y, x = np.ogrid[:L, :L]
    return ((x - radius)**2 + (y - radius)**2 <= radius**2).astype(np.uint8)


def binary_morphology(mask, open_radius=1, close_radius=1):
    out = mask.copy().astype(np.uint8)
    if open_radius > 0:
        out = ndi.binary_opening(out, structure=disk(open_radius))
    if close_radius > 0:
        out = ndi.binary_closing(out, structure=disk(close_radius))
    return out


def raster_to_polygons(mask, meta):
    transform = meta["transform"]
    geoms = [shape(g) for g, v in shapes(mask.astype(np.uint8), mask=mask.astype(bool), transform=transform) if v == 1]
    if not geoms:
        return gpd.GeoDataFrame(columns=["geometry"], crs=meta.get("crs"))
    return gpd.GeoDataFrame({"geometry": geoms}, crs=meta.get("crs"))


def compute_area_ha(gdf):
    if gdf.empty:
        gdf["area_ha"] = []
        return gdf
    crs = gdf.crs
    if CRS(crs).is_geographic:
        gdf_proj = gdf.to_crs(gdf.estimate_utm_crs())
    else:
        gdf_proj = gdf
    gdf["area_ha"] = gdf_proj.geometry.area / 10000.0
    return gdf


def process_index_to_vectors(name, arr, meta, val_range, proc, out_dir, fmt="GPKG"):
    mask = (arr >= val_range[0]) & (arr <= val_range[1])
    mask = binary_morphology(mask, proc["morph_open_radius"], proc["morph_close_radius"])

    labeled, n = ndi.label(mask)
    pixel_area_m2 = abs(meta["transform"].a) * abs(meta["transform"].e)
    min_pixels = int((proc["min_area_ha"] * 10000) / pixel_area_m2)

    clean = np.zeros_like(mask, dtype=np.uint8)
    for i in range(1, n + 1):
        region = (labeled == i)
        if region.sum() >= min_pixels:
            clean[region] = 1

    gdf = raster_to_polygons(clean, meta)
    gdf = compute_area_ha(gdf)
    gdf = gdf[(gdf["area_ha"] >= proc["min_area_ha"]) & (gdf["area_ha"] <= proc["max_area_ha"])].copy()

    if gdf.empty:
        return None

    os.makedirs(out_dir, exist_ok=True)
    out_name = f"{name}_polygons.gpkg" if fmt == "GPKG" else f"{name}_polygons.shp"
    out_path = os.path.join(out_dir, out_name)
    driver = "GPKG" if fmt == "GPKG" else "ESRI Shapefile"
    gdf.to_file(out_path, driver=driver)
    return out_path, gdf


def run(config_path="config.yaml"):
    cfg = load_config(config_path)
    ndvi_path = cfg["paths"].get("ndvi") or os.path.join(cfg["paths"]["output_dir"], "indices", "NDVI.tif")
    gndvi_path = cfg["paths"].get("gndvi") or os.path.join(cfg["paths"]["output_dir"],  "indices", "GNDVI.tif")
    evi2_path = cfg["paths"].get("evi2") or os.path.join(cfg["paths"]["output_dir"], "indices", "EVI2.tif")

    proc = cfg["processing"]
    outdir = os.path.join(cfg["paths"]["output_dir"], "polygons")
    fmt = cfg["output"].get("vector_format", "GPKG").upper()

    ndvi, meta = read_raster(ndvi_path)
    gndvi, _ = read_raster(gndvi_path)
    evi2, _ = read_raster(evi2_path)

    results = {}
    ndvi_res = process_index_to_vectors("NDVI", ndvi, meta, proc["ndvi_range"], proc, outdir, fmt)
    if ndvi_res:
        results["NDVI"] = ndvi_res[0]

    gndvi_res = process_index_to_vectors("GNDVI", gndvi, meta, proc["gndvi_range"], proc, outdir, fmt)
    if gndvi_res:
        results["GNDVI"] = gndvi_res[0]

    evi2_res = process_index_to_vectors("EVI2", evi2, meta, proc["evi2_range"], proc, outdir, fmt)
    if evi2_res:
        results["EVI2"] = evi2_res[0]

    # Combined intersection
    combined = ((ndvi >= proc["ndvi_range"][0]) & (ndvi <= proc["ndvi_range"][1]) &
                (gndvi >= proc["gndvi_range"][0]) & (gndvi <= proc["gndvi_range"][1]) &
                (evi2 >= proc["evi2_range"][0]) & (evi2 <= proc["evi2_range"][1])).astype(np.uint8)
    combined = binary_morphology(combined, proc["morph_open_radius"], proc["morph_close_radius"])

    labeled, n = ndi.label(combined)
    pixel_area_m2 = abs(meta["transform"].a) * abs(meta["transform"].e)
    min_pixels = int((proc["min_area_ha"] * 10000) / pixel_area_m2)
    final_mask = np.zeros_like(combined, dtype=np.uint8)
    for i in range(1, n + 1):
        region = (labeled == i)
        if region.sum() >= min_pixels:
            final_mask[region] = 1

    palm_gdf = raster_to_polygons(final_mask, meta)
    palm_gdf = compute_area_ha(palm_gdf)
    palm_gdf = palm_gdf[(palm_gdf["area_ha"] >= proc["min_area_ha"]) & (palm_gdf["area_ha"] <= proc["max_area_ha"])].copy()

    if palm_gdf.empty:
        return results

    os.makedirs(outdir, exist_ok=True)
    palm_name = "Palm_Combined.gpkg" if fmt == "GPKG" else "Palm_Combined.shp"
    palm_path = os.path.join(outdir, palm_name)
    driver = "GPKG" if fmt == "GPKG" else "ESRI Shapefile"
    palm_gdf.to_file(palm_path, driver=driver)
    results["Palm_Combined"] = palm_path
    return results
if __name__ == "__main__":
    run()