# Memory Tagging Extension 


# Benchmark Tool

This tool helps perform benchmarks on remote machines in three steps: **copy**, **build**, and **analyse**. Follow the steps below to ensure proper execution.

## Steps

1. **Copy Data**  
    Run the `copy` subcommand to copy all relevant data from the repository to the remote machine.  
    ```bash
    python benchmark-tool.py --user <username> --host <hostname> copy
    ```
2. **Build Data Structure**  
    Run the `build` subcommand to build a specific data structure for testing on the remote machine. Specify the data structure using the `--datastructure` option. 
    ```bash
    python benchmark-tool.py --user <username> --host <hostname> build --datastructure <datastructure_name>
    ```

3. **Analyse Data Structure**  
    Run the analyse subcommand to `analyze` the performance of a specific data structure on the remote machine. Specify the data structure using the `--datastructure` option. 
    ```bash
    python benchmark-tool.py --user <username> --host <hostname> analyse --datastructure <datastructure_name>
    ```
