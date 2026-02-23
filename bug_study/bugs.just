bugs_dir := source_dir()
bugs_output_dir := "/scratch/dimitrios/memsafedb/bug_study/memsafedb_bugs/"
cve_dir := "/scratch/dimitrios/memsafedb/bug_study/cve/"
dockerfile_path := bugs_dir + "/Dockerfile"

# Global date filtering
start_date_setting := "2015-01-01"
end_date_setting := "2025-12-31"

# Memory safety keywords
keywords := "buffer overflow|buffer-overflow|bufferoverflow|buffer overrun|buffer-overrun|buffer underflow|buffer-underflow|buffer underrun|\
out of bounds|out-of-bounds|OOB|OOBR|OOBW|array bounds|off-by-one|off by one|offbyone|\
stack overflow|stack-overflow|stackoverflow|stack smashing|stack-smashing|heap overflow|heap-overflow|heapoverflow|\
integer overflow|integer-overflow|integer underflow|\
null pointer dereference|null-pointer dereference|nullptr dereference|null dereference|\
double free|double-free|doublefree|multiple free|free after free|\
use after free|use-after-free|useafterfree|UAF|stack use after|heap use after|\
uninitialized memory|uninitialized variable|uninitialised|use of uninitialized|\
wild pointer|dangling pointer|dangling-pointer|dangling reference|\
memory safety|memory-safety|memory corruption|memory-corruption|heap corruption|stack corruption|memory error|\
invalid memory|illegal memory|invalid read|invalid write|invalid memory access|illegal memory access|\
segmentation fault|segfault|SIGSEGV|address sanitizer|ASLR"

# make the keywords fuzzy
default:
    @just --list

# ========================================
#  llama-server Recipes
# ========================================

# Model configuration (Options: gpt-oss, llama4, llama3)
models_dir := "/scratch/dimitrios/memsafedb/models"
model_type := "gpt-oss"

model_repo := if model_type == "gpt-oss" {
    "unsloth/gpt-oss-120b-GGUF"
} else if model_type == "llama4" {
    "glogwa68/Llama-4-scout-GGUF"
} else {
    "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
}

model_name_pattern := if model_type == "gpt-oss" {
    "Q4_K_M/*.gguf"
} else if model_type == "llama4" {
    "Llama-4-Scout-4bit-Q4_K_M.gguf"
} else {
    "Meta-Llama-3.1-8B-Instruct-Q8_0.gguf"
}

model_name := if model_type == "gpt-oss" {
    "Q4_K_M/gpt-oss-120b-Q4_K_M-00001-of-00002.gguf"
} else if model_type == "llama4" {
    "Llama-4-Scout-4bit-Q4_K_M.gguf"
} else {
    "Meta-Llama-3.1-8B-Instruct-Q8_0.gguf"
}

ctx_size := "131072"
batch_size := "2048"
parallel := "16"
gpu_layers := "99"

download_model:
    #!/usr/bin/env bash
    set -e
    mkdir -p {{ models_dir }}
    model_path="{{ models_dir }}/{{ model_name }}"
    if [ -f "$model_path" ]; then
        echo "Model already exists at $model_path"
    else
        echo "Downloading {{ model_name }} from Hugging Face..."
        huggingface-cli download {{ model_repo }} --include "{{ model_name_pattern }}" --local-dir {{ models_dir }}
        echo "Model downloaded to $model_path"
    fi

build_docker:
    docker build -t llama-server-cuda -f {{ bugs_dir }}/Dockerfile {{ bugs_dir }} #> /dev/null 2>&1

launch_server: download_model build_docker
    docker run -d --device nvidia.com/gpu=all \
        -v {{ models_dir }}:/models \
        -p 8080:8080 \
        llama-server-cuda \
        --model /models/{{ model_name }} \
        --n-gpu-layers {{ gpu_layers }} \
        --ctx-size {{ ctx_size }} \
        --batch-size {{ batch_size }} \
        --parallel {{ parallel }} \
        --cont-batching \
        --host 0.0.0.0 > /dev/null 2>&1

kill_server:
    docker stop $(docker ps -q --filter ancestor=llama-server-cuda)

# ========================================
#  Bug Classification Recipes

