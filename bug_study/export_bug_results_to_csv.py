#!/usr/bin/env python3
"""
Bug Results CSV Export Script

Exports bug analysis results to CSV format with yearly statistics.
Output format: db,year,total_bugs,memory_safety_bugs_llms,memory_safety_bugs_keywords

Handles different bug tracker formats:
- GitHub: created_at field (ISO 8601)
- Jira: created field (ISO 8601 with timezone)
- MySQL: date in description text (e.g., "[4 Jan 2005 13:54]")
"""
import json
import os
import sys
import csv
import re
from collections import defaultdict
from datetime import datetime

# Database list matching bugs.just
DATABASES = ["DuckDB", "Redis", "RocksDB", "MongoDB", "ClickHouse", "CockroachDB", 
             "MariaDB", "MySQL", "LevelDB"]

# Directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUG_RESULTS_DIR = os.path.join(SCRIPT_DIR, "memsafedb_bugs", "bug_results")
BUGS_DIR = os.path.join(SCRIPT_DIR, "memsafedb_bugs")


def extract_year_from_bug(bug_path):
    """
    Extract year from bug JSON file based on tracker type.
    
    Returns:
        int or None: Year if found, None otherwise
    """
    try:
        with open(bug_path, 'r') as f:
            data = json.load(f)
        
        # Try GitHub format: created_at (ISO 8601)
        if 'created_at' in data:
            created_at = data['created_at']
            # Format: "2014-09-09T17:20:51Z"
            match = re.match(r'(\d{4})-', created_at)
            if match:
                return int(match.group(1))
        
        # Try Jira format: created (ISO 8601 with timezone)
        if 'created' in data:
            created = data['created']
            # Format: "2026-01-30T07:55:39.000+0000"
            match = re.match(r'(\d{4})-', created)
            if match:
                return int(match.group(1))
        
        # Try MySQL format: date in description text
        if 'description' in data:
            description = data['description']
            # Format: "[4 Jan 2005 13:54]" or "Submitted: 4 Jan 2005 13:54"
            match = re.search(r'\[?\d{1,2}\s+\w+\s+(\d{4})', description)
            if match:
                return int(match.group(1))
            
            # Also check html_content for MySQL bugs
            if 'html_content' in data:
                html = data['html_content']
                match = re.search(r'Submitted:\s*</th>\s*<td>(\d{1,2}\s+\w+\s+\d{4})', html)
                if match:
                    date_str = match.group(1)
                    year_match = re.search(r'(\d{4})', date_str)
                    if year_match:
                        return int(year_match.group(1))
        
        return None
        
    except Exception as e:
        print(f"Error extracting year from {bug_path}: {e}", file=sys.stderr)
        return None


