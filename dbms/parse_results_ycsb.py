import os
import sys
import re
import csv
import glob

def parse_file(filepath):
    results = []
    filename = os.path.basename(filepath)
    # Expected filename: ycsb_<workload>_<config>_t<threads>.log
    try:
        parts = filename.replace('.log', '').split('_')
        # parts: ['ycsb', 'a', 'mte', 't1']
        workload = parts[1]
        config = "_".join(parts[2:-1])
        threads_str = parts[-1]
        if threads_str.startswith('t'):
            threads = int(threads_str[1:])
        else:
            threads = 0
    except:
        workload = "unknown"
        config = "unknown"
        threads = 0

    with open(filepath, 'r') as f:
        content = f.read()

    # We only care about the Run phase.
    # The log typically has Load phase first, then Run phase.
    # Look for "Run throughput(ops/sec):" to separate or identify the block.
    # The status lines look like:
    # 2026-01-22 17:15:14 2 sec: 100000 operations; [READ: Count=50145 Max=8017.40 Min=2.02 Avg=12.00] ...

    # Split into lines
    lines = content.split('\n')
    
    run_throughput = None
    last_status_line = None
    
    # Iterate to find the Run phase info
    # We look for "Run throughput(ops/sec):"
    # And we assume the status line describing the run is shortly before it.
    
    for i, line in enumerate(lines):
        if "Run throughput(ops/sec):" in line:
            try:
                run_throughput = float(line.split(':')[-1].strip())
            except:
                pass
            
            # Look backwards for the status line
            # It usually starts with a timestamp or "sec:" and contains "operations;" and square brackets
            for j in range(i - 1, -1, -1):
                prev = lines[j].strip()
                if "operations;" in prev and "[" in prev and "]" in prev:
                    last_status_line = prev
                    break
    
    if run_throughput is not None and last_status_line:
        # Parse the status line for weighted avg
        # Pattern for ops: [OPNAME: Count=XXX Max=XXX Min=XXX Avg=XXX]
        op_pattern = re.compile(r'\[([A-Z]+): Count=(\d+) Max=[0-9.]+ Min=[0-9.]+ Avg=([0-9.]+)\]')
        
        ops = op_pattern.findall(last_status_line)
        
        total_count = 0
        total_weighted_sum = 0.0
        
        for op_name, count_str, avg_str in ops:
            count = int(count_str)
            avg = float(avg_str)
            
            total_count += count
            total_weighted_sum += (count * avg)
            
        if total_count > 0:
            avg_latency = total_weighted_sum / total_count
            
            results.append({
                'configuration': config,
                'threads': threads,
                'workload': workload,
                'throughput_ops_sec': run_throughput,
                'average_lat_us': avg_latency
            })

    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_results_ycsb.py <results_dir>")
        sys.exit(1)
        
    results_dir = sys.argv[1]
    all_data = []
    
    files = glob.glob(os.path.join(results_dir, "ycsb_*.log"))
    for f in files:
        all_data.extend(parse_file(f))
        
    all_data.sort(key=lambda x: (x['configuration'], x['threads'], x['workload']))
    
    csv_file = os.path.join(results_dir, "results_ycsb.csv")
    with open(csv_file, 'w', newline='') as csvfile:
        fieldnames = ['configuration', 'threads', 'workload', 'throughput_ops_sec', 'average_lat_us']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in all_data:
            writer.writerow(row)
            
    print(f"Parsed {len(all_data)} records. CSV written to {csv_file}")

if __name__ == "__main__":
    main()
