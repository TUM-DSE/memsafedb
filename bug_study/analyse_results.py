import json
import os
import sys
from collections import defaultdict
import itertools
import math

def main():
    if len(sys.argv) > 1:
        dbms = sys.argv[1]
    else:
        dbms = "LevelDB"
    print(f"Analyzing results for {dbms}...")

    # Load keyword matches
    keyword_matches = set()
    matches_file = f"dataset/matches_{dbms}.json"
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
    
    for rep in range(1, 4):
        filename = f"dataset/{dbms}_rep{rep}.json" 
        current_rep_mem_safety = set()
        current_rep_stats = defaultdict(int)
        
        if not os.path.exists(filename):
            print(f"File {filename} not found.")
            rep_sets.append(set())
            continue
            
        print(f"Reading {filename}...")
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        entry = json.loads(line)
                        f_name = entry.get('file')
                        if not f_name: continue
                        
                        classification = entry.get('classification')
                        if not classification: continue

                        if isinstance(classification, str):
                            try:
                                classification = json.loads(classification)
                            except:
                                continue 
                                
                        if not isinstance(classification, dict):
                            continue

                        # Store full details
                        results[f_name][f"rep{rep}"] = classification

                        issue_type = classification.get('issue_type', 'unknown')
                        current_rep_stats[issue_type] += 1
                        
                        is_mem = classification.get('is_memory_safety', False)
                        if is_mem:
                            current_rep_mem_safety.add(f_name)
                        
                    except Exception as e:
                        continue
        except Exception as e:
             print(f"Error processing file {filename}: {e}")

        rep_sets.append(current_rep_mem_safety)
        
        print(f"Rep {rep} Stats:")
        total = sum(current_rep_stats.values())
        if total == 0:
            print("  No entries found.")
        else:
            bug_count = current_rep_stats.get('bug', 0)
            prog_count = current_rep_stats.get('programmer_error', 0)
            other_count = current_rep_stats.get('other', 0)
            
            mem_safety_count = len(current_rep_mem_safety)
            
            def print_stat(label, count, total_base, indent="-"):
                 pct = (count / total_base * 100) if total_base > 0 else 0
                 print(f"{indent} {label}: {count} ({pct:.2f}%)")

            print_stat("bug", bug_count, total)
            mem_pct = (mem_safety_count / bug_count * 100) if bug_count > 0 else 0
            print(f"    of which {mem_safety_count} memory safety bugs ({mem_pct:.2f}%)")
            print_stat("programmer_error", prog_count, total)
            print_stat("other", other_count, total)
            
        print("-" * 20)

    while len(rep_sets) < 3:
        rep_sets.append(set())

    sets = {
        'Keywords': keyword_matches,
        'LLM_Rep1': rep_sets[0],
        'LLM_Rep2': rep_sets[1],
        'LLM_Rep3': rep_sets[2]
    }
    
    print("\nIntersection of ALL sets (Keywords AND All LLM Reps):")
    def get_id(path):
        return os.path.splitext(os.path.basename(path))[0]

    def print_intersection(s):
        if not s:
            print("  (None)")
        else:
            ids = sorted([get_id(bug) for bug in s], key=lambda x: int(x) if x.isdigit() else x)
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

    # ---------------------------------------------------------
    # Generate Detailed Reports
    # ---------------------------------------------------------
    print("\nGenerating Detailed Reports...")
    
    # Identify all files that were flagged as memory safety by ANY method
    # Union of keyword matches and all 3 LLM reps
    all_flagged = set.union(keyword_matches, *rep_sets)
    if not all_flagged:
        print("No memory safety issues found to report.")
        return

    sorted_bugs = sorted(list(all_flagged), key=lambda x: int(get_id(x)) if get_id(x).isdigit() else get_id(x))
    
    report_lines = []
    
    for bug_file in sorted_bugs:
        # Try to read original file content
        title = "N/A"
        body = "N/A"
        if os.path.exists(bug_file):
            try:
                with open(bug_file, 'r') as bf:
                    bdata = json.load(bf)
                    title = bdata.get('title', 'N/A')
                    body = bdata.get('body', 'N/A')
            except:
                pass
        
        bug_id = get_id(bug_file)
        
        report_lines.append("="*80)
        report_lines.append(f"BUG ID: {bug_id}")
        report_lines.append(f"File: {bug_file}")
        
        in_keywords = bug_file in keyword_matches
        report_lines.append(f"Keyword Match: {in_keywords}")
        report_lines.append("-" * 40)
        report_lines.append(f"TITLE: {title}")
        report_lines.append("-" * 40)
        report_lines.append(f"DESCRIPTION:\n{body}")
        report_lines.append("-" * 40)
        report_lines.append("LLM CLASSIFICATIONS:")
        
        for rep in range(1, 4):
            key = f"rep{rep}"
            report_lines.append(f"  [Repetition {rep}]")
            if bug_file in results and key in results[bug_file]:
                r_data = results[bug_file][key]
                report_lines.append(f"    Issue Type: {r_data.get('issue_type', 'N/A')}")
                report_lines.append(f"    Is Memory Safety: {r_data.get('is_memory_safety', 'N/A')}")
                report_lines.append(f"    Confidence: {r_data.get('confidence', 'N/A')}")
                report_lines.append(f"    Reason: {r_data.get('reason', 'N/A')}")
            else:
                 report_lines.append(f"    (No result found)")
            report_lines.append("")
        
        report_lines.append("\n")

    total_bugs = len(sorted_bugs)
    chunk_size = math.ceil(total_bugs / 3)
    
    chunks = [sorted_bugs[i:i + chunk_size] for i in range(0, len(sorted_bugs), chunk_size)]
    
    for i, chunk_bugs in enumerate(chunks):
        chunk_lines = []
        for bug_file in chunk_bugs:
            title = "N/A"
            body = "N/A"
            if os.path.exists(bug_file):
                try:
                    with open(bug_file, 'r') as bf:
                        bdata = json.load(bf)
                        title = bdata.get('title', 'N/A')
                        body = bdata.get('body', 'N/A')
                except:
                    pass
            
            bug_id = get_id(bug_file)
            chunk_lines.append("="*80)
            chunk_lines.append(f"BUG ID: {bug_id}")
            chunk_lines.append(f"File: {bug_file}")
            in_keywords = bug_file in keyword_matches
            chunk_lines.append(f"Keyword Match: {in_keywords}")
            chunk_lines.append("-" * 40)
            chunk_lines.append(f"TITLE: {title}")
            chunk_lines.append("-" * 40)
            chunk_lines.append(f"DESCRIPTION:\n{body}")
            chunk_lines.append("-" * 40)
            chunk_lines.append("LLM CLASSIFICATIONS:")
            
            for rep in range(1, 4):
                key = f"rep{rep}"
                chunk_lines.append(f"  [Repetition {rep}]")
                if bug_file in results and key in results[bug_file]:
                    r_data = results[bug_file][key]
                    chunk_lines.append(f"    Issue Type: {r_data.get('issue_type', 'N/A')}")
                    chunk_lines.append(f"    Is Memory Safety: {r_data.get('is_memory_safety', 'N/A')}")
                    chunk_lines.append(f"    Confidence: {r_data.get('confidence', 'N/A')}")
                    chunk_lines.append(f"    Reason: {r_data.get('reason', 'N/A')}")
                else:
                     chunk_lines.append(f"    (No result found)")
                chunk_lines.append("")
            chunk_lines.append("\n")
        
        out_name = f"dataset/report_{dbms}_part{i+1}.txt"
        with open(out_name, "w") as f:
            f.write("\n".join(chunk_lines))
        print(f"Wrote {len(chunk_bugs)} bugs to {out_name}")

if __name__ == "__main__":
    main()
