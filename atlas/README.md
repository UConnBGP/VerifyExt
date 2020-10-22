# Download and save Atlas probes to the database

To download a list of all active probes and load them into the database, run

```
$ ./download_and_load_db.sh
```

This will take about 30 minutes. The database table will be called atlas_probes
and it will have the following schema. 

```
    Column    |     Type     | Nullable |
--------------+--------------+----------+
 id           | bigint       | not null |
 asn          | bigint       |          |
 country      | character(2) |          |
 is_connected | boolean      |          |
 prefix       | cidr         |          |
 is_public    | boolean      |          |
 address_v4   | inet         |          |
 is_anchor    | boolean      |          |
Indexes:
    "atlas_probes_pkey" PRIMARY KEY, btree (id)
```

## Dependencies

```
$ pip install ripe.atlas.tools
```

## Notes

The script will save two artifacts: list of probes in all_atlas_probes.txt and
a csv of probes in all_atlas_probes.csv. The txt file is human readable, as it
is the direct output of the ripe-atlas probe-search command. This text file is
converted to csv using the generate_probes_csv.sh script, which uses regular
expressions to reformat the data for insertion into the database. This csv
format is also useful for analysis in Excel. 
