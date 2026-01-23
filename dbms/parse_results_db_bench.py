import os
import sys
import re
import csv
import glob

def parse_file(filepath):
    results = []
    filename = os.path.basename(filepath)
    try:
        parts = filename.replace('.log', '').split('_')
        threads_str = parts[-1] 
        config = "_".join(parts[1:-1])
        if threads_str.startswith('t'):
            threads = int(threads_str[1:])
        else:
            threads = 0
    except:
        config = "unknown"
        threads = 0
        
    with open(filepath, 'r') as f:
        content = f.read()
    
    pattern = re.compile(r'^([a-zA-Z0-9_]+)\s*:\s+([0-9.]+)\s+micros/op;\s+([0-9.]+)\s+MB/s', re.MULTILINE)
    
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        match = pattern.match(line)
        if match:
            benchmark_name = match.group(1)
            micros_op = float(match.group(2))
            throughput = float(match.group(3))
            
            avg_val = None
            stddev_val = None
            min_val = None
            median_val = None
            max_val = None

            try:
                if i + 2 < len(lines) and "Average:" in lines[i+2]:
                    stat_line = lines[i+2]
                    avg_m = re.search(r'Average:\s+([0-9.]+)', stat_line)
                    std_m = re.search(r'StdDev:\s+([0-9.]+)', stat_line)
                    if avg_m: avg_val = float(avg_m.group(1))
                    if std_m: stddev_val = float(std_m.group(1))
                
                if i + 3 < len(lines) and "Min:" in lines[i+3]:
                    val_line = lines[i+3]
                    min_m = re.search(r'Min:\s+([0-9.]+)', val_line)
                    med_m = re.search(r'Median:\s+([0-9.]+)', val_line)
                    max_m = re.search(r'Max:\s+([0-9.]+)', val_line)
                    if min_m: min_val = float(min_m.group(1))
                    if med_m: median_val = float(med_m.group(1))
                    if max_m: max_val = float(max_m.group(1))
            except:
                pass

            results.append({
                'configuration': config,
                'threads': threads,
                'benchmark': benchmark_name,
                'throughput_mb_s': throughput,
                'average_lat_us': avg_val,
                'stddev_lat_us': stddev_val,
                'min_lat_us': min_val,
                'median_lat_us': median_val,
                'max_lat_us': max_val
            })
        i += 1
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_results.py <results_dir>")
        sys.exit(1)
        
    results_dir = sys.argv[1]
    all_data = []
    
    files = glob.glob(os.path.join(results_dir, "*.log"))
    for f in files:
        all_data.extend(parse_file(f))
        
    all_data.sort(key=lambda x: (x['configuration'], x['threads'], x['benchmark']))
    
    csv_file = os.path.join(results_dir, "results_db_bench.csv")
    with open(csv_file, 'w', newline='') as csvfile:
        fieldnames = ['configuration', 'threads', 'benchmark', 'throughput_mb_s', 'average_lat_us', 'stddev_lat_us', 'min_lat_us', 'median_lat_us', 'max_lat_us']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in all_data:
            writer.writerow(row)

if __name__ == "__main__":
    main()
