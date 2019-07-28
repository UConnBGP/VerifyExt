import sys
import psycopg2
import psycopg2.extras
import shutil
import os
import logging
from configparser import ConfigParser
from datetime import datetime

LOG_LOC = r"/tmp/"
TABLE_NAME = r"verify_data_8220"
MRT_TABLE_NAME = r"verify_ctrl_8220_distinct"

def connectToDB():
    """Creates a connection to the SQL database.
    
    Returns:
    cur: a reference to the psycopg2 SQL named tuple cursor
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


# returns AS-PATH accessed from a source of MRT
# announcements as a list, removing repetitions.
def readMrtAnnRow(cursor, AS, prefix, origin):
    parameters = (prefix, AS)
    sql_select = ("SELECT * FROM " + MRT_TABLE_NAME       
                 + " WHERE prefix = (%s)" 
                 + " AND origin = "+ origin
                 + " AND as_path[1] = (%s)")
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchone() 

    as_path_list = []

    for i in announcement[3]:
        if as_path_list.count(int(i))<1:
            as_path_list.append(int(i))

    return as_path_list


# Returns a dict of every prefix-origin pair passing through an AS
# according to the control set.
def getPrefixSet(cursor, AS):
    parameters=(AS,)
    sql_select = ("SELECT * FROM " + MRT_TABLE_NAME       
                 + " WHERE as_path[1] = (%s)")
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchall()

    prefix_dict = {}

    for i in announcement:
        if (i[1],i[2]) not in prefix_dict:
            prefix_dict[(i[1],i[2])]=i[3]

    return prefix_dict


def getAnn(cursor, AS, prefix, origin):
    """Fetch a single announcement for a given AS and prefix/origin
    
    Parameters:
    AS  32-bit integer ASN of target AS
    prefix  CIDR format ipv4 address for target prefix
    origin  32-bit integer ASN of target prefix origin
    
    Returns:
    announcement  A 4-element tuple or None if no rows found 
    """

    parameters = (prefix, )
    sql_select = ("SELECT * FROM " + TABLE_NAME       
                 + " WHERE asn = " + AS 
                 + " AND prefix = (%s)" 
                 + " AND origin = "+ origin)
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchone()
    # Returns tuple or None
    return announcement


# designing this so it can pull what's needed from
# the results
def getAnnSet(cursor,prefix, origin):
    # print("fetching announcement set...")
    parameters = (prefix, )
    sql_select = ("SELECT * FROM " + TABLE_NAME
                 + " WHERE origin = " + origin
                 + " AND prefix = (%s)")
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchall()

    ann_set = {announcement[0][0]:announcement[0][3]}
  
    for i in range(1, len(announcement)):
        ann_set[announcement[i][0]]= announcement[i][3]

    # Returns DICT or None
    return ann_set


# now returns an int list!
def localTraceback(localDict, AS, origin, result_list):
    if AS in localDict:   
        current_as = localDict[AS]
        current_as_str = str(localDict[AS])
        origin_str = str(origin)
        # print("current AS str: "+current_as_str)
        if current_as == origin:
            result_list.append(origin)
            return result_list
        else:
            result_list.append(current_as)
            return localTraceback(localDict, current_as, origin, result_list)    
    else:
        return result_list


"""
old path compare function, preserved if we need it

takes two different as_paths and compares them, then
outputs an accuracy estimate as a float

rough version finished, going to test now
[1,2,3,4], [0,1,2,3,4] -> .8
[], [1] -> 0
"""
def path_compare_old(as_path1, as_path2):
    denominator = float(max(len(as_path1), len(as_path2)))
    numerator = float(0)
    if denominator == 0 or None:
        return 0
    for i in range(len(as_path1)):
        if as_path1[i] in as_path2:
            numerator = numerator + 1
    return numerator / denominator


"""
takes two different as_paths and compares them, then
outputs 1 if they are the same, and 0 if they are different

[1,2,3,4], [0,1,2,3,4] -> 0
[], [1] -> 0
[1,2,3,4], [1,2,4,3] -> 0
[1,2,3,4],[1,2,3,4] -> 1

way to use this:
    keep track of total number we are comparing, and
    the total correct will be the sum of the function calls
    
    conversely, the total number incorrect will be the total
    minus the number correct
    
    from there, you can calculate an estimate of how likely it is
    to be correct
"""
def path_compare(as_path1, as_path2):
    if len(as_path2) != len(as_path1):
        return 0
    if len(as_path1) == 0 or None:
        return 0
    for i in range(len(as_path1)):
        if as_path1[i] != as_path2[i]:
            return 0
    return 1


"""
this is a naive approach to comparing AS paths

takes in two AS paths as lists, and returns
the number of correct hops and incorrect hops

it starts from the end of the path, and works its way
back to the start of the list, and excludes the origin
from the count

I also made sure it would not result in index out of bounds
errors

tests:
[1,2,3],[1,2,3] -> [2, 0]

[1,2,3,4], [1,2,4] -> [1, 1]
^ it compares 4 with 4, 2 with 3, and then excludes the origin
from the second AS path

this should always have at least one correct hop, as the destination
ASes should match, otherwise there is a problem
"""
def naive_compare(as_path1, as_path2):
    correct_hops = 0
    incorrect_hops = 0
    max_index = min(len(as_path1),len(as_path2))
    for i in range(-1, -max_index, -1):
        if(as_path1[i] == as_path2[i]):
            correct_hops = correct_hops + 1
        else:
            incorrect_hops = incorrect_hops + 1
    return [correct_hops, incorrect_hops]


def main():
    """Connects to a SQL database to push a data partition for storage.    
    
    Parameters:
    argv[1]  32-bit integer ASN of target AS
    argv[2]  CIDR format ipv4 address for control prefix
    argv[3]  32-bit integer ASN of target prefix origin
    argv[4]  BETA FEATURE how many prefix origin sets we're testing
    """    

    if len(sys.argv) != 5:
        print("Usage: traceback.py <AS> <prefix> <origin> <rounds>", file=sys.stderr)
        sys.exit(-1)
    
    # Logging config 
    logging.basicConfig(level=logging.INFO, filename=LOG_LOC + datetime.now().strftime("%c"))
    logging.info(datetime.now().strftime("%c") + ": Traceback Start...")
    
    # Create a cursor for SQL Queries
    cursor = connectToDB();

    # Counter to verify correctness
    correct_hops=0
    incorrect_hops=0

    # Trace back the AS path for that announcement
    my_AS = int(sys.argv[1])
    rounds = int(sys.argv[4])

    # Get the prefix set
    print("Verifying received announcements...")
    prefix_set = getPrefixSet(cursor, sys.argv[1])
    
    for i in prefix_set:
        this_pair = i
        origin_str = str(i[1])
        
        # Get the propagted announcents 
        origin_set = getAnnSet(cursor, i[0], origin_str)
        # Recreate the extrapolated AS path
        result_as_path = localTraceback(origin_set, my_AS, i[1], [my_AS])        

        # Get the MRT announcement path
        reported_as_path = readMrtAnnRow(cursor, sys.argv[1], i[0], origin_str)

        hop_results = naive_compare_ftb(reported_as_path, result_as_path)
        correct_hops = correct_hops + hop_results[0]
        incorrect_hops = incorrect_hops + hop_results[1]

        rounds = rounds - 1
        if rounds == 0:
            break
    
    corr_hops_str = str(correct_hops)
    incorr_hops_str = str(incorrect_hops)

    result_str = "Correct Hops: " + corr_hops_str + " Incorrect Hops: " + incorr_hops_str
    print(result_str)


if __name__ == "__main__":
    main()
