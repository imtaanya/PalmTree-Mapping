# Palm Tree Mapping Pipeline
## Overview

This project automates the process of detecting and mapping palm plantations using Sentinel-2 imagery.
The workflow covers data download, preprocessing, vegetation index computation, filtering, and polygon extraction into a reproducible end-to-end pipeline.

# Methodology

1. Use Sentinel-2 L2A (Bottom of Atmosphere reflectance) imagery for analysis.

2. Download scenes with cloud cover below 1%.

3. Compute NDVI, GNDVI, and EVI2 indices.

4. Apply fixed value thresholds to isolate palm vegetation.

5. Use morphological filters to remove noise and small patches.

6. Convert raster masks to polygons and calculate area in hectares.

7. Export final palm polygons and generate a summary report.

# Data Sources and Licenses

   1. Sentinel-2 L2A – Copernicus Open Data License

   2. AOI (GeoJSON) – User-provided Area of Interest
# Run
python run_pipeline.py

# Expected Outputs

   outputs/indices/ --> NDVI, GNDVI, EVI2 rasters

   outputs/polygons/ --> Palm polygons (GeoPackage)

   outputs/logs/ --> Processing summary report

   Each polygon includes:

   Geometry in EPSG:32644 (UTM Zone 44N)

   Calculated area in hectares (area_ha)

# Assumptions and Limitations

   Sentinel-2 L2A is used for BOA reflectance and minimal cloud interference.

   Threshold values for indices may vary depending on the region.

   Dense or mixed vegetation areas may cause overestimation.

   