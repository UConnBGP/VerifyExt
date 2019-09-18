import cProfile
from verifier import Verifier

def main():
    ver_list = ["12350", "13030", "14537", "202032", "49432", "5413", "57264", "58057", "6233", "8220"]
    for AS in ver_list:
        v = Verifier(AS, 0)
        cProfile.runctx('v.run()', globals(), locals())

if __name__ == "__main__":
    main()
