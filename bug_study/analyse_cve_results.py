#!/usr/bin/env python3
"""
CVE Results Analysis Script

Analyzes LLM classification results and keyword matches for CVEs.
Generates detailed reports and cumulative statistics.
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
import itertools
import math

# Same database list as scrape_cves.py
DATABASES = ["mysql", "sqlite", "mariadb", "redis", "leveldb", "rocksdb", "duckdb", 
             "ladybug", "postgresql", "mongodb", "memcached", "influxdb", "redshift"]

# Directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CVE_RESULTS_DIR = os.path.join(SCRIPT_DIR, "cve", "cve_results")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "cve", "reports")


def get_cve_id(path):
    """Extract CVE ID from file path."""
    basename = os.path.basename(path)
    return os.path.splitext(basename)[0]


def analyse_dbms(dbms, cumulative_stats=None):
    """
    Analyze CVE results for a single database.
    
    Args:
        dbms: Database name to analyze
        cumulative_stats: Optional list to append stats for cumulative report
    
    Returns:
        Dictionary with analysis results
    """
    print(f"\n{'='*60}")
    print(f"Analyzing CVE results for {dbms}...")
    print(f"{'='*60}")
    
    # Create reports directory
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Load keyword matches
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
            print(f"Error loading matches file: {e}")
    else:
        print(f"Warning: {matches_file} not found. Assuming no keyword matches.")

    results = defaultdict(lambda: {})
    rep_sets = []
    rep_stats_list = []  # Store stats for each rep
    
    for rep in range(1, 4):
        filename = os.path.join(CVE_RESULTS_DIR, f"{dbms}_cve_rep{rep}.json")
        current_rep_mem_safety = set()
        current_rep_stats = defaultdict(int)
        total_examined = 0
        
        if not os.path.exists(filename):
            print(f"File {filename} not found.")
            rep_sets.append(set())
            rep_stats_list.append({'total': 0, 'bugs': 0, 'memory_safety': 0})
            continue
            
        print(f"Reading {filename}...")
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

                        if isinstance(classification, str):
                            try:
                                classification = json.loads(classification)
                            except:
                                continue 
                                
                        if not isinstance(classification, dict):
                            continue

                        total_examined += 1
                        results[f_name][f"rep{rep}"] = classification

                        issue_type = classification.get('issue_type', 'unknown')
                        current_rep_stats[issue_type] += 1
                        
                        is_mem = classification.get('is_memory_safety', False)
                        if is_mem:
                            current_rep_mem_safety.add(f_name)
                        
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error processing file {filename}: {e}")

        rep_sets.append(current_rep_mem_safety)
        
        bug_count = current_rep_stats.get('bug', 0)
        mem_safety_count = len(current_rep_mem_safety)
        
        rep_stats_list.append({
            'total': total_examined,
            'bugs': bug_count,
            'memory_safety': mem_safety_count
        })
        
        # Print stats
        print(f"Rep {rep} Stats:")
        total = sum(current_rep_stats.values())
        if total == 0:
            print("  No entries found.")
        else:
            prog_count = current_rep_stats.get('programmer_error', 0)
            other_count = current_rep_stats.get('other', 0)
            
            def print_stat(label, count, total_base, indent="-"):
                pct = (count / total_base * 100) if total_base > 0 else 0
                print(f"{indent} {label}: {count} ({pct:.2f}%)")

            print_stat("bug", bug_count, total)
            mem_pct = (mem_safety_count / bug_count * 100) if bug_count > 0 else 0
            print(f"    of which {mem_safety_count} memory safety bugs ({mem_pct:.2f}%)")
            print_stat("programmer_error", prog_count, total)
            print_stat("other", other_count, total)
            
        print("-" * 20)

    # Ensure we have 3 rep sets
    while len(rep_sets) < 3:
        rep_sets.append(set())
    while len(rep_stats_list) < 3:
        rep_stats_list.append({'total': 0, 'bugs': 0, 'memory_safety': 0})

    # Add to cumulative stats if provided
    if cumulative_stats is not None:
        cumulative_stats.append({
            'dbms': dbms,
            'keyword_matches': len(keyword_matches),
            'rep1': rep_stats_list[0],
            'rep2': rep_stats_list[1],
            'rep3': rep_stats_list[2]
        })

    # Set intersection analysis
    sets = {
        'Keywords': keyword_matches,
        'LLM_Rep1': rep_sets[0],
        'LLM_Rep2': rep_sets[1],
        'LLM_Rep3': rep_sets[2]
    }
    
    print("\nIntersection of ALL sets (Keywords AND All LLM Reps):")
    
    def print_intersection(s):
        if not s:
            print("  (None)")
        else:
            ids = sorted([get_cve_id(cve) for cve in s])
            print(f"  {', '.join(ids)}")

    keys = list(sets.keys())
    
    for r in range(len(keys), 0, -1):
        for combo in itertools.combinations(keys, r):
            included = set.intersection(*(sets[k] for k in combo))
            others = [sets[k] for k in keys if k not in combo]
            if others:
                excluded = set.union(*others)
                exclusive_intersection = included - excluded
            else:
                exclusive_intersection = included
            
            if not exclusive_intersection:
                continue

            header = " & ".join(combo)
            print(f"\n[{header}] ({len(exclusive_intersection)}):")
            print_intersection(exclusive_intersection)

    # Generate detailed reports
    print("\nGenerating Detailed Reports...")
    
    all_flagged = set.union(keyword_matches, *rep_sets) if (keyword_matches or any(rep_sets)) else set()
    if not all_flagged:
        print("No memory safety issues found to report.")
        return results

    sorted_cves = sorted(list(all_flagged), key=lambda x: get_cve_id(x))
    
    total_cves = len(sorted_cves)
    chunk_size = math.ceil(total_cves / 3) if total_cves > 0 else 1
    chunks = [sorted_cves[i:i + chunk_size] for i in range(0, len(sorted_cves), chunk_size)]
    
    for i, chunk_cves in enumerate(chunks):
        chunk_lines = []
        for cve_file in chunk_cves:
            cve_id = "N/A"
            description = "N/A"
            title = ""
            if os.path.exists(cve_file):
                try:
                    with open(cve_file, 'r') as cf:
                        cdata = json.load(cf)
                        cve_id = cdata.get('cveMetadata', {}).get('cveId', 'N/A')
                        cna = cdata.get('containers', {}).get('cna', {})
                        title = cna.get('title', '')
                        descriptions = cna.get('descriptions', [])
                        if descriptions:
                            description = descriptions[0].get('value', 'N/A')
                except:
                    pass
            
            chunk_lines.append("="*80)
            chunk_lines.append(f"CVE ID: {cve_id}")
            chunk_lines.append(f"File: {cve_file}")
            in_keywords = cve_file in keyword_matches
            chunk_lines.append(f"Keyword Match: {in_keywords}")
            chunk_lines.append("-" * 40)
            if title:
                chunk_lines.append(f"TITLE: {title}")
                chunk_lines.append("-" * 40)
            chunk_lines.append(f"DESCRIPTION:\n{description}")
            chunk_lines.append("-" * 40)
            chunk_lines.append("LLM CLASSIFICATIONS:")
            
            for rep in range(1, 4):
                key = f"rep{rep}"
                chunk_lines.append(f"  [Repetition {rep}]")
                if cve_file in results and key in results[cve_file]:
                    r_data = results[cve_file][key]
                    chunk_lines.append(f"    Issue Type: {r_data.get('issue_type', 'N/A')}")
                    chunk_lines.append(f"    Is Memory Safety: {r_data.get('is_memory_safety', 'N/A')}")
                    chunk_lines.append(f"    Confidence: {r_data.get('confidence', 'N/A')}")
                    chunk_lines.append(f"    Reason: {r_data.get('reason', 'N/A')}")
                else:
                    chunk_lines.append(f"    (No result found)")
                chunk_lines.append("")
            chunk_lines.append("\n")
        
        out_name = os.path.join(REPORTS_DIR, f"report_{dbms}_cve_part{i+1}.txt")
        with open(out_name, "w") as f:
            f.write("\n".join(chunk_lines))
        print(f"Wrote {len(chunk_cves)} CVEs to {out_name}")

    return results


def generate_cumulative_report(cumulative_stats):
    """Generate a cumulative report with stats for all databases."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    report_lines = []
    report_lines.append("=" * 100)
    report_lines.append("CUMULATIVE CVE ANALYSIS REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    # Header
    report_lines.append(f"{'Database':<15} {'Source':<12} {'Total CVEs':>12} {'Bugs':>10} {'Memory Safety':>15} {'Mem %':>10}")
    report_lines.append("-" * 100)
    
    grand_totals = {
        'keywords': 0,
        'rep1_total': 0, 'rep1_bugs': 0, 'rep1_mem': 0,
        'rep2_total': 0, 'rep2_bugs': 0, 'rep2_mem': 0,
        'rep3_total': 0, 'rep3_bugs': 0, 'rep3_mem': 0,
    }
    
    for stats in cumulative_stats:
        dbms = stats['dbms']
        
        # Keyword stats
        kw_count = stats['keyword_matches']
        grand_totals['keywords'] += kw_count
        report_lines.append(f"{dbms:<15} {'Keywords':<12} {'-':>12} {'-':>10} {kw_count:>15} {'-':>10}")
        
        # Rep stats
        for rep_num in [1, 2, 3]:
            rep_key = f'rep{rep_num}'
            rep = stats[rep_key]
            total = rep['total']
            bugs = rep['bugs']
            mem = rep['memory_safety']
            mem_pct = (mem / bugs * 100) if bugs > 0 else 0
            
            grand_totals[f'rep{rep_num}_total'] += total
            grand_totals[f'rep{rep_num}_bugs'] += bugs
            grand_totals[f'rep{rep_num}_mem'] += mem
            
            report_lines.append(f"{'':<15} {f'LLM Rep {rep_num}':<12} {total:>12} {bugs:>10} {mem:>15} {mem_pct:>9.1f}%")
        
        report_lines.append("-" * 100)
    
    # Grand totals
    report_lines.append("")
    report_lines.append("GRAND TOTALS:")
    report_lines.append(f"{'TOTAL':<15} {'Keywords':<12} {'-':>12} {'-':>10} {grand_totals['keywords']:>15} {'-':>10}")
    
    for rep_num in [1, 2, 3]:
        total = grand_totals[f'rep{rep_num}_total']
        bugs = grand_totals[f'rep{rep_num}_bugs']
        mem = grand_totals[f'rep{rep_num}_mem']
        mem_pct = (mem / bugs * 100) if bugs > 0 else 0
        report_lines.append(f"{'':<15} {f'LLM Rep {rep_num}':<12} {total:>12} {bugs:>10} {mem:>15} {mem_pct:>9.1f}%")
    
    report_lines.append("=" * 100)
    
    # Write report
    out_file = os.path.join(REPORTS_DIR, "cumulative_report.txt")
    with open(out_file, "w") as f:
        f.write("\n".join(report_lines))
    
    print(f"\n{'='*60}")
    print(f"Cumulative report written to: {out_file}")
    print(f"{'='*60}")
    
    # Also print to console
    for line in report_lines:
        print(line)


def main():
    if len(sys.argv) > 1:
        dbms_arg = sys.argv[1].lower()
    else:
        dbms_arg = "all"
    
    if dbms_arg == "all":
        print("Analyzing all databases...")
        cumulative_stats = []
        
        for dbms in DATABASES:
            try:
                analyse_dbms(dbms, cumulative_stats)
            except Exception as e:
                print(f"Error analyzing {dbms}: {e}")
                continue
        
        # Generate cumulative report
        if cumulative_stats:
            generate_cumulative_report(cumulative_stats)
    else:
        if dbms_arg not in DATABASES:
            print(f"Warning: '{dbms_arg}' not in standard database list: {DATABASES}")
        analyse_dbms(dbms_arg)


if __name__ == "__main__":
    main()
