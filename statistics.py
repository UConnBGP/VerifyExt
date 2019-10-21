#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module performs statistical analysis of the Verifier Class.

The verifier class generates data for the verification of a single Autonomous System(AS).
"""

__version__ = '0.1'
__author__ = 'James Breslin'

import sys
import shutil
import csv
import numpy as np
import scipy as sp

from os import path
from datetime import datetime

class Trial:
    def __init__(self):
        self.verifiable = []
        self.mrt_len = []
        self.ext_len = []
        self.kcomp_success = []
        self.kcomp_failure = []
        self.prefix_f = []
        self.origin_f = []
        self.traceback_f = []
        self.compare_f = []
        self.mrt_f = []
        self.inference_f = []
        self.levenshtein_avg = []

    def add_verifiable(self, num):
        self.verifiable.append(num)

    def add_mrt_len(self, num):
        self.mrt_len.append(num)

    def add_ext_len(self, num):
        self.ext_len.append(num)

    def add_kcomp_s(self, lst):
        self.kcomp_success.append(lst)

    def add_kcomp_f(self, lst):
        self.kcomp_failure.append(lst)

    def add_prefix_f(self, num):
        self.prefix_f.append(num)

    def add_origin_f(self, num):
        self.origin_f.append(num)

    def add_traceback_f(self, num):
        self.traceback_f.append(num)

    def add_compare_f(self, num):
        self.compare_f.append(num)

    def add_mrt_f(self, num):
        self.mrt_f.append(num)

    def add_inference_f(self, num):
        self.inference_f.append(num)

    def add_levenshtein_avg(self, num):
        self.levenshtein_avg.append(num)

""" Handles loading data into the Trial objects"""
class Switch(object):
    def num_to_method(self, num, trial, row):
        """Dispatch function"""
        method_name = 'n_' + str(num)
        method = getattr(self, method_name)
        method(trial, row)
    
    def n_0(self, trial, row):
        pass

    def n_1(self, trial, row):
        trial.add_verifiable(row[1])

    def n_2(self, trial, row):
        trial.add_mrt_len(row[0])
    
    def n_3(self, trial, row):
        trial.add_ext_len(row[0])
    
    def n_4(self, trial, row):
        trial.add_kcomp_s(list(row))
    
    def n_5(self, trial, row):
        trial.add_kcomp_f(list(row))

    def n_6(self, trial, row):
        trial.add_prefix_f(row[0])

    def n_7(self, trial, row):
        trial.add_origin_f(row[0])
    
    def n_8(self, trial, row):
        trial.add_traceback_f(row[0])
    
    def n_9(self, trial, row):
        trial.add_compare_f(row[0])

    def n_10(self, trial, row):
        trial.add_levenshtein_avg(row[0])

def open_file(fn):
    """Opens a given file if it exists."""
    if (path.exists(fn)):
        f = open(fn, "r+")
        return f
    else:
        print("%s missing" % sys.argv[1], file=sys.stderr)
        sys.exit(-1)

def load_data(trial, f):
    """Loads data of a given file into a given trial."""
    line_n = 0
    s = Switch()
    with f as csvFile:
        readCSV = csv.reader(csvFile, delimiter=',')
        for row in readCSV:
            s.num_to_method(line_n%11, trial, row)
            line_n += 1

def main():
    """Generates plots for a given set of trials."""

    if len(sys.argv) != 4:
        print("Usage: statitics.py <full_verified.csv> <origin_verified.csv> <no_prop_verified.csv>", file=sys.stderr)
        sys.exit(-1)
   
    fn1 = "results/" + sys.argv[1]
    fn2 = "results/" + sys.argv[2]
    fn3 = "results/" + sys.argv[3]
    
    print(datetime.now().strftime("%c") + ": Loading data.")
    
    # Data for normal verification runs
    full_ext = Trial()
    full_file = open_file(fn1)
    load_data(full_ext, full_file)
    full_file.close()
    
    # Data for origin only verification runs
    origin_only = Trial()
    origin_file = open_file(fn2)
    load_data(origin_only, origin_file)
    origin_file.close()
    
    # Data for MRT no propagation verfication runs
    mrt_no_prop = Trial()
    no_prop_file = open_file(fn3)
    load_data(mrt_no_prop, no_prop_file)
    no_prop_file.close()

    print(datetime.now().strftime("%c") + ": Processing data.")

if __name__ == "__main__":
    main()
