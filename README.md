# CHERI-DB - Evaluation Framework

made with love in the heart of Bavaria by an enthusiastic TUM team.

## TODO: The documentation will be completed over time.

## Configuration File
The functionality of the framework relies entirely on the configuration file provided. The format of
the configuration file is as follows:

```
{
    'target': {
        'so_name': 'so_path'
    },
    "mbench_1": {
        "__comment": "the threadnum should be a list [] - usecases",
        "threadnum": [1, 2, 4],
        "capacity": 100000,
        "repetitions": 5,
        "perf": {
            "do_profiling": true,
            "repetitions": 1
        },

        "granularity": 25,
        "output_path": "output/mbench_1",
    
        "__distribution_types": "[uniform, zipfian]",
        "distribution": "zipfian",
    
        "performfill": {
            "filling_factor": 0.95
        },
    
        "performquery": {
            "query_factor":   0.7,
            "success_factor": 0.5
        },
    
        "performdeletion": {
            "deletion_factor":  0.7,
            "success_factor":   0.5
        }
    }, 
    "ycsb": {
        "repetitions": 5,
        "output_path": "output/ycsb",

        "__comment": "to execute load phase before each workload",
        "phase_load": true,

        "workloads": {
            "workloada": {},
            "workloadb": {}
        }
    }
}
```
where:
- target - states which structures will be evaluated
    - so_name - the structure name (or a generic name, used to save the data in the output folder).
    - so_path - the absolute (or relative) path to the .so - binary definition.
- mbench_1 - the microbenchmark (not really micro, as complexity is similar to ycsb)
    - threadnum    - a list of ints defining new usescases based on thread numbers.
    - capacity     - the datastructure capacity (initial capacity).
    - repetitions  - stating the number of repetitions per usacase. the results will be the average of all repetitions.
    - perf         - used for perf (TODO: write the documentation)
    - granularity  - the granularity used for the axis on graphs (bigger - more intermediary points, smaller - higher abstraction).
    - output_path  - the location for the output data (coupled together with `so_name`).
    - distribution - defining how the distribution used for the data inserted in the table.
    - performfill   - usecase - 1 -
        - filling_factor - what percentage of `capacity` will be inserted into the table.
    - performquery - usecase - 2 -
        - query_factor   - the percentage of `capacity` used to query.
        - success_factor - the percetange of keys exiting into the table.
    - performdeletion -  usecase - 3 -
        - deletion_factor - the percentage of `capacity` used to delete.
        - success_factor  - the percentage of keys existing into the table.
- ycsb - the workload ycsb
    - repetitions - stating the number of repetitions per usacase. the results will be the average of all repetitions.
    - output_path - the location for the output data (coupled together with `so_name`).
    - workloads   - the workloads to be performed
        - workload{a, b, c} (or generic name) - please ref. to the YCSB documenation for the parameters details.

