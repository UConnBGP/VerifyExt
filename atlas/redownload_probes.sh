#!/bin/bash
ripe-atlas probe-search --field id --field asn_v4 --field country --field status --field prefix_v4 --field is_public --field address_v4 --field is_anchor --status 1 --all > all_atlas_probes.txt 
