#!/usr/bin/env python3
"""
CVE Results CSV Export Script

Exports CVE analysis results to CSV format with yearly statistics.
Output format: db,year,total_bugs,memory_safety_bugs_llms,memory_safety_bugs_keywords
"""
import json
import os
import sys
import csv
import re
from collections import defaultdict, Counter

# Same database list as scrape_cves.py
DATABASES = ["mysql", "sqlite", "mariadb", "redis", "leveldb", "rocksdb", "duckdb", 
             "ladybug", "postgresql", "mongodb", "memcached", "influxdb", "redshift"]

# Directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CVE_RESULTS_DIR = os.path.join(SCRIPT_DIR, "cve", "cve_results")
CVE_DIR = os.path.join(SCRIPT_DIR, "cve")


def extract_year_from_cve_path(cve_path):
    """Extract year from CVE file path (e.g., CVE-2009-2761.json -> 2009)."""
    match = re.search(r'CVE-(\d{4})-', os.path.basename(cve_path))
    if match:
        return int(match.group(1))
    return None


def load_keyword_matches(dbms):
    """Load keyword matches for a database."""
    keyword_matches = set()
    matches_file = os.path.join(CVE_RESULTS_DIR, f"matches_{dbms}_cve.json")
    if os.path.exists(matches_file):
        try:
            with open(matches_file, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        keyword_matches = set(data)
        except Exception as e:
            print(f"Error loading matches file for {dbms}: {e}", file=sys.stderr)
    return keyword_matches


def load_llm_results(dbms):
    """
    Load LLM classification results for all 3 repetitions.
    
    Returns:
        dict: {cve_file_path: {'rep1': {...}, 'rep2': {...}, 'rep3': {...}}}
    """
    results = defaultdict(lambda: {})
    
    for rep in range(1, 4):
        filename = os.path.join(CVE_RESULTS_DIR, f"{dbms}_cve_rep{rep}.json")
        
        if not os.path.exists(filename):
            print(f"Warning: {filename} not found", file=sys.stderr)
            continue
            
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        f_name = entry.get('file')
                        if not f_name:
                            continue
                        
                        classification = entry.get('classification')
                        if not classification:
                            continue

                        # Parse classification if it's a string
                        if isinstance(classification, str):
                            try:
                                classification = json.loads(classification)
                            except:
                                continue 
                                
                        if not isinstance(classification, dict):
                            continue

                        results[f_name][f"rep{rep}"] = classification
                        
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"Error processing file {filename}: {e}", file=sys.stderr)
    
    return results


YEAR_MIN = 2015
YEAR_MAX = 2025


def analyze_dbms_by_year(dbms):
    """
    Analyze CVE results for a database, grouped by year.

    Returns:
        tuple: (
            yearly: {year: {'total': int, 'llm_memsafe': int, 'keyword_memsafe': int}},
            db_summary: {'total': int, 'llm_memsafe': int, 'implications_unanimous': Counter}
                        (filtered to YEAR_MIN–YEAR_MAX)
        )
    """
    print(f"Analyzing {dbms}...", file=sys.stderr)

    keyword_matches = load_keyword_matches(dbms)
    llm_results = load_llm_results(dbms)

    # Group by year
    yearly_stats = defaultdict(lambda: {
        'total_cves': set(),
        'llm_memsafe': set(),
        'keyword_memsafe': set()
    })

    # Count total from source CVE list (all examined CVEs in YEAR_MIN–YEAR_MAX)
    cve_list_file = os.path.join(CVE_DIR, f"{dbms}_cves")
    db_total = 0
    if os.path.exists(cve_list_file):
        with open(cve_list_file) as f:
            for line in f:
                path = line.strip()
                if path:
                    year = extract_year_from_cve_path(path)
                    if year is not None and YEAR_MIN <= year <= YEAR_MAX:
                        db_total += 1
    db_memsafe = 0
    db_implications_unanimous = Counter()

    all_cves = set(llm_results.keys())

    for cve_path in all_cves:
        year = extract_year_from_cve_path(cve_path)
        if year is None:
            continue

        reps = llm_results[cve_path]
        bug_count = 0
        memsafe_count = 0
        implication_votes = Counter()

        for rep_num in [1, 2, 3]:
            rep_key = f"rep{rep_num}"
            if rep_key in reps:
                classification = reps[rep_key]
                issue_type = classification.get('issue_type', '')
                is_memsafe = classification.get('is_memory_safety', False)
                implication = classification.get('implication', 'none')

                if issue_type == 'bug':
                    bug_count += 1
                    if is_memsafe:
                        memsafe_count += 1
                if implication:
                    implication_votes[implication] += 1

        # All 3 reps agree it's a bug — count for CSV yearly stats
        if bug_count == 3:
            yearly_stats[year]['total_cves'].add(cve_path)

        # All 3 reps agree it's a memory safety bug
        if memsafe_count == 3:
            yearly_stats[year]['llm_memsafe'].add(cve_path)
            if YEAR_MIN <= year <= YEAR_MAX:
                db_memsafe += 1
                # Unanimous implication — only for memory safety CVEs, 2015-2025
                if implication_votes:
                    top_implication, top_count = implication_votes.most_common(1)[0]
                    if top_count == 3:
                        db_implications_unanimous[top_implication] += 1

    # Process keyword matches
    for cve_path in keyword_matches:
        year = extract_year_from_cve_path(cve_path)
        if year is None:
            continue
        yearly_stats[year]['keyword_memsafe'].add(cve_path)

    # Convert sets to counts
    result = {}
    for year, stats in yearly_stats.items():
        result[year] = {
            'total': len(stats['total_cves']),
            'llm_memsafe': len(stats['llm_memsafe']),
            'keyword_memsafe': len(stats['keyword_memsafe'])
        }

    db_summary = {
        'total': db_total,
        'llm_memsafe': db_memsafe,
        'implications_unanimous': db_implications_unanimous,
    }

    return result, db_summary


