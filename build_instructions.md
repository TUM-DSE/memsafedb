# How to build?

## Structures

### CLHT (LF, LB)

Inside the `CLHT\externa` are two submodules: `ssmem` and `sspfd`.

#### SSMEM
```
  cd CLHT/external/ssmem
  gmake -f Makefile_ace
  cp libssmem.a ../lib
  cp include/ssmem.h ../include
  cd ../../..
```
You can run the tests `ssmem_test` to check if the lib works (it must work).

#### SSPDF
```
  cd CLHT/external/sspfd
  gmake -f Makefile libsspfd.a
  cp libsspfd.a ../lib
  cp sspfd.h ../include
  cd ../../..
```

Build CLHT directory
```
  cd CLHT && gmake -f Makefile_ace clht_lb clht_lf
```

Test CLHT:
```
  # lock base approach
  ./clht_lb

  # lock free approach !!! the -b (buckets) must be a power of 2!!!!
  ./clht_lf -b 1024
```

### oneTBB 

Choosing the build type - release. For the hashtable, only `tbb` must be built from the entire project.
```
  cmake .
  make tbb  # TBB structures
```

Source the path to be used during evaluation. The TBB project provides the vars after building the component.
```
  source <resulting_path>/vars.sh
```

!!!! TBB is a total nightmare. If something is not working, just shut down the SSH and re-establish the connection (some values get cached, stored / sessions).

## Building structures

In `structures`, run:

```
gmake -f Makefile_ace
```

## Other

For debugging, just use the classical approach - adding the flags `-g -O0`. Do not build it in "DEBUG TYPE" (if you do, you will experience the worst nightmare in GDB.
