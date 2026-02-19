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
    Search for CVEs mentioning a specific database.
    Case-insensitive search.
    """
    cves_path = cve_dir / "cves"
    if not cves_path.exists():
        print(f"[WARNING] CVEs directory not found: {cves_path}")
        return []
    
    matches = []
    pattern = re.compile(database, re.IGNORECASE)
    
    # Walk through all JSON files in the cves directory
    for json_file in cves_path.rglob("*.json"):
        try:
            content = json_file.read_text(encoding='utf-8', errors='ignore')
            if pattern.search(content):
                # Store relative path from output_dir
                rel_path = json_file.relative_to(output_dir)
                matches.append(str(rel_path))
        except Exception as e:
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


def scrape_cves(output_dir: Path, databases: list = None, force: bool = False):
    """Main function to scrape CVEs for all databases."""
    if databases is None:
        databases = DATABASES
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    args = parser.parse_args()
    
    scrape_cves(
        output_dir=Path(args.output),
        databases=args.databases,
        force=args.force
    )


if __name__ == '__main__':
    main()
