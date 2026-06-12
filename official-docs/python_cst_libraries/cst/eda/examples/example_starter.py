# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.


import os
from os.path import *


def import_file_as_module(path, modname="testmodule.check"):
    import importlib.util
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


thisdir = dirname(abspath(__file__))
demos = [ f for f in os.listdir(thisdir) if f not in __file__ and f.endswith('.py')]

print("\n")
print("-"*40)
print("Which demo to run?: ")
for i,d in enumerate(demos):
    print( f'{i}: {d}')
try:
    s = input("-> Which example (index) to run?: ")
    d = demos[int(s)]
except:
    print("\nERROR: Invalid index")
    import sys
    sys.exit(1)

print()
print("-> Running", d)

import tempfile
outdir = tempfile.mkdtemp(prefix='output_CST_')

mod = import_file_as_module( join(thisdir, d) )
res = mod.main(outdir=outdir)

pass
