from verifier import Verifier

def main():
    collectors = [47950, 53013, 27446, 680, 45177, 12350, 7660, 198385, 27678, 1351]
    for AS in collectors:
        # full extrapolation verification
        v = Verifier(AS, 0)
        v.run()
        v.output()
        v = None

        # origin only extrapolation verification
        v_oo = Verifier(AS, 1)
        v_oo.run()
        v_oo.output()
        v_oo = None

        # no propagation, mrt only verification
        v_mo = Verifier(AS, 2)
        v_mo.run()
        v_mo.output()


if __name__ == "__main__":
    main()
