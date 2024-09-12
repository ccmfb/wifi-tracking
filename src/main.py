import csv
import json
import pickle

from device import Device
from data_api import Data_API

import sqlite3
from tqdm import tqdm
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree


ACTIVE_TIME = 3*60 # If devices is not seen for 3 minutes, it is considered inactive -> probably left the building
ACTIVE_COUNT = 2 # If device is not at least seen 2 times, it is considered inactive -> probably only passing through


def generate_refined_data(batch: pd.DataFrame, first_batch: bool = False) -> None:
    '''
    Generate refined data from the batch data, i.e. the data with optimised accuracy and room information.
    
    Args:
        batch (pd.DataFrame): Batch data.
        first_batch (bool): If the batch is the first batch.
        
    Returns:
        None
    '''

    batch = batch.reset_index(drop=True)

    mapId_to_floorId = get_mapId_to_floorId()
    zValue_to_pValue = get_zValue_to_pValue()

    floorId_to_roomIds = get_floorId_to_roomIds()
    room_geometries = get_room_geometries()
    floor_trees = get_floor_trees()

    # Get recent devices
    recent_devices = get_recent_devices(first_batch)
    # Loading devices in batch
    devices_in_batch, recent_devices = load_devices_in_batch(batch, recent_devices, mapId_to_floorId)

    # Populate data
    timestamps = batch['timestamp'].to_list()
    timestamp = int(timestamps[-1])
    data = get_refined_data(devices_in_batch, timestamp, zValue_to_pValue, floorId_to_roomIds, room_geometries, floor_trees)

    # Write to sqlite database
    add_to_db(data)

    # Save recent devices
    save_recent_devices(recent_devices, timestamp)


def get_refined_data(devices_in_batch: dict, timestamp: int, zValue_to_pValue: dict, floorId_to_roomIds: dict, room_geometries: dict, floor_trees: dict) -> dict:
    '''
    Get refined data from the devices in the batch.
    
    Args:
        devices_in_batch (dict): Devices in the batch.
        timestamp (int): Timestamp of the data.
        zValue_to_pValue (dict): Mapping of z-values to p-values.
        floorId_to_roomIds (dict): Mapping of floor IDs to room IDs.
        room_geometries (dict): Room geometries.
        floor_trees (dict): Floor trees.
        
    Returns:
        dict: Refined data.
    '''

    data_timestamps = [timestamp for _ in range(len(devices_in_batch))]
    data_mac = []
    data_x, data_y = [], []
    data_error = []
    data_rssi = []
    data_floor_id = []
    data_room_id = []

    for device in devices_in_batch.values():

        if not device.is_active(ACTIVE_TIME, ACTIVE_COUNT):
            continue

        floor_id = int(device.floor_ids[-1])
        if floor_id not in floor_trees.keys():
            continue

        device.update_position(zValue_to_pValue)

        floor_tree = floor_trees[floor_id]
        room_ids = np.array(floorId_to_roomIds[str(floor_id)])

        point = Point(device.x, device.y)
        matches = room_ids.take(floor_tree.query(point))

        room_id = 'None'
        for current_room_id in matches:
            room_geometry = room_geometries[current_room_id]
            if room_geometry.contains(point):
                room_id = current_room_id
                break

        data_mac.append(device.mac)
        data_x.append(device.x)
        data_y.append(device.y)
        data_error.append(device.error)
        data_rssi.append(device.rssi_values[-1])
        data_floor_id.append(str(floor_id))
        data_room_id.append(str(room_id))

    data = [
        data_timestamps,
        data_mac,
        data_x,
        data_y,
        data_error,
        data_rssi,
        data_floor_id,
        data_room_id
    ]
    data = list(map(list, zip(*data)))

    return data


