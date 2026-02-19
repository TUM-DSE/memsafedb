#!/usr/bin/env python3
"""
CVE Scraper for Database Memory Safety Analysis

Downloads the CVE list from the CVEProject repository and filters
CVEs by database name (mysql, sqlite, mariadb, redis, leveldb, rocksdb, duckdb).
"""

import os
import sys
import json
import zipfile
import urllib.request
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import re


CVE_LIST_URL = "https://github.com/CVEProject/cvelistV5/archive/refs/heads/main.zip"
ZIP_FILE = "main.zip"
UNZIP_DIR = "cvelistV5-main"
DATABASES = ["mysql", "sqlite", "mariadb", "redis", "leveldb", "rocksdb", "duckdb", "ladybug", "postgresql", 
                "mongodb", "memcached", "influxdb", "redshift"]


def download_cve_list(output_dir: Path, force: bool = False) -> Path:
    """Download the CVE list zip file if not already present."""
    zip_path = output_dir / ZIP_FILE
    
    if zip_path.exists() and not force:
        print(f"[INFO] {ZIP_FILE} already exists. Use --force to re-download.")
        return zip_path
    
    print(f"[INFO] Downloading CVE list from {CVE_LIST_URL}...")
    urllib.request.urlretrieve(CVE_LIST_URL, zip_path)
    print(f"[INFO] Downloaded to {zip_path}")
    return zip_path


def extract_cve_list(zip_path: Path, output_dir: Path, force: bool = False) -> Path:
    """Extract the CVE list zip file."""
    extract_dir = output_dir / UNZIP_DIR
    
    if extract_dir.exists() and not force:
        print(f"[INFO] {UNZIP_DIR} already exists. Use --force to re-extract.")
        return extract_dir
    
    print(f"[INFO] Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    print(f"[INFO] Extracted to {extract_dir}")
    return extract_dir


def search_cves_for_database(cve_dir: Path, database: str, output_dir: Path) -> list:
    """
    Search for CVEs mentioning a specific database in product or packageName.
    Case-insensitive search.
    """
    cves_path = cve_dir / "cves"
    if not cves_path.exists():
        print(f"[WARNING] CVEs directory not found: {cves_path}")
        return []
    
    matches = []
    pattern = re.compile(re.escape(database), re.IGNORECASE)
    
    # Walk through all JSON files in the cves directory
    # Note: parsing all JSONs might be slower but is more accurate
    for json_file in cves_path.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            found = False
            # Check containers.cna.affected
            cna = data.get('containers', {}).get('cna', {})
            affected_items = cna.get('affected', [])
            
            for item in affected_items:
                product = item.get('product', '')
                package_name = item.get('packageName', '')
                
                if (product and pattern.search(str(product))) or (package_name and pattern.search(str(package_name))):
                    found = True
                    break
            
            if found:
                # Store relative path from output_dir
                try:
                    rel_path = json_file.relative_to(output_dir)
                    matches.append(str(rel_path))
                except ValueError:
                    matches.append(str(json_file))
                    
        except Exception:
            continue
    
    return matches


def save_cve_list(matches: list, database: str, output_dir: Path) -> Path:
    """Save the list of matching CVE files."""
    output_file = output_dir / f"{database}_cves"
    
    with open(output_file, 'w') as f:
        for match in sorted(matches):
            f.write(f"./{match}\n")
    
    print(f"[{database.upper()}] Found {len(matches)} CVEs -> {output_file}")
    return output_file


def scrape_cves(output_dir: Path, databases: list = None, force: bool = False, skip_download: bool = False):
    """Main function to scrape CVEs for all databases."""
    if databases is None:
        databases = DATABASES
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if skip_download:
        cve_dir = output_dir / UNZIP_DIR
        if not cve_dir.exists():
            print(f"[ERROR] --skip-download specified but {cve_dir} does not exist.")
            sys.exit(1)
        print(f"[INFO] Skipping download. Using existing CVE data in {cve_dir}")
    else:
        # Download and extract
        zip_path = download_cve_list(output_dir, force)
        cve_dir = extract_cve_list(zip_path, output_dir, force)
    
    print(f"\n[INFO] Searching for CVEs for {len(databases)} databases...")
    
    # Search for each database
    for db in databases:
        matches = search_cves_for_database(cve_dir, db, output_dir)
        save_cve_list(matches, db, output_dir)
    
    print("\n[INFO] CVE scraping complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape CVEs from CVEProject repository and filter by database"
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='.',
        help='Output directory for CVE data (default: current directory)'
    )
    parser.add_argument(
        '--databases', '-d',
        type=str,
        nargs='+',
        default=DATABASES,
        help=f'Databases to search for (default: {", ".join(DATABASES)})'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force re-download and re-extract even if files exist'
    )
    parser.add_argument(
        '--skip-download', '-s',
        action='store_true',
        help='Skip download and extraction, only perform filtering'
    )
    
    args = parser.parse_args()
    
    scrape_cves(
        output_dir=Path(args.output),
        databases=args.databases,
        force=args.force,
        skip_download=args.skip_download
    )


if __name__ == '__main__':
    main()
