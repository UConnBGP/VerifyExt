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
                 + " AND origin = " + origin)
    # Execute the dynamic query
    cursor.execute(sql_select, parameters)
    announcement = cursor.fetchone()
    # Returns tuple or None
    return announcement

def traceback(cursor, AS, prefix, origin):
    pass

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
                            
    # Logging config 
    logging.basicConfig(level=logging.INFO, filename=LOG_LOC + datetime.now().strftime("%c"))
    logging.info(datetime.now().strftime("%c") + ": Traceback Start...")
    
    # Create a cursor for SQL Queries
    cursor = connectToDB();
    
    # Trace back the AS path for that announcement
    #traceback(cursor, sys.argv[1], sys.argv[2], sys.argv[3])
    getAnn(cursor, sys.argv[1], sys.argv[2], sys.argv[3])

if __name__=="__main__":
    main()