# ========================================
scrape_bugs:
    #!/usr/bin/env bash
    mkdir -p {{ bugs_output_dir }}
    rm -rf {{ bugs_output_dir }}/*
    python3 scrape_bugs.py --output "{{ bugs_output_dir }}"

search_bugs dbms="":
    #!/usr/bin/env bash
    find "{{ bugs_output_dir }}/{{ dbms }}" -maxdepth 1 -name "*.json" -type f -print0 2>/dev/null | \
        xargs -0 -r grep -lEi "{{ keywords }}" || true

classify_bugs +files="":
    #!/usr/bin/env python3
    import sys
    import json
    import requests
    import os
    import re
    import concurrent.futures
    from datetime import datetime, timezone

    # Read files from arguments if provided, otherwise from stdin
    args_files = "{{ files }}".strip()
    if args_files:
        files = args_files.split()
    else:
        # Read from stdin (null-separated from xargs -0)
        files = sys.stdin.read().strip('\0').split('\0')
        files = [f for f in files if f]  # Remove empty strings

    start_date_str = "{{ start_date_setting }}"
    end_date_str = "{{ end_date_setting }}"
    start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc) if start_date_str else None
    end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc) if end_date_str else None

    API_URL = "http://localhost:8080/v1/chat/completions"
    MODEL = "{{ model_name }}"

    SYSTEM_PROMPT = "You are an expert software security researcher specializing in database systems."

    def process_file(bug_file):
        try:
            with open(bug_file, 'r') as f:
                data = json.load(f)
            
            # Date filtering
            created_at_str = data.get('created_at') or data.get('raw', {}).get('created_at')
            if created_at_str:
                try:
                    # Simplify: Assume UTC
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at.tzinfo is None:
                         created_at = created_at.replace(tzinfo=timezone.utc)
                    else:
                         created_at = created_at.astimezone(timezone.utc)

                    if start_date and created_at < start_date:
                        return None
                    if end_date and created_at > end_date:
                        return None

                except ValueError:
                    pass

            title = data.get('title', '')
            desc = data.get('body', '')

            # Truncate long descriptions to prevent payload size issues
            MAX_DESC_LENGTH = 12000
            if len(desc) > MAX_DESC_LENGTH:
                desc = desc[:MAX_DESC_LENGTH] + "\n... [TRUNCATED - description too long]"

            json_template = '''{
            "issue_type": "bug/programmer_error/other",
            "is_memory_safety": true/false,
            "implication": "data_loss/data_corruption/incorrect_query_results/system_crash/resource_exhaustion/concurrency_hazard/transaction_violation/durability_violation/replication_inconsistency/denial_of_service/none",
            "confidence": "high/medium/low",
            "reason": "Brief explanation..."
            }'''

            user_prompt = f"""Analyze the following bug report.
            First, classify the issue into one of the following types:
            1. "bug": Actual bugs (flaws in the system implementation).
            2. "programmer_error": Problems on the side of the programmer (misuse).
            3. "other": Requests or other issues (feature requests, questions, etc.).

            Second, IF the issue is a "bug", determine if it describes a **Memory Safety Issue**.
            If it is not a "bug", "is_memory_safety" must be false.

            Third, IF the issue is a "bug" AND you can determine the primary operational implication
            with HIGH confidence, classify it into exactly one of the following:
            - "data_loss": Data is permanently lost or unrecoverable.
            - "data_corruption": Stored data becomes physically or logically inconsistent.
            - "incorrect_query_results": Queries silently return wrong data (no crash).
            - "system_crash": The database process crashes, aborts, or panics.
            - "resource_exhaustion": Memory leak, disk/CPU saturation, connection pool depletion.
            - "concurrency_hazard": Deadlocks, race conditions, or isolation violations under concurrency.
            - "transaction_violation": ACID guarantees are broken (lost updates, dirty reads, etc.).
            - "durability_violation": Committed transactions are lost after a crash or restart.
            - "replication_inconsistency": Primary and replica data diverge or replication fails.
            - "denial_of_service": Server becomes unresponsive or hangs without crashing.
            - "none": No clear operational implication can be determined with high confidence,
                    or the issue is not a "bug".

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
                ],
                "max_tokens": 1024
            }

            # Validate payload size before sending
            payload_size = len(json.dumps(payload))
            if payload_size > 100000:  # 100KB limit
                print(f"Warning: Large payload ({payload_size} bytes) for {bug_file}", file=sys.stderr, flush=True)

            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']

            output = {                                                                  
                "file": bug_file,                                                       
                "classification": content
            }
            
            # Extract JSON block if present (helpful for reasoning models)
            if "{" in content:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        output["classification"] = json.loads(json_match.group(0))
                    except:
                        pass

            return output

        # Error handling with HTTP response details
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error processing {bug_file}: {e}", file=sys.stderr, flush=True)
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}", file=sys.stderr, flush=True)
            return None
        except Exception as e:
            print(f"Error processing {bug_file}: {e}", file=sys.stderr, flush=True)
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(process_file, f) for f in files]
        total = len(files)
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                print(json.dumps(result), flush=True)
            completed += 1
            if completed % 10 == 0:
                print(f"Progress: {completed}/{total}", file=sys.stderr, flush=True)

run_all_bugs:
    #!/usr/bin/env bash
    set -e
    mkdir -p {{ bugs_output_dir }}/bug_results

    for dbms in "RocksDB" "MongoDB" "ClickHouse" "CockroachDB" "MariaDB" "MySQL" "Redis"  "LevelDB"; do
        START=$(date +%s)
        echo "--------------------------------------------------"
        echo "Processing $dbms"
        echo "--------------------------------------------------"    

        json_count=$(find "{{ bugs_output_dir }}/$dbms" -maxdepth 1 -name "*.json" -type f 2>/dev/null | wc -l)
        if [ "$json_count" -eq 0 ]; then
            echo "No JSON files found for $dbms."
            continue
        fi
        echo "Found $json_count JSON files for $dbms"
        
        matches_str=$(just -f {{ bugs_dir }}/bugs.just search_bugs "$dbms")
        if [ -z "$matches_str" ]; then
            echo "[]" > {{ bugs_output_dir }}/bug_results/matches_${dbms}.json
        else
            echo "$matches_str" | jq -R . | jq -s . > {{ bugs_output_dir }}/bug_results/matches_${dbms}.json
        fi

        for rep in 1 2 3; do
            outfile="{{ bugs_output_dir }}/bug_results/${dbms}_rep${rep}.json"
            find "{{ bugs_output_dir }}/$dbms" -maxdepth 1 -name "*.json" -type f -print0 | \
                just -f {{ bugs_dir }}/bugs.just classify_bugs > "$outfile"
        done

        END=$(date +%s)
        DIFF=$((END-START))
        T_HOURS=$((DIFF / 3600))
        T_MINS=$(((DIFF % 3600) / 60))
        T_SECS=$((DIFF % 60))
        printf "Time taken for %s: %02d:%02d:%02d\n" "$dbms" $T_HOURS $T_MINS $T_SECS
    done

analyse_bug_results dbms="LevelDB":
    #!/usr/bin/env bash
    python3 {{ bugs_dir }}/analyse_bug_results.py "{{ dbms }}"

# ========================================
# CVE Classification Recipes
# ========================================

scrape_cves:
    #!/usr/bin/env bash
    python3 {{ bugs_dir }}/scrape_cves.py --output "{{ cve_dir }}"

search_cves dbms="":
    #!/usr/bin/env bash
    cve_list="{{ cve_dir }}/{{ dbms }}_cves"
    if [ ! -f "$cve_list" ]; then
        echo "No CVE list found for {{ dbms }} at $cve_list" >&2
        exit 1
    fi
    while IFS= read -r cve_path; do
        full_path="{{ cve_dir }}/${cve_path#./}"
        if [ -f "$full_path" ]; then
            if grep -qEi "{{ keywords }}" "$full_path"; then
                echo "$full_path"
            fi
        fi
    done < "$cve_list"

classify_cves +files="":
    #!/usr/bin/env python3
    import sys
    import json
    import requests
    import os
    import concurrent.futures
    from tqdm import tqdm
    from datetime import datetime, timezone

    files = "{{ files }}".split()

    start_date_str = "{{ start_date_setting }}"
    end_date_str = "{{ end_date_setting }}"
    start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc) if start_date_str else None
    end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc) if end_date_str else None

    API_URL = "http://localhost:8080/v1/chat/completions"
    MODEL = "{{ model_name }}"

    SYSTEM_PROMPT = "You are an expert software security researcher specializing in database systems and CVE analysis."

    def extract_cwe_info(data):
        """Extract CWE IDs and descriptions from CVE data."""
        cwes = []
        # Check cna.problemTypes
        cna = data.get('containers', {}).get('cna', {})
        for pt in cna.get('problemTypes', []):
            for desc in pt.get('descriptions', []):
                cwe_id = desc.get('cweId', '')
                cwe_desc = desc.get('description', '')
                if cwe_id or cwe_desc:
                    cwes.append(f"{cwe_id}: {cwe_desc}" if cwe_id else cwe_desc)
        # Check adp.problemTypes (CISA enrichment)
        for adp in data.get('containers', {}).get('adp', []):
            for pt in adp.get('problemTypes', []):
                for desc in pt.get('descriptions', []):
                    cwe_id = desc.get('cweId', '')
                    cwe_desc = desc.get('description', '')
                    if cwe_id and cwe_id not in str(cwes):
                        cwes.append(f"{cwe_id}: {cwe_desc}" if cwe_desc else cwe_id)
        return cwes

    def extract_affected(data):
        """Extract affected product and vendor info."""
        affected = []
        cna = data.get('containers', {}).get('cna', {})
        for a in cna.get('affected', []):
            vendor = a.get('vendor', 'n/a')
            product = a.get('product', 'n/a')
            if vendor != 'n/a' or product != 'n/a':
                affected.append(f"{vendor}/{product}")
        return affected

    def process_file(cve_file):
        try:
            with open(cve_file, 'r') as f:
                data = json.load(f)

            # Date filtering
            cve_meta = data.get('cveMetadata', {})
            date_published = cve_meta.get('datePublished')
            if date_published:
                try:
                    # Simplify: Assume UTC
                    cve_date = datetime.fromisoformat(date_published.replace('Z', '+00:00'))
                    if cve_date.tzinfo is None:
                        cve_date = cve_date.replace(tzinfo=timezone.utc)
                    else:
                        cve_date = cve_date.astimezone(timezone.utc)
                    
                    if start_date and cve_date < start_date:
                        return None
                    if end_date and cve_date > end_date:
                        return None

                except ValueError:
                    pass

            # Extract CVE ID from cveMetadata
            cve_id = data.get('cveMetadata', {}).get('cveId', 'Unknown')

            # Extract title (if available)
            cna = data.get('containers', {}).get('cna', {})
            title = cna.get('title', '')

            # Extract description from containers.cna.descriptions
            descriptions = cna.get('descriptions', [])
            desc = descriptions[0].get('value', '') if descriptions else ''

            # Truncate long descriptions
            MAX_DESC_LENGTH = 12000
            if len(desc) > MAX_DESC_LENGTH:
                desc = desc[:MAX_DESC_LENGTH] + "\n... [TRUNCATED - description too long]"

            if not desc:
                return None

            # Extract CWE info
            cwes = extract_cwe_info(data)
            cwe_str = ', '.join(cwes) if cwes else 'Not specified'

            # Extract affected products
            affected = extract_affected(data)
            affected_str = ', '.join(affected) if affected else 'Not specified'

            json_template = '''{
            "issue_type": "bug/programmer_error/other",
            "is_memory_safety": true/false,
            "implication": "data_loss/data_corruption/incorrect_query_results/system_crash/resource_exhaustion/concurrency_hazard/transaction_violation/durability_violation/replication_inconsistency/denial_of_service/none",
            "confidence": "high/medium/low",
            "reason": "Brief explanation..."
            }'''

            # Build prompt with all available info
            prompt_parts = [
                "Analyze the following CVE (Common Vulnerabilities and Exposures) report.",
                "First, classify the issue into one of the following types:",
                '1. "bug": Actual bugs (flaws in the database system implementation).',
                '2. "programmer_error": Problems on the side of the programmer (misuse).',
                '3. "other": Issues outside the database system, requests, or other misc issues (feature requests, questions, etc.).',
                "",
                "Second, IF the issue is a \"bug\", determine if it describes a **Memory Safety Issue**.",
                "If it is not a \"bug\", \"is_memory_safety\" must be false.",
                "",
                "Memory safety issues INCLUDE:",
                "- Buffer overflow, heap overflow, stack overflow",
                "- Use-after-free, double-free, dangling pointer",
                "- Null pointer dereference",
                "- Out-of-bounds read/write",
                "- Uninitialized memory access",
                "- Integer overflow ONLY if it leads to memory corruption",
                "",
                "Memory safety issues DO NOT INCLUDE:",
                "- SQL injection, XSS, CSRF (these are injection/logic bugs)",
                "- Authentication bypass, privilege escalation (unless memory-related)",
                "- Denial of service through resource exhaustion (unless memory corruption)",
                "- Logic errors, race conditions (unless causing memory corruption)",
                "",
                "Third, IF the issue is a \"bug\" AND you can determine the primary operational implication",
                "with HIGH confidence, classify it into exactly one of the following:",
                '- "data_loss": Data is permanently lost or unrecoverable.',
                '- "data_corruption": Stored data becomes physically or logically inconsistent.',
                '- "incorrect_query_results": Queries silently return wrong data (no crash).',
                '- "system_crash": The database process crashes, aborts, or panics.',
                '- "resource_exhaustion": Memory leak, disk/CPU saturation, connection pool depletion.',
                '- "concurrency_hazard": Deadlocks, race conditions, or isolation violations under concurrency.',
                '- "transaction_violation": ACID guarantees are broken (lost updates, dirty reads, etc.).',
                '- "durability_violation": Committed transactions are lost after a crash or restart.',
                '- "replication_inconsistency": Primary and replica data diverge or replication fails.',
                '- "denial_of_service": Server becomes unresponsive or hangs without crashing.',
                '- "none": No clear operational implication can be determined with high confidence,',
                '        or the issue is not a "bug".',
                "",
                "CVE REPORT:",
                f"CVE ID: {cve_id}",
            ]
            
            if title:
                prompt_parts.append(f"Title: {title}")
            
            prompt_parts.append(f"CWE (Weakness Type): {cwe_str}")
            prompt_parts.append(f"Affected Product: {affected_str}")
            prompt_parts.append(f"Description: {desc}")
            prompt_parts.extend([
                "",
                "TASK:",
                "Classify this CVE. Answer with JSON format:",
                json_template,
                "Only provide the JSON."
            ])

            user_prompt = '\n'.join(prompt_parts)

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
            content = result['choices'][0]['message']['content'].strip()

            # Strip markdown code blocks if present
            import re
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            # Try to extract JSON from content
            classification = content
            try:
                # Find first { and last }
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    json_str = content[start:end+1]
                    # Fix Python-style booleans/None to JSON-style
                    json_str = json_str.replace(': True', ': true').replace(':True', ':true')
                    json_str = json_str.replace(': False', ': false').replace(':False', ':false')
                    json_str = json_str.replace(': None', ': null').replace(':None', ':null')
                    classification = json.loads(json_str)
            except json.JSONDecodeError:
                pass  # Keep as string if parsing fails

            output = {                                                                  
                "file": cve_file,
                "cve_id": cve_id,
                "classification": classification
            }

            print(json.dumps(output), flush=True)
            return output

        except Exception as e:

            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(process_file, f) for f in files]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(files)):
            future.result()

run_all_cves:
    #!/usr/bin/env bash
    set -e
    mkdir -p {{ cve_dir }}/cve_results

    # for dbms in "redis"; do
    for dbms in "mysql" "sqlite" "mariadb" "redis" "leveldb" "rocksdb" "duckdb" "ladybug" "postgresql" "mongodb" "memcached" "influxdb" "redshift"; do
        START=$(date +%s)
        echo "--------------------------------------------------"
        echo "Processing CVEs for $dbms"
        echo "--------------------------------------------------"

        cve_list="{{ cve_dir }}/${dbms}_cves"
        if [ ! -f "$cve_list" ]; then
            echo "No CVE list found for $dbms at $cve_list"
            continue
        fi

        # Build list of CVE file paths
        cve_paths=""
        while IFS= read -r cve_path; do
            full_path="{{ cve_dir }}/${cve_path#./}"
            if [ -f "$full_path" ]; then
                cve_paths="$cve_paths $full_path"
            fi
        done < "$cve_list"

        if [ -z "$cve_paths" ]; then
            echo "No CVEs found for $dbms."
            continue
        fi

        # Search for memory safety keywords
        matches_str=$(just -f {{ bugs_dir }}/bugs.just search_cves "$dbms")
        if [ -z "$matches_str" ]; then
            echo "[]" > {{ cve_dir }}/cve_results/matches_${dbms}_cve.json
        else
            echo "$matches_str" | jq -R . | jq -s . > {{ cve_dir }}/cve_results/matches_${dbms}_cve.json
        fi

        for rep in 1 2 3; do
            outfile="{{ cve_dir }}/cve_results/${dbms}_cve_rep${rep}.json"
            just -f {{ bugs_dir }}/bugs.just classify_cves $cve_paths > "$outfile"
        done

        END=$(date +%s)
        DIFF=$((END-START))
        T_HOURS=$((DIFF / 3600))
        T_MINS=$(((DIFF % 3600) / 60))
        T_SECS=$((DIFF % 60))
        printf "Time taken for %s CVEs: %02d:%02d:%02d\n" "$dbms" $T_HOURS $T_MINS $T_SECS
    done

analyse_cve_results dbms="all":
    #!/usr/bin/env bash
    if [ "{{ dbms }}" = "all" ]; then
        for db in "mysql" "sqlite" "mariadb" "redis" "leveldb" "rocksdb" "duckdb" "ladybug" "postgresql" "mongodb" "memcached" "influxdb" "redshift"; do
            python3 {{ bugs_dir }}/analyse_cve_results.py "$db"
        done
    else
        python3 {{ bugs_dir }}/analyse_cve_results.py "{{ dbms }}"
    fi
