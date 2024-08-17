'''
Script to generate occupancy data from the refined data.
'''

import json
import pandas as pd
from tqdm import tqdm


with open('../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
    floorId_to_roomIds = json.load(file)

#   roomId_to_floorId = {}
#   for floor_id, room_ids in floorId_to_roomIds.items():
    #   for room_id in room_ids:
        #   roomId_to_floorId[room_id] = floor_id

df = pd.read_csv('../data/data_refined.csv')
timestamps_unique = df['timestamp'].unique()


batches = []
for timestamp in timestamps_unique:
    batch = df[df['timestamp'] == timestamp]
    batches.append(batch)


data_timestamp = []
data_count = []

data_room_id = []
data_room_name = []
data_room_popular_name = []
data_room_gross_area = []
data_room_net_area = []
data_room_type_id = []
data_room_type_name = []

data_floor_id = []
data_floor_name = []
data_floor_popular_name = []

data_building_id = []
data_building_name = []
data_building_popular_name = []


for batch in tqdm(batches):
    room_ids = batch['room_id'].unique()

    for room_id in room_ids:
        if room_id == 'None': continue

        room = batch[batch['room_id'] == room_id]
        count = len(room)
        if count == 0: continue

        timestamp = room['timestamp'].to_list()[0]
        floor_id = room['floor_id'].to_list()[0]

        path_floor_info = f'../data/floorplans-main/floors_by_id/{floor_id}/info.json'
        with open(path_floor_info, 'r') as file:
            floor_info = json.load(file)

        building_id = floor_info['buildingId']
        building_name = floor_info['buildingName']
        building_popular_name = floor_info['buildingPopularName']

        floor_name = floor_info['name']
        floor_popular_name = floor_info['popularName']

        path_floor_workspaces = f'../data/floorplans-main/floors_by_id/{floor_id}/workspace.json'
        with open(path_floor_workspaces, 'r') as file:
            floor_workspaces = json.load(file)

        workspace_data = None
        for workspace in floor_workspaces:
            if workspace['id'] == room_id:
                workspace_data = workspace
                break

        room_name = workspace_data['name']
        room_popular_name = workspace_data['popularName']
        room_gross_area = workspace_data['grossarea']
        room_net_area = workspace_data['netarea']
        room_type_id = workspace_data['typeId']
        room_type_name = workspace_data['typeName']


        data_timestamp.append(int(timestamp))
        data_count.append(count)

        data_room_id.append(int(room_id))
        data_room_name.append(room_name)
        data_room_popular_name.append(room_popular_name)
        data_room_gross_area.append(room_gross_area)
        data_room_net_area.append(room_net_area)
        data_room_type_id.append(room_type_id)
        data_room_type_name.append(room_type_name)

        data_floor_id.append(int(floor_id))
        data_floor_name.append(floor_name)
        data_floor_popular_name.append(floor_popular_name)

        data_building_id.append(int(building_id))
        data_building_name.append(building_name)
        data_building_popular_name.append(building_popular_name)



data = {
    'timestamp': data_timestamp,
    'count': data_count,
    'room_id': data_room_id,
    'room_name': data_room_name,
    'room_popular_name': data_room_popular_name,
    'room_gross_area': data_room_gross_area,
    'room_net_area': data_room_net_area,
    'room_type_id': data_room_type_id,
    'room_type_name': data_room_type_name,
    'floor_id': data_floor_id,
    'floor_name': data_floor_name,
    'floor_popular_name': data_floor_popular_name,
    'building_id': data_building_id,
    'building_name': data_building_name,
    'building_popular_name': data_building_popular_name
}

occupancy = pd.DataFrame(data)
occupancy.to_csv('../data/occupancy.csv', index=False)
