import sys
import psycopg2
import psycopg2.extras
import shutil
import os
import logging
from configparser import ConfigParser
from datetime import datetime

LOG_LOC = r"/tmp/"
TABLE_NAME = r"verify_data"
MRT_TABLE_NAME = r"verify_ctrl_distinct"

def connectToDB():
    """Creates a connection to the SQL database.
    
    Returns:
    cur -  A reference to the psycopg2 SQL named tuple cursor.
    """
    # Get the config profile
    cparser = ConfigParser()
    cparser.read("/etc/bgp/bgp.conf")
    # Establish DB connection
    logging.info(datetime.now().strftime("%c") + ": Connecting to database...")
    try:
        conn = psycopg2.connect(host = cparser['bgp']['host'],
                                database = cparser['bgp']['database'],
                                user = cparser['bgp']['user'],
                                password = cparser['bgp']['password'])
        logging.info(datetime.now().strftime("%c") + ": Login successful.")
    except:
        logging.warning(datetime.now().strftime("%c") + ": Login failed.")
    # Create the cursor
    cur = conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
    return cur


def get_mrt_ann(cursor, AS):
    """Creates a dictionary from the the set of prefix/origins as key-value pairs.
    Parameters:
    AS  String of 32-bit integer ASN of target AS

    Returns:
    prefix_dict  A dictionary of every prefix-origin pair passing through an AS according to the control set.
    """
    parameters=(AS,)
    sql_select = ("SELECT * FROM " + MRT_TABLE_NAME       
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


def get_ext_ann(cursor, prefix, origin):
    """ Creates a dictionary for all announcements keyed to prefixi/origin.
    Parameters:
    prefix  String of CIDR format ipv4 address for target prefix
    origin  String of 32-bit integer ASN of target prefix origin
   
    Returns:
    ann_set  A dictionary of prefix origin key-value pairs  
    """
    #print("Fetching announcement set for " + str(prefix))
    parameters = (origin, prefix)
    sql_select = ("SELECT * FROM " + TABLE_NAME
                 + " WHERE origin = (%s)"
                 + " AND prefix = (%s)")
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    anns = cursor.fetchall()
    ann_sz = len(anns)
    # Returns DICT or None
    if ann_sz != 0:
        # Create dictionary of {current ASN:received from ASN} pairs
        ann_set = {anns[0][0]:anns[0][3]}
        
        for i in range(1, len(anns)):
            ann_set[anns[i][0]] = anns[i][3]
        return ann_set
    else:
        return None


def traceback(ext_dict, AS, origin, result_list):
    """Generates a AS path as a list from the passed dictionary object.
    Parameters:
    ext_dict  Dictionary of current ASN, received from ASN pairs
    AS  32-bit integer ASN of the current AS on path
    origin  32-bit integer ASN of target prefix origin
   
    Returns:
    result_list  A list of 32-bit int ASNs along the extrapolated AS path.  
    """
    AS = int(AS)
    if AS in ext_dict:
        current_as = ext_dict[AS]
        current_as_str = str(current_as)
        origin_str = str(origin)
        if current_as == origin:
            result_list.append(origin)
            return result_list
        else:
            result_list.append(int(current_as))
            return traceback(ext_dict, current_as, origin, result_list)    
    else:
        print("AS " + str(AS) + " not in dictionary.")
        return None


def path_compare(prop_path, mrt_path):
    hops = len(prop_path)
    correct = 0
    if hops == 0 or None:
        return [0, 0]
    for i in range(hops - 1):
        if prop_path[i] in mrt_path:
            correct += 1
    return [correct-2, hops - correct]


k = [0] * 10
l = [0] * 10
def naive_compare_btf(prop_path, mrt_path):
    correct = 0
    incorrect = 0
    max_index = min(len(prop_path), len(mrt_path))
    mismatch = max(len(prop_path), len(mrt_path)) - max_index
   
    # Reverse index to start at end of lists
    j = 2
    for i in range(-1, -max_index, -1):
        if prop_path[i] == mrt_path[i]:
            if (i < -1 and j == abs(i)):
                k[j-2] += 1
                j += 1
            correct += 1
        else:
            if (j == abs(i)):
                l[j-2] += 1
            incorrect += 1
    return [correct-1, incorrect + mismatch]


def main():
    """Connects to a SQL database to push a data partition for storage.    
    
    Parameters:
    argv[1]  32-bit integer ASN of target AS
    argv[2]  Origin Only Boolean
    """    

    if len(sys.argv) != 3:
        print("Usage: traceback.py <AS> <OOBool>", file=sys.stderr)
        sys.exit(-1)
    
    # Set table names
    ctrl_AS = str(sys.argv[1])
    global TABLE_NAME;
    global MRT_TABLE_NAME;
    if (int(sys.argv[2]) == 0):
        print("Setting MRT verification.")
        TABLE_NAME = "verify_data_" + ctrl_AS
        MRT_TABLE_NAME = r"verify_ctrl_" + ctrl_AS + "_distinct"
    else:
        print("Setting origin only verification.")
        TABLE_NAME = "verify_data_" + ctrl_AS + "_oo"
        MRT_TABLE_NAME = r"verify_ctrl_" + ctrl_AS + "_distinct"

    # Logging config 
    logging.basicConfig(level=logging.INFO, filename=LOG_LOC + datetime.now().strftime("%c"))
    logging.info(datetime.now().strftime("%c") + ": Verification Start...")
    
    # Create a cursor for SQL Queries
    cursor = connectToDB();

    # Counter to verify correctness
    correct_hops=0
    incorrect_hops=0

    # Trace back the AS path for that announcement
    # Get the mrt set
    print("Getting MRT announcements...")
    # Dict = {prefix: (as_path, origin)}
    mrt_set = get_mrt_ann(cursor, sys.argv[1])
    
    ver_pref = len(mrt_set)
    print("Performing verification for " + str(ver_pref) + " prefixes")
    for ann in mrt_set:
        origin_str = str(mrt_set[ann][1])
        
        # Get the propagted announcements
        # Dict = {current ASN: received from ASN}
        origin_set = get_ext_ann(cursor, ann, origin_str)
        
        if origin_set == None:
            ver_pref -= 1
            print(str(ann) + " " + str(origin_str) + " is not present in results.")
            continue;
        
        # Recreate the extrapolated AS path
        ext_as_path = traceback(origin_set, ctrl_AS, mrt_set[ann][1], [int(ctrl_AS)])
        
        # If extrapolated path is complete
        if (ext_as_path != None):
            # Get the MRT announcement path
            reported_as_path = mrt_set[ann][0]
            # Compare paths
            hop_results = naive_compare_btf(reported_as_path, ext_as_path)
            correct_hops += hop_results[0]
            incorrect_hops += hop_results[1]
        else:
            # Incomplete extrapolated path
            ver_pref -= 1
            print(str(ann) + " " + str(origin_str) + " does not have complete path.")

    print(k)
    print(l)
    corr_hops_str = str(correct_hops)
    incorr_hops_str = str(incorrect_hops)
    print("Verifiable prefixes: " + str(ver_pref))
    result_str = "Correct Hops: " + corr_hops_str + " Incorrect Hops: " + incorr_hops_str
    print(result_str)


if __name__ == "__main__":
    main()
