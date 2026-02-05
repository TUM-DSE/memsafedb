bugs_dir := source_dir()
output_dir := "/scratch/$USER/memsafedb/bug_study/memsafedb_bugs/"
cve_dir := "/scratch/$USER/memsafedb/bug_study/cve/"
dockerfile_path := bugs_dir+"/Dockerfile"
keywords := "buffer overflow|buffer overrun|buffer underflow|buffer underrun|out of bounds|array bounds|stack overflow|stack smashing|integer overflow|null pointer dereference|null pointer exception|double free|multiple free|uninitialized memory|use of uninitialized|wild pointer|dangling pointer|dangling reference|use after free|UAF|stack use after scope|stack use after return|memory safety|memory corruption|heap corruption|stack corruption|memory error|invalid memory access|illegal memory access|segmentation fault|SIGSEGV|address sanitizer|ASLR"
# make the keywords fuzzy
default:
    @just --list

scrape:
    #!/usr/bin/env bash
    mkdir -p {{output_dir}}
    rm -rf {{output_dir}}/*
    python3 scrape_bugs.py --output "{{output_dir}}"

scrape_cves:
    #!/usr/bin/env bash
    python3 {{bugs_dir}}/scrape_cves.py --output "{{cve_dir}}"

search_bugs dbms="":
    #!/usr/bin/env bash
    grep -lEi "{{keywords}}" {{output_dir}}/{{dbms}}/*.json || true

build_docker:
    #!/usr/bin/env bash
    ssh jack "nix develop {{bugs_dir}}/..#jack --command docker build -t llama-server-cuda -f {{bugs_dir}}/Dockerfile {{bugs_dir}}" #> /dev/null 2>&1

launch_server: build_docker
    #!/usr/bin/env bash
    ssh jack "nix develop {{bugs_dir}}/..#jack --command docker run -d --device=nvidia.com/gpu=all -v /scratch/$USER/models:/models -p 8080:8080 llama-server-cuda" > /dev/null 2>&1

kill_server:
    ssh jack "nix develop {{bugs_dir}}/..#jack --command docker stop $(docker ps -q --filter name=llama-server-cuda)"

classify_bugs +files:
    #!/usr/bin/env python3
    import sys
    import json
    import requests
    import os
    import concurrent.futures
    from tqdm import tqdm
    files = "{{files}}".split()
    
    API_URL = "http://jack:8080/v1/chat/completions"
    MODEL = "Meta-Llama-3.1-8B-Instruct-Q8_0.gguf"
    
    SYSTEM_PROMPT = "You are an expert software security researcher specializing in database systems."
    
    def process_file(bug_file):
        try:
            with open(bug_file, 'r') as f:
                data = json.load(f)
            title = data.get('title', '')
            desc = data.get('body', '')
            
            json_template = '{ "issue_type": "bug/programmer_error/other", "is_memory_safety": true/false, "confidence": "high/medium/low", "reason": "Brief explanation..." }'
            user_prompt = f"""Analyze the following bug report.
            First, classify the issue into one of the following types:
            1. "bug": Actual bugs (flaws in the system implementation).
            2. "programmer_error": Problems on the side of the programmer (misuse).
            3. "other": Requests or other issues (feature requests, questions, etc.).
            
            Second, IF the issue is a "bug", determine if it describes a **Memory Safety Issue**.
            If it is not a "bug", "is_memory_safety" must be false.
            
            Bug Report:
            Title: {title}
            Description: {desc}
            
            Task:
            Classify this bug. Answer with JSON format:
            {json_template}
            Only provide the JSON."""
            
            payload = {                                             
                "model": MODEL,                              
                "messages": [                                       
                    {"role": "system", "content": SYSTEM_PROMPT}, 
                    {"role": "user", "content": user_prompt}
                ]                                                   
            }
            
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            output = {                                                                  
                "file": bug_file,                                                       
                "classification": json.loads(content) if "{" in content else content
            }
            if isinstance(output["classification"], str):
                 try:
                     output["classification"] = json.loads(output["classification"])
                 except:
                     pass
                     
            print(json.dumps(output))
            return output

        except Exception as e:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_file, f) for f in files]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(files)):
            future.result()

run_all:
    #!/usr/bin/env bash
    set -e
    mkdir -p dataset
    
    for dbms in "LevelDB" "DuckDB" "Redis" "RocksDB"; do
        START=$(date +%s)
        echo "--------------------------------------------------"
        echo "Processing $dbms"
        echo "--------------------------------------------------"
        
        if ! ls {{output_dir}}/$dbms/*.json >/dev/null 2>&1; then
            echo "No files found for $dbms."
            continue
        fi
        
        matches_str=$(just -f {{bugs_dir}}/bugs.just search_bugs "$dbms")
        if [ -z "$matches_str" ]; then
            echo "[]" > dataset/matches_${dbms}.json
        else
            echo "$matches_str" | jq -R . | jq -s . > dataset/matches_${dbms}.json
        fi

        for rep in 1 2 3; do
            outfile="dataset/${dbms}_rep${rep}.json"
            just -f {{bugs_dir}}/bugs.just classify_bugs {{output_dir}}/$dbms/*.json > "$outfile"
        done

        END=$(date +%s)
        DIFF=$((END-START))
        T_HOURS=$((DIFF / 3600))
        T_MINS=$(((DIFF % 3600) / 60))
        T_SECS=$((DIFF % 60))
        printf "Time taken for %s: %02d:%02d:%02d\n" "$dbms" $T_HOURS $T_MINS $T_SECS
    done

analyse_results dbms="LevelDB":
    #!/usr/bin/env bash
    python3 {{bugs_dir}}/analyse_results.py "{{dbms}}"
    