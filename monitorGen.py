import datetime
from lib_bgp_data import MRT_Parser

# Current epoch time
epoch_time = int(datetime.datetime.now().timestamp())
# Epoch minus 12 hours
epoch_start = epoch_time - 43200

ripe_collectors = ["rrc00","rrc01","rrc03","rrc04","rrc05","rrc06","rrc07""rrc10","rrc11","rrc12","rrc13","rrc14","rrc15","rrc16","rrc17","rrc18","rrc19","rrc20","rrc21","rrc22","rrc23"]

# Friday, June 21, 2019 12:00:00 AM == 1561075200
MRT_Parser().parse_files(start = 1561075200,
                         end = 1561118400,
			 api_param_mods = {"collector": "rrc00",
                                            "types": ['ribs']})
