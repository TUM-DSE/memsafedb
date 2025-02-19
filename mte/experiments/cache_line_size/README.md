# Determining the Cache Line Size of MTE Tags
## Introduction

In this experiment, we aim to determine the cache line size for MTE tags. To achieve this, we use a well-known methodology for measuring cache line size: iterating over an array with different stride sizes.

A stride refers to the step size between consecutive accesses in memory. For example, a stride of 1 means accessing every byte, a stride of 2 accesses every second byte, and so on. By running this experiment, we expect to observe a drop in performance at a certain stride size. This drop indicates the size of a cache line because when data is accessed, an entire cache line is loaded into the cache. As long as accesses remain within the same cache line, no additional memory fetches are needed. However, once the stride size exceeds the cache line size, accesses start skipping entire cache lines, leading to performance degradation. This happens because:

- The benefits of spatial and temporal locality are lost.
- The prefetcher, despite its deterministic behavior, provides little advantage in this scenario.


## First Approach

Following the methodology outlined above, the first approach iterates over the array only once. This means that a stride of 1 performs twice the number of accesses compared to a stride of 2, and a stride of 2 does twice the work of a stride of 4, and so on.

While this approach provides insight into cache behavior, it introduces inconsistencies. Since different strides result in varying amounts of work, comparing performance across different stride sizes becomes difficult.


## Second Approach

To address this issue, we modified the experiment to ensure that each run with the same stride performs the same amount of work. Instead of iterating once over the array, we adjust the workload based on the array length so that an array of length x results in x operations.

This refinement initially produced results that aligned with expectations. However, one major issue emerged: when using different array lengths, performance drops occurred at cache size boundaries. This effect made it difficult to isolate the cache line size. While the performance degradation is an expected consequence of cache hierarchy behavior, it interferes with obtaining a stable measurement of cache line size.
Final Refinement

To obtain a clearer and more stable measurement, we refined the experiment further:

- Exclude array sizes that fit within the cache. This prevents interference from cache size effects.
- Regardless of the stride size, we ensure the same amount of work by making the number of operations dependent on the array size—meaning that for an array of size x, we perform x operations.

