#!/usr/bin/env python3
"""
    Benchmarks Interface
"""
class IBenchmarks(object):
    def perform_benchmark(self, libso_path: str, output_path: str):
        raise NotImplemented()

    def perform_perf(self, libso_path: str, output_path: str):
        raise NotImplemented()
