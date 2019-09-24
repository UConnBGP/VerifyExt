#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module defines the Verifier class.

The verifier class generates statistics for the verification of a single Autonomous System(AS).
"""

__version__ = '0.3'
__author__ = 'James Breslin'

import sys
import psycopg2
import psycopg2.extras
import shutil
import os
import logging
from os import path
from configparser import ConfigParser
from datetime import datetime

CONFIG_LOC = r"/etc/bgp/bgp.conf"

class Verifier:
    """This class performs verification for a single AS."""
    
    def __init__(self, asn, origin_only):
        self.ctrl_AS = asn
        self.oo = int(origin_only)
        
        # Set dynamic SQL table names
        self.mrt_table =  r"verify_ctrl_" + str(asn)
        if (self.oo == 0):
            print(datetime.now().strftime("%c") + ": Performing verification for AS" + str(asn))
            print(datetime.now().strftime("%c") + ": Setting full path verification.")
            self.ext_table = r"verify_data_" + str(asn)
        else:
            print(datetime.now().strftime("%c") + ": Performing origin verification for AS" + str(asn))
            print(datetime.now().strftime("%c") + ": Setting origin only verification.")
            self.ext_table = "verify_data_" + str(asn) + "_oo"
        
        # Number of prefixes in MRT and number verifiable
        self.prefixes = 0
        self.verifiable = 0
        # General path stats
        self.mrt_avg_len = 0
        self.mrt_max_len = 0
        self.ext_avg_len = 0
        self.ext_max_len = 0
        # Records success up to the Kth hop
        self.k = [0] * 10
        # Records failure at the Kth hop
        self.l = [0] * 10
        # Records for naive compare 
        self.correct_hops = 0
        self.incorrect_hops = 0
        # Verified prefixes for AVG. calc 
        self.ver_count = 0
        # Records for Levenshtein compare
        self.levenshtein_d = 0
        self.levenshtein_avg = 0


    def connectToDB(self):
        """Creates a connection to the SQL database.
        
        Returns:
        cur -  A reference to the psycopg2 SQL named tuple cursor.
        """
        # Get the config profile
        cparser = ConfigParser()
        cparser.read("/etc/bgp/bgp.conf")
        # Establish DB connection
        print(datetime.now().strftime("%c") + ": Connecting to database...")
        try:
            conn = psycopg2.connect(host = cparser['bgp']['host'],
                                    database = cparser['bgp']['database'],
                                    user = cparser['bgp']['user'],
                                    password = cparser['bgp']['password'])
            print(datetime.now().strftime("%c") + ": Login successful.")
        except:
            print(datetime.now().strftime("%c") + ": Login failed.")
        # Create the cursor
        cur = conn.cursor()
        return cur

    def get_mrt_anns(self, cursor, AS):
        """Creates a dictionary from the the set of prefix/origins as key-value pairs.
        Parameters:
        AS  String of 32-bit integer ASN of target AS

        Returns:
        prefix_dict  A dictionary of every prefix-origin pair passing through an AS according to the control set.
        """
        parameters=(AS,)
        sql_select = ("SELECT * FROM " + self.mrt_table)
        # Execute the dynamic query
        cursor.execute(sql_select, parameters)
        announcements = cursor.fetchall()
        mrt_dict = {}
        
        # For each announcemennt
        for ann in announcements:
            # If prefix not in the dictionary, add it
            # This ignores multi-origin prefixes
            # This ignores multi-AS path prefixes
            prefix = ann[0]
            if prefix not in mrt_dict:
                # Create AS path for current prefix
                as_path = []
                for asn in ann[2]:
                    # Removes duplicate ASNs
                    if as_path.count(int(asn))<1:
                        as_path.append(int(asn))
                mrt_dict[prefix]=(as_path, ann[1])
        return mrt_dict

    def get_ext_anns(self, cursor):
        """ Creates a dictionary for all announcements keyed to AS/prefix.
       
        Returns:
        ann_set  A dictionary of AS-prefix : (origin, recv from AS) key-value pairs
        """
        sql_select = ("SELECT * FROM " + self.ext_table)
        # Execute the dynamic query
        cursor.execute(sql_select)
        anns = cursor.fetchall()
        anns_sz = len(anns)
        # Returns DICT or None
        ext_dict = {}
        if anns_sz != 0:
            # Create dictionary of {current ASN + prefix + origin: received from ASN} pairs
            for ann in anns:
                key = str(ann[0]) + str(ann[1] + str(ann[2]))
                ext_dict[key] = (ann[3])
            return ext_dict
        else:
            return None

    def traceback(self, ext_dict, AS, prefix, origin, result_list):
        """Generates a AS path as a list from the passed dictionary object.
        Parameters:
        ext_dict  Dictionary of current ASN, received from ASN pairs
        AS  32-bit integer ASN of the current AS on path
        origin  32-bit integer ASN of target prefix origin
       
        Returns:
        result_list  A list of 32-bit int ASNs along the extrapolated AS path.  
        """
        cur_key = str(AS) + str(prefix) + str(origin)
        if cur_key in ext_dict:
            # Origin/received from AS pair
            recv = ext_dict[cur_key]
            
            # End of path
            if recv == origin:
                result_list.append(int(origin))
                return result_list
            else:
                result_list.append(int(recv))
                return self.traceback(ext_dict, recv, prefix, origin, result_list)    
        else:
            self.verifiable -= 1
            print(datetime.now().strftime("%c") + ": Traceback Error: " + cur_key + " not in results.")
            return None

    def naive_compare_btf(self, prop_path, mrt_path):
        """Simple K compare method, counting correct path hops up to the first mistake.
        Parameters:
        prop_path  Propagated path given by Extrapolation results
        mrt_path  Correct path given by MRT announcement
       
        Returns:
        result_list  A list of correct and incorrect hops.  
        """
        # If propagted path is empty
        if not prop_path:
            return [0, len(mrt_path)]
        
        correct = 0
        incorrect = 0
        # Find bounds
        max_index = min(len(prop_path), len(mrt_path))
        mismatch = max(len(prop_path), len(mrt_path)) - max_index
        
        # Reverse index to start at end of lists
        j = 2
        for i in range(-1, -max_index, -1):
            if prop_path[i] == mrt_path[i]:
                if (i < -1 and j == abs(i)):
                    self.k[j-2] += 1
                    j += 1
                correct += 1
            else:
                if (j == abs(i)):
                    self.l[j-2] += 1
                incorrect += 1
        return [correct - 1, incorrect + mismatch]

    def call_counter(func):
        def wrapper(*args, **kwargs):
            wrapper.calls += 1
            return func(*args, **kwargs)
        wrapper.calls = 0
        wrapper.__name__ = func.__name__
        return wrapper

    def memoize(func):
        mem = {}
        def memoizer(*args, **kwargs):
            # TODO May need a delimiter
            key = str(args) + str(kwargs)
            if key not in mem:
                mem[key] = func(*args, **kwargs)
            return mem[key]
        return memoizer

    @memoize    
    def levenshtein(mrt_path, prop_path):
        """Levenshtein compare method, calculating edit distance between two paths.
        Parameters:
        mrt_path  Correct path given by MRT announcement
        prop_path  Propagated path given by Extrapolation results
       
        Returns:
        result  The edit distance between two paths. 
        """
        # Check for empty strings
        if not mrt_path:
            return len(prop_path)
        if not prop_path:
            return len(mrt_path)
        # If last element matchs
        if mrt_path[-1] == prop_path[-1]:
            cost = 0
        else: # Operation required
            cost = 1
        # Recursive call triming path for add, subtract, substitute
        res = min([Verifier.levenshtein(mrt_path[:-1], prop_path)+1,
                   Verifier.levenshtein(mrt_path, prop_path[:-1])+1, 
                   Verifier.levenshtein(mrt_path[:-1], prop_path[:-1]) + cost])
        return res

    def run(self):
        # Create a cursor for SQL Queries
        cursor = self.connectToDB();
       
        # Trace back the AS path for that announcement
        print(datetime.now().strftime("%c") + ": Getting MRT announcements...")
        # Dict = {prefix: (as_path, origin)}
        mrt_set = self.get_mrt_anns(cursor, self.ctrl_AS)
        
        print(datetime.now().strftime("%c") + ": Getting extrapolated announcements...")
        # Dict = {current ASN + prefix: (origin, received from ASN)}
        ext_set = self.get_ext_anns(cursor)
    
        # Set total vs. verifiable prefix count
        self.prefixes = len(mrt_set)
        self.verifiable = len(mrt_set)
        
        # For each prefix in the ASes MRT announcements
        print(datetime.now().strftime("%c") + ": Performing verification for " + str(self.prefixes) + " prefixes")
        for prefix in mrt_set:
            mrt_pair = mrt_set[prefix]
            mrt_path = mrt_pair[0]
            mrt_origin = mrt_pair[1]
            
            cur_key = str(self.ctrl_AS) + str(prefix) + str(mrt_origin)
            
            # Get the MRT announcement path
            reported_as_path = mrt_set[prefix][0]

            # If AS has no extrapolated announcement for current prefix
            if cur_key not in ext_set:
                # Add length of real path to mistakes
                self.incorrect_hops += len(reported_as_path)
                # Immediate failure for K compare
                self.l[0] += 1
                # Levenshtein distance is length of real path
                cur_distance= len(reported_as_path)
                self.levenshtein_avg = self.levenshtein_avg + (cur_distance - self.levenshtein_avg) / self.ver_count
                self.levenshtein_d += cur_distance
                #print("Prefix Error: " + cur_key + " is not in results.")
                continue;
            """
            # If MRT origin doesn't match extrapolated origin
            ext_origin = int(ext_set[cur_key][0])
            if ext_origin != mrt_origin:
                # Add length of real path to mistakes
                self.incorrect_hops += len(reported_as_path)
                # Immediate failure for K compare
                self.l[0] += 1
                # Levenshtein distance is length of real path
                cur_distance= len(reported_as_path)
                self.levenshtein_avg = self.levenshtein_avg + (cur_distance - self.levenshtein_avg) / self.ver_count
                self.levenshtein_d += cur_distance
                #print("Origin Error: " + cur_key + " is not in results.")
                continue;
            """

            # Recreate the extrapolated AS path
            ext_as_path = self.traceback(ext_set, self.ctrl_AS, prefix, mrt_origin, [int(self.ctrl_AS)])
            
            # If extrapolated path is complete
            if (ext_as_path != None):
                # Compare paths
                hop_results = self.naive_compare_btf(ext_as_path, reported_as_path)
                self.correct_hops += hop_results[0]
                self.incorrect_hops += hop_results[1]

                # Levenshtein compare
                self.ver_count += 1
                cur_distance = Verifier.levenshtein(reported_as_path, ext_as_path)
                self.levenshtein_avg = self.levenshtein_avg + (cur_distance - self.levenshtein_avg) / self.ver_count
                self.levenshtein_d += cur_distance
        
    def output(self):
        # TODO Make multiprocess safe
        fn = "batch_a.csv"
        print(datetime.now().strftime("%c") + ": Writing output to " + fn)
        if (path.exists(fn)):
            f = open(fn, "a+")
        else:
            f = open(fn, "w+")
        
        if self.oo == 0:
            f.write("%s\n" % self.ctrl_AS)
        else:
            f.write("%s-OO\n" % self.ctrl_AS)
        f.write("%d,%d\n" % (self.prefixes, self.verifiable))
        
        # K Compare Correct
        str_l = []
        for x in self.k:
            str_l.append(str(x))
        f.write(','.join(str_l)) 
        f.write("\n")
        
        # K Compare Incorrect
        str_l = []
        for x in self.l:
            str_l.append(str(x))
        f.write(','.join(str_l))
        f.write("\n")
        
        # Levenshtein Values
        f.write("%f\n" % self.levenshtein_avg)
        f.write("%d\n" % self.levenshtein_d)
        f.write("%d,%d\n\n" % (self.correct_hops, self.incorrect_hops))
        f.close()
        print("\n")
    
    def output_cl(self):
        if self.oo == 0:
            print("%s\n" % self.ctrl_AS)
        else:
            print("%s-OO\n" % self.ctrl_AS)
        print("%d,%d\n" % (self.prefixes, self.verifiable))
        
        # K Compare Correct
        str_l = []
        for x in self.k:
            str_l.append(str(x))
        print(','.join(str_l)) 
        print("\n")
        
        # K Compare Incorrect
        str_l = []
        for x in self.l:
            str_l.append(str(x))
        print(','.join(str_l))
        print("\n")
        
        # Levenshtein Values
        print("%f\n" % self.levenshtein_avg)
        print("%d\n" % self.levenshtein_d)
        print("%d,%d\n\n" % (self.correct_hops, self.incorrect_hops))


def main():
    """Generates stats for a set of ASes using multi-processing.
    
    Parameters:
    argv[1]  32-bit integer ASN of target AS
    argv[2]  Origin Only Boolean
    """    

    if len(sys.argv) != 3:
        print("Usage: verifier.py <AS> <OOBool>", file=sys.stderr)
        sys.exit(-1)
    
    # Set table names
    ctrl_AS = str(sys.argv[1])
    v = Verifier(ctrl_AS, sys.argv[2])
    v.run()
    v.output_cl()
    
if __name__ == "__main__":
    main()
