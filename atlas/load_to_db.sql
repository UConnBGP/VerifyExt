DROP TABLE IF EXISTS atlas_probes;
CREATE TABLE atlas_probes (id bigint primary key, asn bigint, country char(2), is_connected boolean, prefix cidr, is_public bool, address_v4 inet, is_anchor bool);
COPY atlas_probes from '/tmp/all_atlas_probes.csv' with DELIMITER ',' NULL 'None';
