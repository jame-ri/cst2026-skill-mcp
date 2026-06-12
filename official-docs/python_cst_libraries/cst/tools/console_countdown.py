# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

import time
import sys
import msvcrt
import math
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("timeout", default=5, nargs="?")

args = parser.parse_args()

N = int(args.timeout)

def wait_for_key():
    start_time = time.time()
    ncountdown = N
    ncountdown_old = -1
    while (elapsed := time.time() - start_time) < N:
        if (ncountdown := math.ceil(N - elapsed)) != ncountdown_old:
            sys.stdout.write(f"Press key to keep console open. Closing in {ncountdown:2}s   \r")
            sys.stdout.flush()
            ncountdown_old = ncountdown

        if msvcrt.kbhit():
            print("\nKey pressed. Console will remain open.")
            return True
        time.sleep(0.1)
    return False


if not wait_for_key():
    print("\nNo key pressed. Exiting...")
    time.sleep(1)
    exit(1)

exit(0)
