import csv
import json
import pickle

from device import Device

from tqdm import tqdm
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree


ACTIVE_TIME = 3*60 # If devices is not seen for 3 minutes, it is considered inactive -> probably left the building
ACTIVE_COUNT = 2 # If device is not at least seen 2 times, it is considered inactive -> probably only passing through


def generate_refined_data(batch: pd.DataFrame, first_batch: bool = False) -> None:
    '''
    Generate refined data from the batch data.
    
    Args:
        batch (pd.DataFrame): Batch data.
        first_batch (bool): If the batch is the first batch.
        
    Returns:
        None
    '''

    batch = batch.reset_index(drop=True)

    mapId_to_floorId = get_mapId_to_floorId()
    zValue_to_pValue = get_zValue_to_pValue()
    recent_devices = get_recent_devices(first_batch)
    floorId_to_roomIds = get_floorId_to_roomIds()
    room_geometries = get_room_geometries()
    floor_trees = get_floor_trees()

    # Loading devices in batch
    devices_in_batch = get_devices_in_batch(batch, recent_devices, mapId_to_floorId)

    # Populate data
    timestamps = batch['timestamp'].to_list()
    timestamp = timestamps[-1]
    data = get_refined_data(devices_in_batch, timestamp, zValue_to_pValue, floorId_to_roomIds, room_geometries, floor_trees)

    # Write to file
    with open('../data/data_refined.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data)

    # Save recent devices
    save_recent_devices(recent_devices, devices_in_batch, timestamp)


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

        device.update_position(zValue_to_pValue)

        floor_id = device.floor_ids[-1]
        floor_tree = floor_trees[floor_id]
        room_ids = np.array(floorId_to_roomIds[floor_id])

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
        data_floor_id.append(floor_id)
        data_room_id.append(room_id)

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


def get_devices_in_batch(batch: pd.DataFrame, recent_devices: dict, mapId_to_floorId: dict) -> dict:
    '''
    Get devices in the batch.
    
    Args:
        batch (pd.DataFrame): Batch data.
        recent_devices (dict): Recent devices.
        mapId_to_floorId (dict): Mapping of map IDs to floor IDs.
        
    Returns:
        dict: Devices in the batch.
    '''

    devices_in_batch = {}
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

    return devices_in_batch


def save_recent_devices(recent_devices: dict, devices_in_batch: dict, timestamp: int) -> None:
    '''
    Save recent devices.
    
    Args:
        recent_devices (dict): Recent devices.
        devices_in_batch (dict): Devices in the batch.
        timestamp (int): Timestamp of the data.
        
    Returns:
        None
    '''

    recent_devices.update(devices_in_batch)
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