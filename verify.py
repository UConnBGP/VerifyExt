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
MRT_TABLE_NAME = r"mrt_small"


def connectToDB():
    """Creates a connection to the SQL database.

    Returns:
    cur: a reference to the psycopg2 SQL cursor
    """
    # Get the config profile
    cparser = ConfigParser()
    cparser.read("/etc/bgp/bgp.conf")
    # Establish DB connection
    logging.info(datetime.now().strftime("%c") + ": Connecting to database...")
    try:
        conn = psycopg2.connect(host=cparser['bgp']['host'],
                                database=cparser['bgp']['database'],
                                user=cparser['bgp']['user'],
                                password=cparser['bgp']['password'])
        logging.info(datetime.now().strftime("%c") + ": Login successful.")
    except:
        logging.warning(datetime.now().strftime("%c") + ": Login failed.")
    # Create the cursor
    cur = conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
    return cur


# returns AS-PATH accessed from a source of MRT
# announcements as a list, removing repetitions.
def readMrtAnnRow(cursor, AS, prefix, origin):
    """
    print("SELECT * FROM " + MRT_TABLE_NAME
                 + " WHERE prefix = "+prefix
                 + " AND origin = "+ origin
                 + " AND "+ AS +" = ANY (as_path)")
    """
    parameters = (prefix,)
    sql_select = ("SELECT * FROM " + MRT_TABLE_NAME
                  + " WHERE prefix = (%s)"
                  + " AND origin = " + origin
                  + " AND " + AS + " = ANY (as_path)")
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchone()
    print(announcement[2])
    return announcement


def getAnn(cursor, AS, prefix, origin):
    """Fetch a single announcement for a given AS and prefix/origin

    Parameters:
    AS  32-bit integer ASN of target AS
    prefix  CIDR format ipv4 address for target prefix
    origin  32-bit integer ASN of target prefix origin

    Returns:
    announcement  A 4-element tuple or None if no rows found
    """

    parameters = (prefix,)
    sql_select = ("SELECT * FROM " + TABLE_NAME
                  + " WHERE asn = " + AS
                  + " AND prefix = (%s)"
                  + " AND origin = " + origin)
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchone()
    # Returns tuple or None
    return announcement


# designing this so it can pull what's needed from
# verify_data
def getAnnSet(cursor, prefix, origin):
    parameters = (prefix,)
    sql_select = ("SELECT * FROM " + TABLE_NAME
                  + " WHERE prefix = (%s)"
                  + " AND origin = " + origin)
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchall()

    ann_set = {announcement[0][0]: announcement[0][3]}
    # print(ann_set)

    for i in range(1, len(announcement)):
        ann_set[announcement[i][0]] = announcement[i][3]

    # print(ann_set)

    # Returns DICT or None
    return ann_set


def localTraceback(localDict, AS, origin, result_str):
    if AS in localDict:
        current_as = localDict[AS]
        current_as_str = str(localDict[AS])
        # print("current AS str: "+current_as_str)
        if current_as_str == origin:
            result_str = result_str + ", " + origin + " (origin) }"
            print(result_str)
        else:
            result_str = result_str + ", " + current_as_str
            # print(result_str)
            localTraceback(localDict, current_as, origin, result_str)
    else:
        result_str = result_str + " (origin) }"
        print(result_str)


def traceback(cursor, AS, prefix, origin, result_str):
    announcement = getAnn(cursor, AS, prefix, origin)
    # print(announcement)
    current_as = str(announcement[3])
    if current_as == origin:
        result_str = result_str + ", " + origin + " (origin) }"
        print(result_str)
    else:
        result_str = result_str + ", " + current_as
        traceback(cursor, current_as, prefix, origin, result_str)


"""
takes two different as_paths and compares them, then
outputs an accuracy estimate as a float

rough version finished, going to test now
[1,2,3,4], [0,1,2,3,4] -> .8
[], [1] -> 0
"""


def path_compare(as_path1, as_path2):
    denominator = float(max(len(as_path1), len(as_path2)))
    numerator = float(0)
    if denominator == 0 or None:
        return 0
    for i in range(len(as_path1)):
        if as_path1[i] in as_path2:
            numerator = numerator + 1
    return numerator / denominator


def main():
    """Connects to a SQL database to push a data partition for storage.
    Parameters:
    argv[1]  32-bit integer ASN of target AS
    argv[2]  CIDR format ipv4 address for target prefix
    argv[3]  32-bit integer ASN of target prefix origin
    """

    if len(sys.argv) != 4:
        print("Usage: traceback.py <AS> <prefix> <origin>", file=sys.stderr)
        sys.exit(-1)

    # they're all strings
    # print(type(sys.argv[1]), type(sys.argv[2]), type(sys.argv[3]), sep=" \n")

    # Logging config
    logging.basicConfig(level=logging.INFO, filename=LOG_LOC + datetime.now().strftime("%c"))
    logging.info(datetime.now().strftime("%c") + ": Traceback Start...")

    # Create a cursor for SQL Queries
    cursor = connectToDB();

    result_str = "Reconstructed AS-PATH: { (destination) " + sys.argv[1]

    # Trace back the AS path for that announcement
    my_set = getAnnSet(cursor, sys.argv[2], sys.argv[3])
    # print(my_set)

    my_AS = int(sys.argv[1])

    localTraceback(my_set, my_AS, sys.argv[3], result_str)
    # traceback(cursor, sys.argv[1], sys.argv[2], sys.argv[3], result_str)
    # readMrtAnnRow(cursor, sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
