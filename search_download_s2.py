import requests
import os
import yaml
import geopandas as gpd
from pathlib import Path

# ===================== CONFIG & AUTH =====================

CDSE_BASE = "https://catalogue.dataspace.copernicus.eu/odata/v1"
ZIP_BASE = "https://zipper.dataspace.copernicus.eu/odata/v1/Products"


def load_config(config_path="config.yaml"):
    """Load configuration parameters from a YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_aoi(aoi_path):
    """Load AOI geometry from GeoJSON and return as WKT string."""
    gdf = gpd.read_file(aoi_path)
    return gdf.geometry.iloc[0].wkt


def authenticate(username, password):
    """Authenticate with Copernicus Data Space Ecosystem and return an access token."""
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    data = {
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    print(" Authenticating to Copernicus Data Space...")
    r = requests.post(url, data=data)
    r.raise_for_status()
    token = r.json()["access_token"]
    print(" Authentication successful.")
    return token


# ===================== SEARCH PRODUCTS =====================

def search_products(config, wkt_str, token):
    """Search Sentinel-2 products for given AOI, date range, and cloud threshold."""
    start_date = config["imagery"]["start_date"]
    end_date = config["imagery"]["end_date"]
    max_cloud = config["imagery"]["max_cloud_cover"]

    query = (
        f"{CDSE_BASE}/Products?"
        f"$filter=Collection/Name eq 'SENTINEL-2' and "
        f"ContentDate/Start gt {start_date}T00:00:00.000Z and "
        f"ContentDate/Start lt {end_date}T23:59:59.999Z and "
        f"Attributes/OData.CSC.DoubleAttribute/any(a:a/Name eq 'cloudCover' "
        f"and a/OData.CSC.DoubleAttribute/Value lt {max_cloud}) and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt_str}')"
        f"&$orderby=ContentDate/Start desc&$top=10"
    )

    headers = {"Authorization": f"Bearer {token}"}
    print(" Searching Sentinel-2 imagery ...")
    resp = requests.get(query, headers=headers)
    resp.raise_for_status()
    return resp.json().get("value", [])


# ===================== DOWNLOAD ZIP =====================

def download_product_zip(product_id, product_name, token, output_dir="downloads"):
    """Download Sentinel-2 product ZIP into the output directory."""
    os.makedirs(output_dir, exist_ok=True)

    url = f"{ZIP_BASE}({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}
    zip_path = os.path.join(output_dir, f"{product_name}.zip")

    print(f"⬇  Downloading {product_name} ...")
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)

    print(f" Downloaded: {zip_path}")
    return zip_path


# ===================== MAIN =====================

def main():
    """Authenticate, search Sentinel-2 imagery, and download selected ZIPs."""
    config = load_config()

    username = config["cdse"]["username"]
    password = config["cdse"]["password"]
    aoi_path = config["paths"]["aoi_path"]

    wkt_str = load_aoi(aoi_path)
    token = authenticate(username, password)

    products = search_products(config, wkt_str, token)
    if not products:
        print(" No products found for given AOI/date range.")
        return

    print(f"\n Found {len(products)} product(s):\n")
    for i, p in enumerate(products, start=1):
        date = p["ContentDate"]["Start"][:10]
        name = p["Name"]
        print(f"{i}. {name} | Date: {date} | ID: {p['Id']}")

    choice = input("\nEnter product numbers to download (comma-separated): ")
    selected = [products[int(c.strip()) - 1] for c in choice.split(",") if c.strip().isdigit()]

    for prod in selected:
        download_product_zip(prod["Id"], prod["Name"], token, output_dir="downloads")


if __name__ == "__main__":
    main()
