#!/usr/bin/env python3

def do_average(lvals: list[list[int]]) -> list[int]:
    """
        all lists must be equal in size
    """
    size    = min([len(lval) for lval in lvals])
    average = [0] * size
    for index in range(size):
        average[index] += sum([lval[index] for lval in lvals])
        average[index] /= len(lvals)
    return average
