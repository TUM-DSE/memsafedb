# Cache size

With this experiment we constructe a workload in which we are able to estimate the size of the different caches (e.g. L1, L2, ...). For this we initialise different sized arrays in which we will access every element multiple times, furthere we will do a total access of X on every array undependent its size. If after the first full iteration of the array we will start again at the beginning, if the full array fits in the cache the access will now take less time than the first iteration, if not, certain part will be thrown away, and we have to fetch the data again, this will result in worse perfromance. Because we are doing always the same amount of work (aka the steps we are doing) the total work/memory access will stay the same, and only the time to load data into cache will be relevant.


