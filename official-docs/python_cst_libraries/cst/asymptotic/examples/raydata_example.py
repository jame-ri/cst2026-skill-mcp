# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

#!/usr/bin/env python3
import sys
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from cst.asymptotic import raydata  # make sure you've set your PYTHONPATH


def main():
    """Example routine to analyze ray data in HDF5 file."""
    # Define file to read
    # Use commandline argument, if specified
    if len(sys.argv) > 1:
        filePath = sys.argv[1]
    else:
        dirname = os.path.join(os.path.dirname(__file__))
        filePath = os.path.join(dirname, "data", "raystorage-all-0.h5")

    # Plot only some raypaths to keep the plot clean
    # Use commandline argument, if specified
    if len(sys.argv) > 2:
        everynth = int(sys.argv[2])
    else:
        everynth = 1

    # Read raydata file
    print("Reading raydata file... ")
    rd = raydata.read(filePath)
    print(f"Number of sources in file: {len(rd.sources)}")

    # Operate on first source
    sourceID = 0
    source = rd.sources[sourceID]
    print(f"Showing data for source {source.name}")
    print(f"Total number of rays: {len(source.trees)}")

    # Get average number of segments in trees
    nsegments = np.average([len(list(tree.segments()))
                            for tree in source.trees])
    print(f"Average number of segments: {nsegments:.1f}")

    # Get maximum hitorder for color normalisation
    maxhitorder = max(max(s.hitorder() for s in tree.segments())
                      for tree in source.trees)
    print(f"Maximum hitorder: {maxhitorder}")

    # Count segments of any hitorder
    hitorders = np.zeros(maxhitorder + 1)
    for tree in source.trees:
        for s in tree.segments():
            hitorders[s.hitorder()] += 1
    for order in range(maxhitorder + 1):
        print(f"Segments with hit order {order}: {hitorders[order]:.0f}")

    # Compute average length over all possible ray paths
    avg_pathlength = np.average([
        np.average([sum(s.length() for s in path)
                    for path in tree.paths()])
        for tree in source.trees])
    print(f"Average pathlength: {avg_pathlength:.2f}m")

    # Initialize plotting
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    norm = mpl.colors.Normalize(vmin=0, vmax=maxhitorder)
    cmap = mpl.cm.plasma
    mapper = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    plottrees = source.trees[::everynth]

    # Plot initial hits
    pos1 = np.array([tree.position2() for tree in plottrees])
    ax.scatter3D(*pos1.T, depthshade=False, marker='.', color=[1, 0, 0, 0.8])

    # Plot raypath segments; color by hitorder
    for tree in plottrees:
        for path in tree.paths():
            # only show rays with exit path
            if not any(s.termination() == raydata.Termination.Exitray
                       for s in path):
                continue
            for s in path:
                ax.plot3D(*s.positions().T, color=mapper.to_rgba(s.hitorder()))

    # Plot a legend
    patches = [mpl.patches.Patch(color=mapper.to_rgba(
        hitorder), label=hitorder) for hitorder in range(maxhitorder + 1)]
    ax.legend(title="Hitorder", handles=patches)

    plt.show()


if __name__ == '__main__':
    main()
