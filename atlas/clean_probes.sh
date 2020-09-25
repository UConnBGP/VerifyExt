#!/bin/bash

sed -e "s/^b'//" -e "s/'$//" -e 's/Never Connected/false/' -e 's/Connected/true/' -e 's/Abandoned/false/' -e 's/Disconnected/false/'  -e '/=\+/d' -e '/ID.*/d' -e '/Showing/d' -e '/^$/d' -e '/false/d' -e 's/^\([[:digit:]]\+\) \+\([[:alpha:]][[:alpha:]]\)/\1,,\2/' -e 's/^\([[:digit:]]\+ \+[[:digit:]]\+\) \+\(true\)/\1,,\2/' -e 's/\\xe2\\x9c\\x98/false/g' -e 's/\\xe2\\x9c\\x94/true/g' -e 's/[[:space:]]\+/,/g' -e 's/,$//' all_atlas_probes.txt