def load_keyword_matches(dbms):
    """Load keyword matches for a database."""
    keyword_matches = set()
    matches_file = os.path.join(BUG_RESULTS_DIR, f"matches_{dbms}.json")
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
        dict: {bug_file_path: {'rep1': {...}, 'rep2': {...}, 'rep3': {...}}}
    """
    results = defaultdict(lambda: {})
    
    for rep in range(1, 4):
        filename = os.path.join(BUG_RESULTS_DIR, f"{dbms}_rep{rep}.json")
        
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


def analyze_dbms_by_year(dbms):
    """
    Analyze bug results for a database, grouped by year.

    Returns:
        tuple: (
            yearly: {year: {'total': int, 'llm_memsafe': int, 'keyword_memsafe': int}},
            db_summary: {'total': int, 'llm_memsafe': int, 'implications': Counter}
        )
    """
    print(f"Analyzing {dbms}...", file=sys.stderr)

    from collections import Counter

    keyword_matches = load_keyword_matches(dbms)
    llm_results = load_llm_results(dbms)

    # Group by year
    yearly_stats = defaultdict(lambda: {
        'total_bugs': set(),
        'llm_memsafe': set(),
        'keyword_memsafe': set()
    })

    # Count total from source directory (all scraped issues)
    source_dir = os.path.join(BUGS_DIR, dbms)
    db_total = sum(1 for f in os.listdir(source_dir) if f.endswith('.json')) \
               if os.path.isdir(source_dir) else 0
    db_memsafe = 0
    db_implications_unanimous = Counter()

    all_bugs = set(llm_results.keys())

    for bug_path in all_bugs:
        year = extract_year_from_bug(bug_path)
        reps = llm_results[bug_path]
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
            if year is not None:
                yearly_stats[year]['total_bugs'].add(bug_path)

        # All 3 reps agree it's a memory safety bug
        if memsafe_count == 3:
            db_memsafe += 1
            if year is not None:
                yearly_stats[year]['llm_memsafe'].add(bug_path)
            # Unanimous implication — only for memory safety bugs
            if implication_votes:
                top_implication, top_count = implication_votes.most_common(1)[0]
                if top_count == 3:
                    db_implications_unanimous[top_implication] += 1

    # Process keyword matches
    for bug_path in keyword_matches:
        year = extract_year_from_bug(bug_path)
        if year is None:
            continue
        yearly_stats[year]['keyword_memsafe'].add(bug_path)

    # Convert sets to counts
    yearly_result = {}
    for year, stats in yearly_stats.items():
        yearly_result[year] = {
            'total': len(stats['total_bugs']),
            'llm_memsafe': len(stats['llm_memsafe']),
            'keyword_memsafe': len(stats['keyword_memsafe'])
        }

    db_summary = {
        'total': db_total,
        'llm_memsafe': db_memsafe,
        'implications_unanimous': db_implications_unanimous,
    }

    return yearly_result, db_summary


IMPLICATION_CATEGORIES = [
    'data_loss', 'data_corruption', 'incorrect_query_results', 'system_crash',
    'resource_exhaustion', 'concurrency_hazard', 'transaction_violation',
    'durability_violation', 'replication_inconsistency', 'denial_of_service', 'none'
]


def print_summary_tables(all_db_summaries):
    """Print two summary tables to stdout."""

    # ── Table 1: per-DB totals ──────────────────────────────────────────────
    print()
    print("=" * 60)
    print("TABLE 1: Bug Totals per Database (all 3 LLM reps agree)")
    print("=" * 60)
    header = f"{'Database':<16} {'Total Bugs':>12} {'Mem Safety':>12} {'Mem% of Bugs':>14}"
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

    # ── Table 2: implication breakdown for memory safety bugs (unanimous) ────
    # Only show categories that appear at least once
    active_cats = [c for c in IMPLICATION_CATEGORIES
                   if any(s['implications_unanimous'].get(c, 0) > 0 for _, s in all_db_summaries)]

    col_w = 10  # width per category column
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

    def print_implication_table(title, key):
        print("=" * (db_col + col_w * len(active_cats)))
        print(title)
        print("=" * (db_col + col_w * len(active_cats)))
        hdr_cats = ''.join(abbrev.get(c, c)[:col_w].rjust(col_w) for c in active_cats)
        print(f"{'Database':<{db_col}}{hdr_cats}")
        print("-" * (db_col + col_w * len(active_cats)))
        for dbms, summary in all_db_summaries:
            impl = summary[key]
            row = ''.join(str(impl.get(c, 0)).rjust(col_w) for c in active_cats)
            print(f"{dbms:<{db_col}}{row}")
        print()

    print_implication_table(
        "TABLE 2: Implication Breakdown — Memory Safety Bugs, Unanimous (all 3 reps agree)",
        'implications_unanimous'
    )


def export_to_csv(output_file="bug_results_by_year.csv"):
    """Export all database bug results to CSV and print summary tables."""
    all_rows = []
    all_db_summaries = []

    for dbms in DATABASES:
        yearly_stats, db_summary = analyze_dbms_by_year(dbms)
        all_db_summaries.append((dbms, db_summary))

        for year, stats in sorted(yearly_stats.items()):
            all_rows.append({
                'db': dbms.lower(),
                'year': year,
                'total_bugs': stats['total'],
                'memory_safety_bugs_llms': stats['llm_memsafe'],
                'memory_safety_bugs_keywords': stats['keyword_memsafe']
            })

    # Write to CSV
    output_path = os.path.join(BUGS_DIR, output_file)
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['db', 'year', 'total_bugs', 'memory_safety_bugs_llms', 'memory_safety_bugs_keywords']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"CSV exported to: {output_path}")
    print(f"Total rows: {len(all_rows)}")

    # Print summary tables
    print_summary_tables(all_db_summaries)

    return output_path


def main():
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    else:
        output_file = "bug_results_by_year.csv"

    export_to_csv(output_file)


if __name__ == "__main__":
    main()
