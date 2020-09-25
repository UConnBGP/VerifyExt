#!/bin/bash

# 1 and 2: remove the b and the quotes
# 3 through 6: Map the connection status to true/false
# 7, 8, and 9: Remove the column headers and last line
# 10: remove emtpy lines
# 11: remove disconnected probes
# 12, 13, and 14: Fill in 'None' for missing values
# 15, 16: Map the binary values for is_public and is_probe to true/false
# 17: Replace spaces with commas
# 18: Remove trailing comma

sed -e "s/^b'//" \
    -e "s/'$//" \
    -e 's/Never Connected/false/' \
    -e 's/Connected/true/' \
    -e 's/Abandoned/false/' \
    -e 's/Disconnected/false/' \
    -e '/=\+/d' \
    -e '/ID.*/d' \
    -e '/Showing/d' \
    -e '/^$/d' \
    -e '/false/d' \
    -e 's/^\([[:digit:]]\+\) \+\([[:alpha:]][[:alpha:]]\)/\1,None,\2/' \
    -e 's/^\([[:digit:]]\+ \+[[:digit:]]\+\) \+\(true\)/\1,None,\2/' \
    -e 's/^\([[:digit:]]\+,None,\)\+\(true\)/\1None,\2/' \
    -e 's/\\xe2\\x9c\\x98/false/g' \
    -e 's/\\xe2\\x9c\\x94/true/g' \
    -e 's/[[:space:]]\+/,/g' \
    -e 's/,$//' all_atlas_probes.txt
