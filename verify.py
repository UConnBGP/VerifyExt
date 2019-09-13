

def main():
    """Connects to a SQL database to push a data partition for storage.    
    
    Parameters:
    argv[1]  32-bit integer ASN of target AS
    argv[2]  Origin Only Boolean
    """    

    if len(sys.argv) != 3:
        print("Usage: traceback.py <AS> <OOBool>", file=sys.stderr)
        sys.exit(-1)
    
    # Set table names
    ctrl_AS = str(sys.argv[1])
    global TABLE_NAME;
    global MRT_TABLE_NAME;
    if (int(sys.argv[2]) == 0):
        print("Setting MRT verification.")
        TABLE_NAME = "verify_data_" + ctrl_AS
        MRT_TABLE_NAME = r"verify_ctrl_" + ctrl_AS + "_distinct"
    else:
        print("Setting origin only verification.")
        TABLE_NAME = "verify_data_" + ctrl_AS + "_oo"
        MRT_TABLE_NAME = r"verify_ctrl_" + ctrl_AS + "_distinct"

    # Logging config 
    logging.basicConfig(level=logging.INFO, filename=LOG_LOC + datetime.now().strftime("%c"))
    logging.info(datetime.now().strftime("%c") + ": Verification Start...")
    
    # Create a cursor for SQL Queries
    cursor = connectToDB();

    # Counter to verify correctness
    correct_hops = 0
    incorrect_hops = 0
    ver_count = 0
    levenshtein_d = 0
    levenshtein_avg = 0

    # Trace back the AS path for that announcement
    # Get the mrt set
    print("Getting MRT announcements...")
    # Dict = {prefix: (as_path, origin)}
    mrt_set = get_mrt_ann(cursor, sys.argv[1])
    
    ver_pref = len(mrt_set)
    print("Performing verification for " + str(ver_pref) + " prefixes")
    for ann in mrt_set:
        origin_str = str(mrt_set[ann][1])
        
        # Get the propagted announcements
        # Dict = {current ASN: received from ASN}
        origin_set = get_ext_ann(cursor, ann, origin_str)
        
        if origin_set == None:
            ver_pref -= 1
            print(str(ann) + " " + str(origin_str) + " is not present in results.")
            continue;
        
        # Recreate the extrapolated AS path
        ext_as_path = traceback(origin_set, ctrl_AS, mrt_set[ann][1], [int(ctrl_AS)])
        
        # If extrapolated path is complete
        if (ext_as_path != None):
            # Get the MRT announcement path
            reported_as_path = mrt_set[ann][0]
            # Compare paths
            hop_results = naive_compare_btf(ext_as_path, reported_as_path)
            correct_hops += hop_results[0]
            incorrect_hops += hop_results[1]

            # Levenshtein compare
            ver_count += 1
            cur_distance = levenshtein(reported_as_path, ext_as_path)
            levenshtein_avg = levenshtein_avg + (cur_distance - levenshtein_avg) / ver_count
            levenshtein_d += cur_distance
        else:
            # Incomplete extrapolated path
            ver_pref -= 1
            print(str(ann) + " " + str(origin_str) + " does not have complete path.")
    
    # K is success up to kth hop
    print(k)
    # L is success until the kth hop
    print(l)
    print("Total Levenshtein Distance: " + str(levenshtein_d))
    print("Levenshtein Average: " + str(levenshtein_avg))
    corr_hops_str = str(correct_hops)
    incorr_hops_str = str(incorrect_hops)
    print("Verifiable prefixes: " + str(ver_pref))
    result_str = "Correct Hops: " + corr_hops_str + " Incorrect Hops: " + incorr_hops_str
    print(result_str)


if __name__ == "__main__":
    main()
