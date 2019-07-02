import sys
import psycopg2
import psycopg2.extras
import shutil
import os
import logging
from configparser import ConfigParser
from datetime import datetime

LOG_LOC = r"/tmp/"
TABLE_NAME = "extrapolation_results"

def connectToDB():
    """Creates a connection to the SQL database.
    
    Returns:
    cur: a reference to the psycopg2 SQL cursor
    """
    # Get the config profile
    cparser = ConfigParser()
    cparser.read("/etc/bgp/bgp.conf")
    # Establish DB connection
    try:
        conn = psycopg2.connect(host = cparser['bgp']['host'],
                                database = cparser['bgp']['database'],
                                user = cparser['bgp']['user'],
                                password = cparser['bgp']['password'])
        logging.info(datetime.now().strftime("%c") + ": Login successful.")
    except: 
        logging.info(datetime.now().strftime("%c") + ": Login failed.")
    # Create the cursor
    cur = conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
    return cur


def main():
    """Connects to a SQL database to push a data partition for storage.

    parameter argv[1]  32-bit integer ASN of target AS
    parameter argv[2]  CIDR format ipv4 address for target prefix
    parameter argv[3]  32-bit integer ASN of target prefix origin
    """
    if len(sys.argv) != 4:
        print("Usage: traceback.py <AS> <prefix> <origin>", file=sys.stderr)
        sys.exit(-1)
                            
    # Logging config
    logging.basicConfig(level=logging.INFO, filename=LOG_LOC + t.strftime("%d_%m_%Y"))
    logging.info(datetime.now().strftime("%c") + ": Traceback Start...")
    
    # Create a cursor for SQL Queries
    cursor = connectToDB();

    # Query DB for announcement

    # Trace back the AS path for that announcement


if __name__=="__main__":
    main()
