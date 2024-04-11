#!/bin/sh

$(cd ./CLHT && make && make clht_lb clht_lb_res clht_lf clht_lf_res)
$(make all)
