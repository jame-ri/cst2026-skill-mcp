# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

import os

def parse_layermap_file(file, comment_char='#'):
    assert os.path.exists(file)
    with open(file, 'r') as flm:
        lines = flm.readlines()

    layer_name_map = {}
    purpose_name_map = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(comment_char):
            continue

        # LayerName LayerPurpose gdsLayer gdsPurpose Material MaskNumber
        parts = line.split()
        if not len(parts) >= 4:
            continue

        LayerName, LayerPurpose, gdsLayer, gdsPurpose = parts[0:4]        

        layer_name_map[LayerName] = int(gdsLayer)
        purpose_name_map[LayerPurpose] = int(gdsPurpose)

    return layer_name_map, purpose_name_map


def convert_to_json_file(layermap, json_file):
    layer_name_map, purpose_name_map = parse_layermap_file(layermap)
    data = {'layers': layer_name_map, 'purposes': purpose_name_map}
    import json
    with open(json_file, 'w') as f:
        json.dump(data, f)
    

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('layermap', help='The layermap file to be read from')
    parser.add_argument('json_out', help='The result of the conversion stored in json format')

    args = parser.parse_args()

    convert_to_json_file(args.layermap, args.json_out)
