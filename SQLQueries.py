# Counts for collectors’s prefixes
sql_collectors = "CREATE TABLE all_collector_stats AS 
SELECT as_path[1] asn, 
       COUNT(DISTINCT (prefix)) prefix_only, 
       COUNT(DISTINCT (prefix, origin)) prefix_origin, 
       COUNT(DISTINCT (prefix, as_path)) prefix_path 
FROM mrt_w_roas GROUP BY as_path[1] ORDER BY prefix_path DESC;"

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

# Good Collectors
sql_good = "CREATE TABLE collector_conn_good AS SELECT * FROM all_collector_stats WHERE prefix_only > 100000 AND prefix_only = prefix_path;"

# Verifiable Prefixes
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
WHERE count = 189;"

# Verifiable Collectors by most peer
sql_peer = "CREATE TABLE verifiable_asns_peer AS SELECT asn FROM collector_conn_good ORDER BY num_peers DESC LIMIT 100;"

# Verifiable Collectors by most customers
sql_cust = "CREATE TABLE verifiable_asns_customer AS SELECT asn FROM collector_conn_good ORDER BY num_customers DESC LIMIT 100;"

# Select mrt_small table (1000 random good prefixes)
sql_mrt_small = "CREATE TABLE mrt_small_b AS 
SELECT m.time, m.prefix, m.as_path, m.origin 
FROM (SELECT prefix 
      FROM (SELECT DISTINCT prefix 
	    FROM verifiable_prefixes) AS foo 
      ORDER BY RANDOM() LIMIT 1000) AS r,
     mrt_w_roas m
WHERE m.prefix=r.prefix;"

# Select trial ASNs
sql_ctrl = "SELECT asn FROM verifiable_asns_peer ORDER BY RANDOM() LIMIT 10"