def load_devices_in_batch(batch: pd.DataFrame, recent_devices: dict, mapId_to_floorId: dict) -> tuple:
    '''
    Returns list of devices in batch as well as updated recent devices.
    
    Args:
        batch (pd.DataFrame): Batch data.
        recent_devices (dict): Recent devices.
        mapId_to_floorId (dict): Mapping of map IDs to floor IDs.
        
    Returns:
        dict: Devices in the batch.
    '''

    devices_in_batch = {}
    rec_devices = recent_devices.copy()

    for i in range(len(batch)):

        if batch['map_id'][i] not in mapId_to_floorId:
            print(f'Floor not found for mapId {batch["map_id"][i]}')
            continue

        if batch['mac'][i] not in rec_devices:
            rec_devices[batch['mac'][i]] = Device(batch['mac'][i])

        current_device = rec_devices[batch['mac'][i]]

        floor_id = mapId_to_floorId[batch['map_id'][i]]
        current_device.add_data(
            float(batch['x'][i]),
            float(batch['y'][i]),
            float(batch['rssi'][i]),
            int(batch['timestamp'][i]),
            int(floor_id)
        )

        if current_device.mac not in devices_in_batch:
            devices_in_batch[current_device.mac] = current_device

    return devices_in_batch, rec_devices 


def add_to_db(data: list) -> None:
    conn = sqlite3.connect('../data/refined_data.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS data_refined (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        mac TEXT,
        x REAL,
        y REAL,
        error REAL,
        rssi INTEGER,
        floor_id TEXT,
        room_id TEXT
    )
    ''')

    cursor.executemany("INSERT INTO data_refined (timestamp, mac, x, y, error, rssi, floor_id, room_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data)

    conn.commit()
    conn.close()


def save_recent_devices(recent_devices: dict, timestamp: int) -> None:
    '''
    Save recent devices and sort out the inactive ones.
    
    Args:
        recent_devices (dict): Recent devices.
        timestamp (int): Timestamp of the data.
        
    Returns:
        None
    '''
    assert type(recent_devices) == dict and type(timestamp) == int, 'Invalid data types'
    new_recent_devices = {}

    for mac, device in recent_devices.items():
        if device.timestamps[-1] > timestamp - 60*20:
            new_recent_devices[mac] = device

    with open('../data/objects/recent_devices.pkl', 'wb') as file:
        pickle.dump(new_recent_devices, file)


def get_mapId_to_floorId() -> dict:
    '''
    Get mapping of map IDs to floor IDs.
    
    Returns:
        dict: Mapping of map IDs to floor IDs.
    '''

    with open('../data/id_mappings/floorId_to_mapId.json', 'r') as file:
        floorId_to_mapId = json.load(file)
        mapId_to_floorId = {v: k for k, v in floorId_to_mapId.items()}

    return mapId_to_floorId


def get_zValue_to_pValue() -> dict:
    '''
    Get mapping of z-values to p-values.
    
    Returns:
        dict: Mapping of z-values to p-values.
    '''

    with open('../data/zValue_to_pValue.json', 'r') as file:
        zValue_to_pValue = json.load(file)
        zValue_to_pValue = {float(k): v for k, v in zValue_to_pValue.items()}

    return zValue_to_pValue


def get_recent_devices(first_batch: bool) -> dict:
    '''
    Get recent devices.
    
    Args:
        first_batch (bool): If the batch is the first batch.
    
    Returns:
        dict: Recent devices.
    '''

    if first_batch:
        return {}
    else:
        with open('../data/objects/recent_devices.pkl', 'rb') as file:
            recent_devices = pickle.load(file)

        return recent_devices


def get_floorId_to_roomIds() -> dict:
    '''
    Get mapping of floor IDs to room IDs.
    
    Returns:
        dict: Mapping of floor IDs to room IDs.
    '''

    with open('../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
        floorId_to_roomIds = json.load(file)

    return floorId_to_roomIds


def get_room_geometries() -> dict:
    '''
    Get room geometries.
    
    Returns:
        dict: Room geometries.
    '''

    with open('../data/objects/room_geometries.pkl', 'rb') as file:
        room_geometries = pickle.load(file)

    return room_geometries


def get_floor_trees() -> dict:
    '''
    Get floor trees.
    
    Returns:
        dict: Floor trees.
    '''
    
    with open('../data/objects/floor_trees.pkl', 'rb') as file:
        floor_trees = pickle.load(file)

    return floor_trees


if __name__ == '__main__':
    data_api = Data_API()

    batch = data_api.get_last_batch()
    first_batch = True

    generate_refined_data(batch=batch, first_batch=first_batch)