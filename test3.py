#!/usr/bin/python3

import random

def emulate_packet_loss(pdrop):
    r = random.random()
    print(str(r))
    if (r > pdrop):
        return False
    else:
        return True

if __name__ == "__main__":
    random.seed(1)
    i = 0
    while (i < 10):
        # r = random()
        # print(str(r))
        print(str(emulate_packet_loss(0.5)))
        i += 1