#!/usr/bin/env python3
"""
Generates a concise processing report summarizing
inputs, key parameters, intermediate outputs, and results.
"""

import os
import yaml
import datetime
import glob
import geopandas as gpd
import rasterio

def load_config(config_path="config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def summarize_raster(raster_path):
    try:
        with rasterio.open(raster_path) as src:
            crs = src.crs
            res = src.res
            bounds = src.bounds
            return {
                "CRS": str(crs),
                "Resolution": res,
                "Extent": [round(bounds.left,2), round(bounds.bottom,2),
                           round(bounds.right,2), round(bounds.top,2)]
            }
    except Exception as e:
        return {"Error": str(e)}

def summarize_vector(vector_path):
    try:
        gdf = gpd.read_file(vector_path)
        total_area = gdf["area_ha"].sum() if "area_ha" in gdf.columns else None
        return {
            "Features": len(gdf),
            "Total Area (ha)": round(total_area, 2) if total_area else "N/A",
            "CRS": str(gdf.crs)
        }
    except Exception as e:
        return {"Error": str(e)}

def generate_report(config_path="config.yaml", output_dir="outputs"):
    cfg = load_config(config_path)
    report_lines = []

    # --- Header ---
    report_lines.append("Palm Plantation Detection Report")
    report_lines.append("=" * 45)
    report_lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # --- Inputs ---
    report_lines.append("INPUT SETTINGS")
    report_lines.append("-" * 20)
    report_lines.append(f"AOI: {cfg['paths'].get('aoi_path')}")
    report_lines.append(f"Bands used: {', '.join(cfg['bands'])}")
    report_lines.append(f"Date Range: {cfg['imagery']['start_date']} → {cfg['imagery']['end_date']}")
    report_lines.append("")

    # --- Processed Rasters ---
    report_lines.append("RASTER SUMMARY")
    report_lines.append("-" * 20)
    for name in ["NDVI", "GNDVI", "EVI2"]:
        path = os.path.join(output_dir, "indices", f"{name}.tif")
        if os.path.exists(path):
            info = summarize_raster(path)
            report_lines.append(f"{name}.tif → {info}")
    report_lines.append("")

    # --- Vector outputs ---
    report_lines.append("VECTOR SUMMARY")
    report_lines.append("-" * 20)
    palms_dir = os.path.join(output_dir, "palms")
    if os.path.exists(palms_dir):
        for f in glob.glob(os.path.join(palms_dir, "*.gpkg")):
            info = summarize_vector(f)
            report_lines.append(f"{os.path.basename(f)} → {info}")
    report_lines.append("")

    # --- Processing Parameters ---
    proc = cfg["processing"]
    report_lines.append("PROCESSING PARAMETERS")
    report_lines.append("-" * 20)
    for k, v in proc.items():
        report_lines.append(f"{k}: {v}")
    report_lines.append("")

    # --- Save report ---
    log_dir = os.path.join(output_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    report_path = os.path.join(log_dir, "report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f" Report generated --> {report_path}")
    return report_path

if __name__ == "__main__":
    generate_report()
