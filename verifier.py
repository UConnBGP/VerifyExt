#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module defines the Verifier class.

The verifier class generates statistics for the verification of a single Autonomous System(AS).
"""

__version__ = '0.2'
__author__ = 'James Breslin'

import sys
import psycopg2
import psycopg2.extras
import shutil
import os
import logging
from configparser import ConfigParser
from datetime import datetime

CONFIG_LOC = r"/etc/bgp/bgp.conf"

class Verifier:
    """This class performs verification for a single AS."""
    # Number of prefixes in MRT and number verifiable
    prefixes = 0
    verifiable = 0
    # Records success up to the Kth hop
    k = [0] * 10
    # Records failure at the Kth hop
    l = [0] * 10
    # Records for naive compare 
    correct_hops = 0
    incorrect_hops = 0
    # Verified prefixes for AVG. calc 
    ver_count = 0
    # Records for Levenshtein compare
    levenshtein_d = 0
    levenshtein_avg = 0
    
    def __init__(self, asn, origin_only):
        # Set dynamic SQL table names
        self.mrt_table =  r"verify_ctrl_" + str(asn)
        
        if (int(origin_only) == 0):
            print("Setting full path verification.")
            self.ext_table = r"verify_data_" + str(asn)
        else:
            print("Setting origin only verification.")
            self.ext_table = "verify_data_" + str(asn) + "_oo"

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
        cur = conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        return cur

    def get_mrt_anns(self, cursor, AS):
        """Creates a dictionary from the the set of prefix/origins as key-value pairs.
        Parameters:
        AS  String of 32-bit integer ASN of target AS

        Returns:
        prefix_dict  A dictionary of every prefix-origin pair passing through an AS according to the control set.
        """
        parameters=(AS,)
        sql_select = ("SELECT * FROM " + self.mrt_table
                     + " WHERE as_path[1] = (%s)")
        # Execute the dynamic query
        cursor.execute(sql_select, parameters)
        announcements = cursor.fetchall()
        mrt_dict = {}
        
        # For each announcemennt
        for ann in announcements:
            # If prefix not in the dictionary, add it
            # This ignores multi-origin prefixes
            # This ignores multi-AS path prefixes
            if ann[0] not in mrt_dict:
                # Create AS path for current prefix
                as_path = []
                for asn in ann[2]:
                    # Removes duplicate ASNs
                    if as_path.count(int(asn))<1:
                        as_path.append(int(asn))
                mrt_dict[ann[0]]=(as_path, ann[1])
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
            # Create dictionary of {current ASN + prefix : (origin, received from ASN)} pairs
            for i in range(anns_sz):
                key = str(anns[i][0]) + str(anns[i][1])
                ext_dict[key] = (anns[i][2], anns[i][3])
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
        cur_key = str(AS) + str(prefix)
        if cur_key in ext_dict:
            # Origin/received from AS pair
            pair = ext_dict[cur_key]
            origin = pair[0]
            recv = pair[1]
            
            # End of path
            if recv == origin:
                result_list.append(int(origin))
                return result_list
            else:
                result_list.append(int(recv))
                return traceback(ext_dict, recv, prefix, origin, result_list)    
        else:
            self.verifiable -= 1
            print("Traceback Error: " + cur_key + " not in results.")
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
        res = min([levenshtein(mrt_path[:-1], prop_path)+1,
                   levenshtein(mrt_path, prop_path[:-1])+1, 
                   levenshtein(mrt_path[:-1], prop_path[:-1]) + cost])
        return res

    def run():
        pass


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
    
    # Create a cursor for SQL Queries
    cursor = v.connectToDB();

    # Counter to verify correctness
   
    # Trace back the AS path for that announcement
    print("Getting MRT announcements...")
    # Dict = {prefix: (as_path, origin)}
    mrt_set = v.get_mrt_anns(cursor, sys.argv[1])
    
    print("Getting extrapolated announcements...")
    # Dict = {current ASN + prefix: (origin, received from ASN)}
    ext_set = v.get_ext_anns(cursor)

    v.prefixes = len(mrt_set)
    v.verifiable = len(mrt_set)
    
    # For each prefix in the ASes MRT announcements
    print("Performing verification for " + str(v.prefixes) + " prefixes")
    for prefix in mrt_set:
        mrt_pair = mrt_set[prefix]
        mrt_path = mrt_pair[0]
        mrt_origin = mrt_pair[1]
        
        cur_key = str(ctrl_AS) + str(prefix)
        
        # If AS has no extrapolated announcement for current prefix
        if cur_key not in ext_set:
            v.verifiable -= 1
            print("Prefix Error: " + cur_key + " is not in results.")
            continue;       
        
        # If MRT origin doesn't matche extrapolated origin
        ext_origin = ext_set[cur_key][1]
        if ext_origin != mrt_origin:
            v.verifiable -= 1
            print("Origin Error: " + cur_key + " is not in results.")
            continue;

        # Recreate the extrapolated AS path
        ext_as_path = v.traceback(ext_set, ctrl_AS, prefix, mrt_origin, [int(ctrl_AS)])
        
        # If extrapolated path is complete
        if (ext_as_path != None):
            # Get the MRT announcement path
            reported_as_path = mrt_set[ann][0]
            # Compare paths
            hop_results = v.naive_compare_btf(ext_as_path, reported_as_path)
            v.correct_hops += hop_results[0]
            v.incorrect_hops += hop_results[1]

            # Levenshtein compare
            v.ver_count += 1
            cur_distance = levenshtein(reported_as_path, ext_as_path)
            v.levenshtein_avg = levenshtein_avg + (cur_distance - levenshtein_avg) / ver_count
            v.levenshtein_d += cur_distance
    
    # K is success up to kth hop
    print(v.k)
    # L is success until the kth hop
    print(v.l)
    print("Total Levenshtein Distance: " + str(v.levenshtein_d))
    print("Levenshtein Average: " + str(v.levenshtein_avg))
    print("Verifiable prefixes: " + str(v.verifiable))
    result_str = "Correct Hops: " + str(v.correct_hops) + " Incorrect Hops: " + str(v.incorrect_hops)
    print(result_str)


if __name__ == "__main__":
    main()