IMPLICATION_CATEGORIES = [
    'data_loss', 'data_corruption', 'incorrect_query_results', 'system_crash',
    'resource_exhaustion', 'concurrency_hazard', 'transaction_violation',
    'durability_violation', 'replication_inconsistency', 'denial_of_service', 'none'
]


def print_summary_tables(all_db_summaries):
    """Print summary tables to stdout (data filtered to YEAR_MIN–YEAR_MAX)."""

    # ── Table 1: per-DB totals ──────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"TABLE 1: CVE Totals per Database ({YEAR_MIN}–{YEAR_MAX}, all 3 LLM reps agree)")
    print("=" * 60)
    header = f"{'Database':<16} {'Total CVEs':>12} {'Mem Safety':>12} {'Mem% of CVEs':>14}"
    print(header)
    print("-" * 60)
    grand_total = grand_memsafe = 0
    for dbms, summary in all_db_summaries:
        total = summary['total']
        memsafe = summary['llm_memsafe']
        pct = (memsafe / total * 100) if total > 0 else 0.0
        grand_total += total
        grand_memsafe += memsafe
        print(f"{dbms:<16} {total:>12} {memsafe:>12} {pct:>13.1f}%")
    print("-" * 60)
    grand_pct = (grand_memsafe / grand_total * 100) if grand_total > 0 else 0.0
    print(f"{'TOTAL':<16} {grand_total:>12} {grand_memsafe:>12} {grand_pct:>13.1f}%")
    print()

    # ── Table 2: implication breakdown for memory safety CVEs (unanimous) ───
    active_cats = [c for c in IMPLICATION_CATEGORIES
                   if any(s['implications_unanimous'].get(c, 0) > 0 for _, s in all_db_summaries)]

    col_w = 10
    db_col = 16

    abbrev = {
        'data_loss': 'DataLoss',
        'data_corruption': 'DataCorr',
        'incorrect_query_results': 'WrongQry',
        'system_crash': 'Crash',
        'resource_exhaustion': 'ResExhst',
        'concurrency_hazard': 'Concur',
        'transaction_violation': 'TxnViol',
        'durability_violation': 'DurViol',
        'replication_inconsistency': 'ReplIncn',
        'denial_of_service': 'DoS',
        'none': 'None',
    }

    width = db_col + col_w * len(active_cats)
    print("=" * width)
    print(f"TABLE 2: Implication Breakdown — Memory Safety CVEs, Unanimous ({YEAR_MIN}–{YEAR_MAX})")
    print("=" * width)
    hdr_cats = ''.join(abbrev.get(c, c)[:col_w].rjust(col_w) for c in active_cats)
    print(f"{'Database':<{db_col}}{hdr_cats}")
    print("-" * width)
    for dbms, summary in all_db_summaries:
        impl = summary['implications_unanimous']
        row = ''.join(str(impl.get(c, 0)).rjust(col_w) for c in active_cats)
        print(f"{dbms:<{db_col}}{row}")
    print()


def export_to_csv(output_file="cve_results_by_year.csv"):
    """Export all database CVE results to CSV and print summary tables."""
    all_rows = []
    all_db_summaries = []

    for dbms in DATABASES:
        yearly_stats, db_summary = analyze_dbms_by_year(dbms)
        all_db_summaries.append((dbms, db_summary))

        for year, stats in sorted(yearly_stats.items()):
            all_rows.append({
                'db': dbms,
                'year': year,
                'total_bugs': stats['total'],
                'memory_safety_bugs_llms': stats['llm_memsafe'],
                'memory_safety_bugs_keywords': stats['keyword_memsafe']
            })

    # Write to CSV
    output_path = os.path.join(CVE_DIR, output_file)
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['db', 'year', 'total_bugs', 'memory_safety_bugs_llms', 'memory_safety_bugs_keywords']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"CSV exported to: {output_path}")
    print(f"Total rows: {len(all_rows)}")

    print_summary_tables(all_db_summaries)

    return output_path


def main():
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    else:
        output_file = "cve_results_by_year.csv"
    
    export_to_csv(output_file)


if __name__ == "__main__":
    main()
