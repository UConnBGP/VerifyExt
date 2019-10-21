from verifier import Verifier

def main():
    collectors_old = [23106, 50304, 395152, 8222, 53364, 8607, 59891, 53013, 6894, 20080, 8492, 28260, 3333, 32709, 12307, 25160, 48362, 15562, 198385, 328474, 16347, 53070, 14630, 32097, 4777, 47422, 6720, 25933, 395766, 5645, 59414, 61832]
    
    collectors_peer = [51405, 35266, 18106, 29140, 28917, 8283, 25220, 50304, 53070, 196753]
    collectors_cust = [47950, 53013, 27446, 680, 45177, 12350, 7660, 198385, 27678, 1351]
    for AS in collectors_old:
        v = Verifier(AS, 0)
        v.run()
        v.output()
        v = None

        v_oo = Verifier(AS, 1)
        v_oo.run()
        v_oo.output()
        v_oo = None

        v_mo = Verifier(AS, 2)
        v_mo.run()
        v_mo.output()


if __name__ == "__main__":
    main()
