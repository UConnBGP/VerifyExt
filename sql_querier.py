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
        # Create the cursor
        cur = conn.cursor("ver_cursor")
        return cur

    def collectors_tbl():
        # Counts for collectors’s prefixes
        sql_collectors = "CREATE TABLE all_collector_stats AS 
        SELECT as_path[1] asn, 
               COUNT(DISTINCT (prefix)) prefix_only, 
               COUNT(DISTINCT (prefix, origin)) prefix_origin, 
               COUNT(DISTINCT (prefix, as_path)) prefix_path 
        FROM mrt_w_roas GROUP BY as_path[1] ORDER BY prefix_path DESC;"
        return sql_collectors

    def collectors_conn_tbl():
        # Collector Caida Connectivity
        sql_conn = "CREATE TABLE collector_connectivity AS (
        SELECT ases.asn AS asn,                                                                            
            COALESCE(prov.prov_conn, 0) AS num_customers,
            COALESCE(cust.cust_conn, 0) AS num_providers,
            COALESCE(p1.peer_conn, 0) + COALESCE(p2.peer_conn, 0) AS num_peer
        FROM all_collector_stats AS ases
        LEFT JOIN (
        SELECT cp.provider_as AS asn,
            COUNT(cp.provider_as) AS prov_conn
        FROM customer_providers AS cp GROUP BY cp.provider_as) AS prov
        ON ases.asn = prov.asn
        LEFT JOIN (
        SELECT cp.customer_as AS asn,
            COUNT(cp.customer_as) AS cust_conn
        FROM customer_providers AS cp GROUP BY cp.customer_as) AS cust
            ON ases.asn = cust.asn
            LEFT JOIN (
                SELECT p.peer_as_1 AS asn,
                       COUNT(p.peer_as_1) AS peer_conn
        FROM peers AS p GROUP BY p.peer_as_1) AS p1
            ON ases.asn = p1.asn
            LEFT JOIN (
                SELECT p.peer_as_2 AS asn,
                       COUNT(p.peer_as_2) AS peer_conn
        FROM peers AS p GROUP BY p.peer_as_2) AS p2
            ON ases.asn = p2.asn
        );"
        return sql_conn

    def collectors_good_tbl():
        # Good Collectors
        sql_good = "CREATE TABLE collector_conn_good AS 
        SELECT * FROM all_collector_stats 
        WHERE prefix_only > 100000 AND prefix_only = prefix_path;"
        return sql_good

    def verifiable_collector_tbl():
        # Verifiable Collectors by most peer
        sql_peer = "CREATE TABLE verifiable_asns_peer AS 
        SELECT asn FROM collector_conn_good 
        ORDER BY num_peers DESC LIMIT 100;"
        return sql_peer

    def verifiable_prefix_tbl(self, n):
        # Verifiable Prefixes
        # TODO dynamic collector count
        sql_prefixes = "CREATE TABLE verifiable_prefixes AS 
        SELECT prefix 
        FROM (SELECT mrt.prefix, 
                     COUNT(mrt.prefix) AS count 
              FROM mrt_w_roas_v2 AS mrt 
              INNER JOIN (SELECT asn FROM all_asn_stats 
                          WHERE prefix_only > 100000 AND prefix_only = prefix_path) 
                          AS pa 
              ON mrt.as_path[1] = pa.asn GROUP BY mrt.prefix ORDER BY count DESC) 
              AS foo 
        WHERE count >= 189;"
        return sql_prefixes

    def mrt_small_tbl(self, n):
        # Select mrt_small table (1000 random good prefixes)
        sql_mrt_small = "CREATE TABLE mrt_small_b AS 
        SELECT m.time, m.prefix, m.as_path, m.origin 
        FROM (SELECT prefix 
              FROM (SELECT DISTINCT prefix 
                    FROM verifiable_prefixes) AS foo 
              ORDER BY RANDOM() LIMIT 1000) AS r,
             mrt_w_roas m
        WHERE m.prefix=r.prefix;"
        return sql_mrt_small

    def ctrl_tbl(self, n):
        # Select trial ASNs
        sql_ctrl = "CREATE TABLE ctrl_coll AS
        SELECT asn FROM verifiable_asns_peer 
        ORDER BY RANDOM() LIMIT 10"
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

    cursor = q.connect_to_db();
    cursor.execute(q.collectors_tbl())
    cursor.execute(q.collectors_conn_tbl())
    cursor.execute(q.collectors_good_tbl())
    cursor.execute(q.verifiable_collector_tbl())
    cursor.execute(q.verifiable_prefix_tbl())
    cursor.execute(q.mrt_small_tbl(1000))
    cursor.execute(q.ctrl_tbl(20))
    cursor.close()
    
if __name__ == "__main__":
    main()
