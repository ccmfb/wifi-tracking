import csv
import json
import pickle
import time

from device import Device

import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree


ACTIVE_TIME = 3*60 # If devices is not seen for 3 minutes, it is considered inactive -> probably left the building
ACTIVE_COUNT = 2 # If device is not at least seen 2 times, it is considered inactive -> probably only passing through


def generate_refined_data(batch, first_batch=False):
    # reset index of batch
    batch = batch.reset_index(drop=True)

    #   _start = time.time()

    with open('../data/id_mappings/floorId_to_mapId.json', 'r') as file:
        floorId_to_mapId = json.load(file)
        mapId_to_floorId = {v: k for k, v in floorId_to_mapId.items()}

    with open('../data/zValue_to_pValue.json', 'r') as file:
        zValue_to_pValue = json.load(file)
        zValue_to_pValue = {float(k): v for k, v in zValue_to_pValue.items()}

    if first_batch:
        recent_devices = {} # Load from .pkl, format is {mac: Device}
    else:
        with open('../data/objects/recent_devices.pkl', 'rb') as file:
            recent_devices = pickle.load(file)

    devices_in_batch = {}

    with open('../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
        floorId_to_roomIds = json.load(file)

    with open('../data/objects/room_geometries.pkl', 'rb') as file:
        room_geometries = pickle.load(file)

    with open('../data/objects/floor_trees.pkl', 'rb') as file:
        floor_trees = pickle.load(file)


    #   _stop = time.time()
    #   print(f'Loading data took {_stop - _start:.2f} seconds')
    #   _start = time.time()


    # Data to collect
    timestamps = batch['timestamp'].to_list()
    timestamp = timestamps[0]
    data_batch_timestamp = [int(timestamp) for _ in range(len(batch))]
    data_mac = []
    data_x, data_y = [], []
    data_rssi = []
    data_floor_id = []
    data_room_id = []


    # Loading devices in current batch
    for i in range(len(batch)):

        if batch['mac'][i] not in recent_devices:
            recent_devices[batch['mac'][i]] = Device(batch['mac'][i])

        current_device = recent_devices[batch['mac'][i]]
        if batch['map_id'][i] not in mapId_to_floorId:
            print(f'Floor not found for mapId {batch["map_id"][i]}')
            continue

        floor_id = mapId_to_floorId[batch['map_id'][i]]
        current_device.add_data(
            batch['x'][i],
            batch['y'][i],
            batch['rssi'][i],
            batch['timestamp'][i],
            floor_id
        )

        if current_device.mac not in devices_in_batch:
            devices_in_batch[current_device.mac] = current_device



    for device in devices_in_batch.values():
        
        if device.timestamps[-1] < timestamps[-1] - ACTIVE_TIME:
            continue

        if len(device.positions) < ACTIVE_COUNT:
            continue

        if device.floor_ids[-1] != device.floor_ids[-2]:
            continue

        device.update_position(zValue_to_pValue)

        floor_id = device.floor_ids[-1]
        floor_tree = floor_trees[floor_id]
        room_ids = np.array(floorId_to_roomIds[floor_id])

        point = Point(device.x, device.y)
        matches = room_ids.take(floor_tree.query(point))

        room_id = 'None'
        for room_id_ in matches:
            room_geometry = room_geometries[room_id_]

            if room_geometry.contains(point):
                room_id = room_id_
                break

        data_mac.append(device.mac)
        data_x.append(device.x)
        data_y.append(device.y)
        data_rssi.append(device.rssi_values[-1])
        data_floor_id.append(floor_id)
        data_room_id.append(room_id)

    #   _stop = time.time()
    #   print(f'Processing data took {_stop - _start:.2f} seconds')
    #   _start = time.time()

    data = [
        data_batch_timestamp,
        data_mac,
        data_x,
        data_y,
        data_rssi,
        data_floor_id,
        data_room_id
    ]
    transposed_data = list(map(list, zip(*data)))

    with open('../data/data_refined.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(transposed_data)

    # Updating recent devices
    recent_devices.update(devices_in_batch)
    new_recent_devices = {}

    for mac, device in recent_devices.items():
        if device.timestamps[-1] > timestamps[-1] - 60*20:
            new_recent_devices[mac] = device

    with open('../data/objects/recent_devices.pkl', 'wb') as file:
        pickle.dump(new_recent_devices, file)

    #   _stop = time.time()
    #   print(f'Writing data took {_stop - _start:.2f} seconds')
