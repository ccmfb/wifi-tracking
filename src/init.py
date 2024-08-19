import os
import pickle
import json
import yaml

from tqdm import tqdm
from shapely.geometry import Polygon
from shapely.strtree import STRtree
import pandas as pd


floor_trees = {}
room_geometries = {}


# Data from floors by id
path = '../data/floorplans-main/floors_by_id'

all_entries = os.listdir(path)
floor_ids = [entry for entry in all_entries if os.path.isdir(os.path.join(path, entry))]


for floor_id in tqdm(floor_ids):

    workspace_path = f"{path}/{floor_id}/workspace.json"
    info_path = f"{path}/{floor_id}/info.json"

    with open(workspace_path, 'r') as file:
        workspace_data = json.load(file)

    with open(info_path, 'r') as file:
        info_data = json.load(file)

    building_id = info_data['buildingId']
    offset_path = f"../data/floorplans-main/buildings_by_id/{building_id}/state.yaml"
    if not os.path.exists(offset_path):
        continue

    with open(offset_path) as file:
        offset_data = yaml.safe_load(file)
        # check if offset is present
        if offset_data['layout'] is None:
            continue
        viewbox = [float(num) for num in offset_data['layout']['viewbox'].split()]
        offset = [-viewbox[0], -viewbox[1]]

    current_polygons = []
    for room in workspace_data:
        room_id = room['id']
        
        room_coords = []
        for coord in room['outline']['coords']:
            room_coords.append((coord['x'] + offset[0], coord['y'] + offset[1])) 
        
        room_polygon = Polygon(room_coords)
        room_geometries[room_id] = room_polygon
        current_polygons.append(room_polygon)

    floor_trees[floor_id] = STRtree(current_polygons)

with open('../data/objects/floor_trees.pkl', 'wb') as file:
    pickle.dump(floor_trees, file)

with open('../data/objects/room_geometries.pkl', 'wb') as file:
    pickle.dump(room_geometries, file)

# ----------------------------------------------------------------------------------------------------------------------

floorId_to_roomIds = {}


for floor_id in tqdm(floor_ids):

    workspace_path = f"{path}/{floor_id}/workspace.json"
    with open(workspace_path, 'r') as file:
        workspace_data = json.load(file)

    room_ids = [room['id'] for room in workspace_data]

    floorId_to_roomIds[floor_id] = room_ids

with open('../data/id_mappings/floorId_to_roomIds.json', 'w') as file:
    json.dump(floorId_to_roomIds, file)


# ----------------------------------------------------------------------------------------------------------------------


data_refined_columns = {
    'timestamp': [], 'mac': [], 'x': [], 'y': [], 'rssi': [], 'floor_id': [], 'room_id': []
}

df_refined = pd.DataFrame(data_refined_columns)
df_refined.to_csv('../data/data_refined.csv', index=False, header=True)