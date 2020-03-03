 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module defines the Querier class."""

__version__ = '0.5'
__author__ = 'James Breslin'

import sys
import psycopg2
import psycopg2.extras
import shutil
from configparser import ConfigParser
from datetime import datetime


class Querier:
    
    def __init__(self):
        """Parameters:
        asn  A string or int representation of 32 bit ASN.
        origin_only  A integer to select extrapolator data.
        """
        CONFIG_LOC = r"/etc/bgp/bgp.conf"

    def connect_to_db(self):
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
        # Return connection
        return conn

    def collectors_tbl(self, cursor):
        # Counts for collectors’s prefixes
        print(datetime.now().strftime("%c") + ": Creating collector quality table...")
        sql_collectors = "CREATE TABLE collector_quality AS \
        SELECT as_path[1] asn, \
               COUNT(DISTINCT (prefix)) prefix_only, \
               COUNT(DISTINCT (prefix, origin)) prefix_origin, \
               COUNT(DISTINCT (prefix, as_path)) prefix_path \
        FROM mrt_announcements GROUP BY as_path[1] ORDER BY prefix_path DESC;"
        cursor.execute(sql_collectors)
        return sql_collectors

    def collectors_good_tbl(self, cursor):
        # Good Collectors
        print(datetime.now().strftime("%c") + ": Creating good collectors table...")
        sql_good = "CREATE TABLE collector_good AS \
        SELECT * FROM collector_quality \
        WHERE prefix_only > 100000 AND prefix_only = prefix_path;"
        cursor.execute(sql_good)
        return sql_good

    def select_num_collectors(self, cursor):
        # Select the number of good collectors
        sql_num = "SELECT COUNT(*) FROM collector_good"
        return sql_num

    def collectors_conn_tbl(self, cursor):
        # Collector Caida Connectivity
        print(datetime.now().strftime("%c") + ": Creating collector connectivity table...")
        sql_conn = "CREATE TABLE collector_connectivity AS ( \
        SELECT ases.asn AS asn, \
            COALESCE(prov.prov_conn, 0) AS num_customers, \
            COALESCE(cust.cust_conn, 0) AS num_providers, \
            COALESCE(p1.peer_conn, 0) + COALESCE(p2.peer_conn, 0) AS num_peers \
        FROM collector_good AS ases \
        LEFT JOIN ( \
        SELECT cp.provider_as AS asn, \
            COUNT(cp.provider_as) AS prov_conn \
        FROM customer_providers AS cp GROUP BY cp.provider_as) AS prov \
        ON ases.asn = prov.asn \
        LEFT JOIN ( \
        SELECT cp.customer_as AS asn, \
            COUNT(cp.customer_as) AS cust_conn \
        FROM customer_providers AS cp GROUP BY cp.customer_as) AS cust \
            ON ases.asn = cust.asn \
            LEFT JOIN ( \
                SELECT p.peer_as_1 AS asn, \
                       COUNT(p.peer_as_1) AS peer_conn \
        FROM peers AS p GROUP BY p.peer_as_1) AS p1 \
            ON ases.asn = p1.asn \
            LEFT JOIN ( \
                SELECT p.peer_as_2 AS asn, \
                       COUNT(p.peer_as_2) AS peer_conn \
        FROM peers AS p GROUP BY p.peer_as_2) AS p2 \
            ON ases.asn = p2.asn \
        );"
        cursor.execute(sql_conn)
        return sql_conn

    def verifiable_collector_tbl(self, cursor):
        # Verifiable Collectors by most peer
        print(datetime.now().strftime("%c") + ": Creating verifiable collectors table...")
        sql_peer = "CREATE TABLE collector_verifiable AS \
        SELECT asn FROM collector_connectivity \
        ORDER BY num_peers DESC LIMIT 100;"
        cursor.execute(sql_peer)
        return sql_peer

    def verifiable_prefix_tbl(self, cursor, n):
        # Verifiable Prefixes
        print(datetime.now().strftime("%c") + ": Creating verifiable prefixes table...")
        sql_prefixes = "CREATE TABLE prefix_verifiable_probes AS \
        SELECT prefix \
        FROM (SELECT mrt.prefix, \
                     COUNT(mrt.prefix) AS count \
              FROM mrt_announcements AS mrt \
              INNER JOIN (SELECT asn FROM probes_verifiable) \
                          AS c \
              ON mrt.as_path[1] = c.asn GROUP BY mrt.prefix ORDER BY count DESC) \
              AS foo \
        WHERE count >= 32;"
        cursor.execute(sql_prefixes)
        return sql_prefixes

    def mrt_small_tbl(self, cursor, n):
        # Select mrt_small table (1000 random good prefixes)
        print(datetime.now().strftime("%c") + ": Creating mrt_small table...")
        sql_mrt_small = "CREATE TABLE mrt_small_probes AS \
        SELECT m.time, m.prefix, m.as_path, m.origin \
        FROM (SELECT prefix \
              FROM (SELECT DISTINCT prefix \
                    FROM prefix_verifiable_probes) AS foo \
              ORDER BY RANDOM() LIMIT 1000) AS r, \
             mrt_announcements m \
        WHERE m.prefix=r.prefix;"
        cursor.execute(sql_mrt_small)
        return sql_mrt_small

    def ctrl_tbl(self, cursor, n):
        # Select trial ASNs
        print(datetime.now().strftime("%c") + ": Creating control collectors table...")
        sql_ctrl = "CREATE TABLE ctrl_coll_probes AS \
        SELECT asn FROM probes_verifiable \
        ORDER BY RANDOM() LIMIT 25"
        cursor.execute(sql_ctrl)
        return sql_ctrl

def main():
    """Generates data tables for verification.

    Parameters:
    argv[1]  # of prefix
    argv[2]  # of collectors
    """    

    if len(sys.argv) != 3:
        print("Usage: sql_querier.py <#prefixes> <#collectors>", file=sys.stderr)
        sys.exit(-1)
    
    q = Querier()
    conn = q.connect_to_db()
    cur = conn.cursor()

    #q.collectors_tbl(cur)
    #q.collectors_good_tbl(cur)
    #q.collectors_conn_tbl(cur)
    #q.verifiable_collector_tbl(cur)
    q.verifiable_prefix_tbl(cur, 1)
    q.mrt_small_tbl(cur, 1000)
    q.ctrl_tbl(cur, 25)
    
    cur.close()
    conn.commit()

    if conn is not None:
        conn.close()
    
if __name__ == "__main__":
    main()
