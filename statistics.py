#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module performs statistical analysis of the output of the driver script.

The driver generates data for the verification of a set of AS BGP Collectors.
"""

__version__ = '0.2'
__author__ = 'James Breslin'

import sys
import shutil
import csv
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as sts
from scipy import mean
from os import path
from datetime import datetime

""" The Trial_Set stores one set of data for a single trial.

    Each Trial consists of three sets of data;
        1) Full Extrapolation
        2) Origin Only Propagation
        3) MRT No Propagation
"""
class Trial_Set:
    def __init__(self):
        self.asns = []
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
        self.levenshtein_d = []

    def add_asn(self, asn):
        self.asns.append(asn)

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

    def add_levenshtein_d(self, lst):
        self.levenshtein_d.append(lst)

""" Handles loading data into the Trials objects."""
class Switch(object):
    def num_to_method(self, num, trial, row):
        """Dispatch function"""
        method_name = 'n_' + str(num)
        method = getattr(self, method_name)
        method(trial, row)
    
    def n_0(self, trial, row):
        #TODO remove string slice
        trial.add_asn(str(row[0]))
        #trial.add_asn(str(row[0][:-5]))

    def n_1(self, trial, row):
        trial.add_verifiable(int(row[1]))

    def n_2(self, trial, row):
        trial.add_mrt_len(float(row[0]))
    
    def n_3(self, trial, row):
        trial.add_ext_len(float(row[0]))
    
    def n_4(self, trial, row):
        trial.add_kcomp_s(list(map(int, row)))
    
    def n_5(self, trial, row):
        trial.add_kcomp_f(list(map(int, row)))

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

    def n_11(self, trial, row):
        trial.add_levenshtein_d(list(map(int, row)))

def average(lst):
    return sum(lst) / len(lst)

def check_file(fn):
    """Returns the given filename if the file exists."""
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
            s.num_to_method(line_n%12, trial, row)
            line_n += 1

def calc_std(lst_of_lsts):
    """Generates a numpy array storing standard deviations for each sublist."""
    std_lst = []
    for lst in lst_of_lsts:
        std_lst.append(np.std(lst))
    return np.array(std_lst)

def conf_int(lst):
    confidence = 0.95
    n = len(lst)
    m = mean(lst)
    std_err = sts.sem(lst)
    h = std_err * sts.t.ppf((1 + confidence) / 2, n - 1)
    return h

def calc_ci(lst_of_lsts):
    """Generates a numpy array storing standard deviations for each sublist."""
    std_lst = []
    for lst in lst_of_lsts:
        std_lst.append(conf_int(lst))
    return np.array(std_lst)

def kcomp_to_arr(kc_lists, max_p_l):
    """ Generates a numpy array of kcomp averages from a list of lists.
    
        The Kth position in the returned array is the average of all Kth position values.
    """
    kc_avg = []
    kc_ci = []
    kc_tp = np.transpose(kc_lists)
    sample_sz = len(kc_lists)
    for lst in kc_tp:
        kc_avg.append(average(lst))
        kc_ci.append(conf_int(lst))
    return (np.array(kc_avg[:max_p_l]), np.array(kc_ci[:max_p_l])) 

def ttest_ld(full_ext, origin_only, mrt_no_prop):
    """Performs a ttest for the average levenshtein distance."""
    full_lev_d = np.array(full_ext.levenshtein_avg)
    oo_lev_d = np.array(origin_only.levenshtein_avg)
    np_lev_d = np.array(mrt_no_prop.levenshtein_avg)
    
    ttest_res = sts.ttest_ind(full_lev_d, oo_lev_d, equal_var=False)
    print("Full vs. Origin Only T-Test")
    print(ttest_res)
    
    ttest_res = sts.ttest_ind(full_lev_d, np_lev_d, equal_var=False)
    print("Full vs. No Propagation T-Test")
    print(ttest_res)

def ttest_kc(full_ext, origin_only, mrt_no_prop):
    """Performs a ttest for the average kcompare correctness."""
    print("Full vs. Origin Only T-Test")
    print("Full vs. No Propagation T-Test")

def plot_ld(full, origin_o, no_prop):
    """Generates a plot for average levenshtein distance."""
    
    # sort by full path ext
    zipped = zip(full.levenshtein_avg, origin_o.levenshtein_avg, no_prop.levenshtein_avg, full.asns)
    sort = sorted(zipped, key=lambda x: x[0])
    unzipped = list(zip(*sort))

    f_lev_d = np.array(unzipped[0])
    oo_lev_d = np.array(unzipped[1])
    np_lev_d = np.array(unzipped[2])
    asn_index = np.array(unzipped[3])
    print(asn_index)

    f_ci = calc_ci(full.levenshtein_d)
    oo_ci = calc_ci(origin_o.levenshtein_d)
    np_ci = calc_ci(no_prop.levenshtein_d)

    N = f_lev_d.size
    f_ind = np.arange(1,N+1) # the x collectors for the trial
    #oo_ind = np.arange(1.1,N+1.1, 1) # the x collectors for the trial
    #np_ind = np.arange(1.2,N+1.2, 1) # the x collectors for the trial

    p1 = plt.errorbar(f_ind, f_lev_d, yerr=f_ci, fmt='o', label="Full")
    p2 = plt.errorbar(f_ind, oo_lev_d, yerr=oo_ci, fmt='o', label="Origin Only")
    p3 = plt.errorbar(f_ind, np_lev_d, yerr=np_ci, fmt='o', label="MRT No Propagation")

    plt.xlabel('%d Collectors' % N)
    plt.title('Average Levenshtein Distance')
    plt.xticks(f_ind, asn_index, rotation='vertical')
    plt.legend()

    plt.show()

def plot_kc(full, origin_o, no_prop, f=False):
    """Generates a plot for average k-compare correctness."""
    # Data to plot
    l = 6   # max path length
    if (f == False):
        name = 'K Compare Success'
        f_kc, f_std = kcomp_to_arr(full.kcomp_success, l)
        oo_kc, oo_std = kcomp_to_arr(origin_o.kcomp_success, l)
        np_kc, np_std = kcomp_to_arr(no_prop.kcomp_success, l)
    else:
        name = 'K Compare Failure'
        f_kc, f_std = kcomp_to_arr(full.kcomp_failure, l)
        oo_kc, oo_std = kcomp_to_arr(origin_o.kcomp_failure, l)
        np_kc, np_std = kcomp_to_arr(no_prop.kcomp_failure, l)

    N = f_kc.size
    ind = np.arange(N) # the n hops for the trial
    
    # Create plot
    fig, ax = plt.subplots()
    b_width = .25
    b_opacity = .8

    #p1 = plt.errorbar(f_ind, f_kc, yerr=f_std, fmt='o', label="Full")
    p1 = plt.bar(ind, f_kc, b_width, yerr=f_std, label="Full")
    p2 = plt.bar(ind+b_width, oo_kc, b_width, yerr=oo_std, label="Origin Only")
    p3 = plt.bar(ind+b_width*2, np_kc, b_width, yerr=np_std, label="MRT No Propagation")

    plt.xlabel('Kth Hop')
    plt.title(name)
    plt.legend()

    plt.show()

def plot_class_fail(full, origin_o, no_prop):
    """Generates a plot for average k-compare correctness."""
    # Data to plot
    name = 'Failure Classification'
    
    f_prefix = np.array(full.prefix_f)
    f_origin = np.array(full.origin_f)
    f_compare = np.array(full.compare_f)
    
    oo_prefix = np.array(origin_o.prefix_f)
    oo_origin = np.array(origin_o.origin_f)
    oo_compare = np.array(origin_o.compare_f)
    
    np_prefix = np.array(no_prop.prefix_f)
    np_origin = np.array(no_prop.origin_f)
    np_compare = np.array(no_prop.compare_f)

    asn_index = np.array(full.asns)

    N = f_prefix.size
    ind = np.arange(N) # the n collectors for the trial
    
    # Create plot
    fig, ax = plt.subplots()
    b_width = .25
    b_opacity = .8

    #p1 = plt.errorbar(f_ind, f_kc, yerr=f_std, fmt='o', label="Full")
    p1 = plt.bar(ind, f_prefix, b_width, color='red')
    p2 = plt.bar(ind, f_origin, b_width, bottom=f_prefix, color='green')
    p3 = plt.bar(ind, f_compare, b_width, bottom=f_origin, color='blue')
    p4 = plt.bar(ind+b_width, oo_prefix, b_width, color='red')
    p5 = plt.bar(ind+b_width, oo_origin, b_width, bottom=oo_prefix, color='green')
    p6 = plt.bar(ind+b_width, oo_compare, b_width, bottom=oo_origin, color='blue')
    p7 = plt.bar(ind+b_width*2, np_prefix, b_width, color='red')
    p8 = plt.bar(ind+b_width*2, np_origin, b_width, bottom=np_prefix, color='green')
    p9 = plt.bar(ind+b_width*2, np_compare, b_width, bottom=np_origin, color='blue')

    plt.xlabel('Collector')
    plt.ylabel('Failures')
    plt.title(name)
    plt.legend()
    plt.xticks(ind, asn_index, rotation='vertical')

    plt.show()

def main():
    """Generates stats and plots for a given trial."""

    if len(sys.argv) != 2:
        print("Usage: statitics.py <results_dir> ", file=sys.stderr)
        sys.exit(-1)
   
    fn1 = sys.argv[1] + "/full_verified.csv"
    fn2 = sys.argv[1] + "/origin_verified.csv"
    fn3 = sys.argv[1] + "/no_prop_verified.csv"
    
    print(datetime.now().strftime("%c") + ": Loading data.")
    
    # Data for normal verification runs
    full_ext = Trial_Set()
    load_data(full_ext, fn1)

    # Data for origin only verification runs
    origin_only = Trial_Set()
    load_data(origin_only, fn2)
    
    # Data for MRT no propagation verfication runs
    mrt_no_prop = Trial_Set()
    load_data(mrt_no_prop, fn3)

    print(datetime.now().strftime("%c") + ": Processing data.")
    
    ttest_ld(full_ext, origin_only, mrt_no_prop)
    plot_ld(full_ext, origin_only, mrt_no_prop)
    plot_kc(full_ext, origin_only, mrt_no_prop)
    plot_kc(full_ext, origin_only, mrt_no_prop, True)
    plot_class_fail(full_ext, origin_only, mrt_no_prop)

if __name__ == "__main__":
    main()
