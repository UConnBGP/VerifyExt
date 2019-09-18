from verifier import Verifier

def main():
    ver_list = ["12350", "13030", "14537", "202032", "49432", "5413", "57264", "58057", "6233", "8220"]
    for AS in ver_list:
        v = Verifier(AS, 0)
        v.run()
        v.output()

        v_oo = Verifier(AS, 1)
        v_oo.run()
        v_oo.output()

if __name__ == "__main__":
    main()
