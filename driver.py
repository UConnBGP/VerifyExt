from verifier import Verifier

def main():
    a_list = ["12350", "13030", "14537", "202032", "49432", "5413", "57264", "58057", "6233", "8220"]
    b_list = [267613, 15547, 2497, 1403, 20811, 49605, 3130, 293, 12779, 6762, 20764, 6667, 3549, 47692, 3257, 41095, 59605, 286, 6453, 1103]
    for AS in b_list:
        v = Verifier(AS, 0)
        v.run()
        v.output()

        v_oo = Verifier(AS, 1)
        v_oo.run()
        v_oo.output()

if __name__ == "__main__":
    main()
