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
#import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import scipy.stats as sts
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
        trial.add_verifiable(int(row[1]))

    def n_2(self, trial, row):
        trial.add_mrt_len(float(row[0]))
    
    def n_3(self, trial, row):
        trial.add_ext_len(float(row[0]))
    
    def n_4(self, trial, row):
        trial.add_kcomp_s(map(int, list(row)))
    
    def n_5(self, trial, row):
        trial.add_kcomp_f(map(int, list(row)))

    def n_6(self, trial, row):
        trial.add_prefix_f(int(row[0]))

    def n_7(self, trial, row):
        trial.add_origin_f(int(row[0]))
    
    def n_8(self, trial, row):
        trial.add_traceback_f(int(row[0]))
    
    def n_9(self, trial, row):
        trial.add_compare_f(int(row[0]))

    def n_10(self, trial, row):
        trial.add_levenshtein_avg(float(row[0]))

def check_file(fn):
    """Opens a given file if it exists."""
    if (path.exists(fn)):
        return fn
    else:
        print("%s missing" % fn, file=sys.stderr)
        sys.exit(-1)

def load_data(trial, fn):
    """Loads data of a given file into a given trial."""
    line_n = 0
    s = Switch()
    with open(check_file(fn), "r+") as csvFile:
        readCSV = csv.reader(csvFile, delimiter=',')
        for row in readCSV:
            s.num_to_method(line_n%11, trial, row)
            line_n += 1

def plot_ld(full, origin_o, no_prop):
    N = full.size
    ind = np.arange(N)    # the x locations for the groups

    p1 = plt.scatter(ind, full, label="Full")
    p2 = plt.scatter(ind, origin_o, label="Origin Only")
    p3 = plt.scatter(ind, no_prop, label="MRT No Propagation")

    plt.xlabel('%d Collectors' % N)
    plt.title('Levenshtein Distance')
    plt.legend()

    plt.show()

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
    load_data(full_ext, fn1)
    
    # Data for origin only verification runs
    origin_only = Trial()
    load_data(origin_only, fn2)
    
    # Data for MRT no propagation verfication runs
    mrt_no_prop = Trial()
    load_data(mrt_no_prop, fn3)

    print(datetime.now().strftime("%c") + ": Processing data.")

    full_lev_d = np.array(full_ext.levenshtein_avg)
    oo_lev_d = np.array(origin_only.levenshtein_avg)
    np_lev_d = np.array(mrt_no_prop.levenshtein_avg)
    
    
    ttest_res = sts.ttest_ind(full_lev_d, oo_lev_d, equal_var=False)
    print("Full vs. Origin Only T-Test")
    print(ttest_res)
    
    ttest_res = sts.ttest_ind(full_lev_d, np_lev_d, equal_var=False)
    print("Full vs. No Propagation T-Test")
    print(ttest_res)

    plot_ld(full_lev_d, oo_lev_d, np_lev_d)


if __name__ == "__main__":
    main()
