import datetime
from lib_bgp_data import MRT_Parser

# Current epoch time
epoch_time = int(datetime.datetime.now().timestamp())
# Epoch minus 12 hours
epoch_start = epoch_time - 43200

# RIPE
#ripe_collectors = ["rrc00","rrc01","rrc03","rrc04","rrc05","rrc06","rrc07""rrc10","rrc11","rrc12","rrc13","rrc14","rrc15","rrc16","rrc17","rrc18","rrc19","rrc20","rrc21","rrc22","rrc23"]

# Minus rrc00
ripe_collectors = ["rrc01","rrc03","rrc04","rrc05","rrc06","rrc07""rrc10","rrc11","rrc12","rrc13","rrc14","rrc15","rrc16","rrc17","rrc18","rrc19","rrc20","rrc21","rrc22","rrc23"]

# Routeview
routeview_collectors = ["route-views2", "route-views3", "route-views4", "route-views6", "route-views.eqix", "route-views.isc", "route-views.kixp", "route-views.jinx", "route-views.linx", "route-views.telxatl", "route-views.wide", "route-views.sydney", "route-views.saopaulo", "route-views.nwax", "route-views.perth", "route-views.sg", "route-views.sfmix", "route-views.soxrs", "route-views.chicago", "route-views.napafrica", "route-views.flix", "route-views.chile", "route-views.amsix"]

collectors = ripe_collectors + route_collectors

# Friday, June 21, 2019 12:00:00 AM == 1561075200
MRT_Parser().parse_files(start = 1561075200,
                         end = 156111840)
                         api_param_mods = {"collector": "rrc00",
                                            "types": ['ribs']})
