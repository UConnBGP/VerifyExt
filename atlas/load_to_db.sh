#!/bin/bash

./generate_probes_csv.sh > all_atlas_probes.csv
cp all_atlas_probes.csv /tmp/all_atlas_probes.csv
PGPASSWORD=$(sed -e '/^password/!d' -e 's/password = //g' /etc/bgp/bgp.conf | head -n 1)
psql -U bgp_user -h localhost -d bgp -f load_to_db.sql
rm /tmp/all_atlas_probes.csv

