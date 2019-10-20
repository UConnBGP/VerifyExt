#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module defines the Verifier class.

The verifier class generates statistics for the verification of a single Autonomous System(AS).
"""

__version__ = '0.4'
__author__ = 'James Breslin'

import sys
import psycopg2
import psycopg2.extras
import shutil
import os
import gc
import logging
from os import path
from configparser import ConfigParser
from datetime import datetime
from profilehooks import profile

CONFIG_LOC = r"/etc/bgp/bgp.conf"

class Verifier:
    """This class performs verification for a single AS."""
    
    def __init__(self, asn, origin_only):
        """Parameters:
        asn  A string or int representation of 32 bit ASN.
        origin_only  A integer to select extrapolator data.
        """
        self.ctrl_AS = int(asn)
        self.oo = int(origin_only)
        
        # Set dynamic SQL table names
        self.mrt_table =  r"verify_ctrl_" + str(asn)
        if (self.oo == 0):
            print(datetime.now().strftime("%c") + ": Performing verification for AS" + str(asn))
            print(datetime.now().strftime("%c") + ": Setting full path verification.")
            self.ext_table = r"verify_data_" + str(asn)
        elif (self.oo == 1):
            print(datetime.now().strftime("%c") + ": Performing verification for AS" + str(asn))
            print(datetime.now().strftime("%c") + ": Setting origin only verification.")
            self.ext_table = "verify_data_" + str(asn) + "_oo"
        else:
            print(datetime.now().strftime("%c") + ": Performing verification for AS" + str(asn))
            print(datetime.now().strftime("%c") + ": Setting MRT only verification.")
            self.ext_table = "verify_data_" + str(asn) + "_mo"

        # Number of prefixes in MRT and number verifiable
        self.prefixes = 0
        self.verifiable = 0
        # General path stats
        self.cur_count = 0
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
        # Failure Classification
        self.pref_orig_f = 0
        self.traceback_f = 0
        self.compare_f = 0


    def connectToDB(self):
        """Creates a connection to the SQL database.
        
        Returns:
        cur  A reference to the psycopg2 SQL named tuple cursor.
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
        cur = conn.cursor("ver_cursor")
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
            prefix = ann[1]
            if prefix not in mrt_dict:
                # Create AS path for current prefix
                as_path = []
                for asn in ann[3]:
                    # Removes duplicate ASNs
                    if as_path.count(int(asn))<1:
                        as_path.append(int(asn))
                mrt_dict[prefix]=(as_path, ann[2])
        return mrt_dict

    def get_ext_anns(self, cursor):
        """ Creates a dictionary for all announcements keyed to AS/prefix.
       
        Returns:
        ann_set  A dictionary of AS-prefix : (origin, recv from AS) key-value pairs
        """
        sql_select = ("SELECT * FROM " + self.ext_table)
        # Execute the dynamic query
        cursor.execute(sql_select)
        print(datetime.now().strftime("%c") + ": Cursor fetchall...")
        anns = cursor.fetchall()
        collected = gc.collect()
        print(datetime.now().strftime("%c") + ": Fetch complete.")
        anns_sz = len(anns)
        # Returns DICT or None
        ext_dict = {}
        print(datetime.now().strftime("%c") + ": Creating Dictionary...")
        if anns_sz != 0:
            # Create dictionary of {current ASN + prefix + origin: received from ASN} pairs
            for ann in anns:
                key = str(ann[0]) + ann[1] + str(ann[2])
                ext_dict[key] = (ann[3])
            print(datetime.now().strftime("%c") + ": Dictionary construction complete.")
            return ext_dict
        else:
            return None
    
    def get_ptp_rel(self, cursor):
        """ Creates a dictionary for all peer-to-peer relationships.
       
        Returns:
        ptp_set  A dictionary of {lower ASN: higher ASN} pairs.
        """
        sql_select = ("SELECT * FROM peers")
        cursor.execute(sql_select)
        relationships = cursor.fetchall()
        ptp_dict = {}
        for rel in relationships:
            ptp_dict[rel[0]] = rel[1]
        return ptp_dict

    def get_ptc_rel(self, cursor):
        """ Creates a dictionary for all provider-to-customer relationships.
       
        Returns:
        ptc_set  A dictionary of {provider ASN: customer ASN} pairs.
        """
        sql_select = ("SELECT * FROM customer_providers")
        cursor.execute(sql_select)
        relationships = cursor.fetchall()
        ptc_dict = {}
        for rel in relationships:
            ptc_dict[rel[0]] = rel[1]
        return ptc_dict

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
            # Some ASN on path is missing the prefix/origin
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
    
    def k_compare(self, prop_path, mrt_path):
        """Simple K compare method, counting correct path hops up to the first mistake.
        Parameters:
        prop_path  Propagated path given by Extrapolation results
        mrt_path  Correct path given by MRT announcement
       
        Returns:
        result_list  A list of correct and incorrect hops.  
        """
        # If propagted path is empty
        if not prop_path:
            print("No path, k compare gets nothing!")
            self.l[0] += 1
            return [0, len(mrt_path)]
        
        correct = 0
        incorrect = 0
        # Find bounds
        max_index = min(len(prop_path), len(mrt_path))
        
        # Reverse index to start at end of lists
        for i, (ext, mrt) in enumerate(zip(mrt_path, prop_path)):
            if ext == mrt:
                self.k[i] += 1
            else:
                self.l[i] += 1
                break

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
    
    @memoize    
    def levenshtein_opt(mrt_path, prop_path):
        """Levenshtein compare method, calculating edit distance between two paths.
        Parameters:
        mrt_path  Correct path given by MRT announcement
        prop_path  Propagated path given by Extrapolation results
       
        Returns:
        result  The edit distance between two paths. 
        """
        prop_l = len(prop_path)
        mrt_l = len(mrt_path)
        # Check for empty strings
        if not mrt_path:
            return prop_l
        if not prop_path:
            return mrt_l
        # If last element matchs
        if mrt_path[-1] == prop_path[-1]:
            cost = 0
        else: # Operation required
            cost = 1
        
        # If MRT is longer, need to add
        if mrt_l > prop_l:
            res = min([Verifier.levenshtein_opt(mrt_path[:-1], prop_path) + 1,
                        Verifier.levenshtein_opt(mrt_path[:-1], prop_path[:-1]) + cost])
        # If Prop is longer, need to subtract
        elif prop_l > mrt_l:
            res = min([Verifier.levenshtein_opt(mrt_path, prop_path[:-1]) + 1, 
                   Verifier.levenshtein_opt(mrt_path[:-1], prop_path[:-1]) + cost])
        # If equal length, only perform substitution
        else:
            res = min([Verifier.levenshtein_opt(mrt_path[:-1], prop_path[:-1]) + cost])

        return res

    def run(self):
        # Build the MRT control data set
        print(datetime.now().strftime("%c") + ": Getting MRT announcements...")
        # Dict = {prefix: (as_path, origin)}
        cursor = self.connectToDB();
        mrt_set = self.get_mrt_anns(cursor, self.ctrl_AS)
        cursor.close()
        
        # Build the Ext data set for comparison
        print(datetime.now().strftime("%c") + ": Getting extrapolated announcements...")
        # Dict = {current ASN + prefix: (origin, received from ASN)}
        cursor = self.connectToDB();
        ext_set = self.get_ext_anns(cursor)
        cursor.close()
        cursor = None
        gc.collect()

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
            reported_as_path.reverse()

            # Update MRT length stats
            self.cur_count += 1
            mrt_l = len(reported_as_path)
            if mrt_l > self.mrt_max_len:
                self.mrt_max_len = mrt_l
            #TODO write avg func
            self.mrt_avg_len = self.mrt_avg_len + (mrt_l - self.mrt_avg_len) / self.cur_count

            # If AS has no extrapolated announcement for current prefix/origin
            if cur_key not in ext_set:
                # Classify the failure
                self.pref_orig_f += 1
                # Verifiable failer
                self.ver_count += 1
                # Immediate failure for K compare
                self.l[0] += 1
                # Levenshtein distance is length of real path
                cur_distance= len(reported_as_path)
                self.levenshtein_avg = self.levenshtein_avg + (cur_distance - self.levenshtein_avg) / self.ver_count
                self.levenshtein_d += cur_distance
                continue;

            # Recreate the extrapolated AS path
            ext_as_path = self.traceback(ext_set, self.ctrl_AS, prefix, mrt_origin, [int(self.ctrl_AS)])
            
            # If extrapolated path is complete
            if (ext_as_path != None):
                # Update Ext length stats
                ext_as_path.reverse()
                self.ver_count += 1
                ext_l = len(ext_as_path)
                if mrt_l > self.ext_max_len:
                    self.ext_max_len = ext_l
                self.ext_avg_len = self.ext_avg_len + (ext_l - self.ext_avg_len) / self.cur_count

                # Compare paths
                self.k_compare(ext_as_path, reported_as_path)

                # Levenshtein compare
                cur_distance = Verifier.levenshtein_opt(reported_as_path, ext_as_path)
                self.levenshtein_avg = self.levenshtein_avg + (cur_distance - self.levenshtein_avg) / self.ver_count
                self.levenshtein_d += cur_distance
                
                # Classify Failure
                if cur_distance != 0:
                    self.compare_f += 1
            else:
                # Classify Failure
                self.traceback_f += 1
        
    def output(self):
        """Outputs stats for this AS to a .csv file."""
        # TODO Make multiprocess safe
        fn = "verified.csv"
        print(datetime.now().strftime("%c") + ": Writing output to " + fn)
        # TODO Try - except here
        if (path.exists(fn)):
            f = open(fn, "a+")
        else:
            f = open(fn, "w+")
        
        if (self.oo == 0):
            f.write("%s-Full\n" % self.ctrl_AS)
        elif (self.oo == 1):
            f.write("%s-OO\n" % self.ctrl_AS)
        else:
            f.write("%s-MO\n" % self.ctrl_AS)
        f.write("%d,%d\n" % (self.prefixes, self.verifiable))
        
        # Path statistics
        f.write("%f,%d\n" % (self.mrt_avg_len, self.mrt_max_len))
        f.write("%f,%d\n" % (self.ext_avg_len, self.ext_max_len))

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
        
        # Failure classification
        f.write("%d\n" % self.pref_orig_f)
        f.write("%d\n" % self.traceback_f)
        f.write("%d\n" % self.compare_f)

        # Levenshtein Values
        f.write("%f\n" % self.levenshtein_avg)
        f.close()
        print("\n")
    
    def output_cli(self):
        """Outputs stats for this AS to the CLI."""
        if self.oo == 0:
            print("%s\n" % self.ctrl_AS)
        else:
            print("%s-OO\n" % self.ctrl_AS)
        print("%d,%d\n" % (self.prefixes, self.verifiable))
       
        print("%f\n" % self.mrt_avg_len)
        print("%d\n" % self.mrt_max_len)
        print("%f\n" % self.ext_avg_len)
        print("%d\n" % self.ext_max_len)

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


def main():
    """Generates stats for a set of ASes using multi-processing.
    
    Parameters:
    argv[1]  32-bit integer ASN of target AS
    argv[2]  Origin Only Boolean
    """    

    if len(sys.argv) != 3:
        print("Usage: verifier.py <ASN> <OriginOnlyBool>", file=sys.stderr)
        sys.exit(-1)
    
    # Set table names
    ctrl_AS = sys.argv[1]
    v = Verifier(ctrl_AS, sys.argv[2])
    v.run()
    v.output_cli()
    
if __name__ == "__main__":
    main()
