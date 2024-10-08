import os
import pickle
import json
import yaml

from pythagoras_api import Pythagoras_API

from tqdm import tqdm
from shapely.geometry import Polygon
from shapely.strtree import STRtree
import pandas as pd


PATH_FLOORPLANS = '../data/floorplans-main'


def init() -> None:
    '''
    Initialise necessary files. These include: room geometries, floor trees, 
    floor to room mappings, and department mappings. Can be run to update the 
    files.

    Returns:
        None
    '''

    api = Pythagoras_API()
    floor_ids = api.get_floor_ids()

    init_saved_objects(floor_ids, api)
    init_floor_to_rooms_mapping(floor_ids, api)
    init_department_mappings(api)
    init_floorId_mapId_mapping()

    print('Initialising necessary files complete.')


def init_saved_objects(floor_ids: list, api: Pythagoras_API) -> None:
    '''
    Generate and save the room geometries and floor trees for each floor.
    
    Args:
        floor_ids (list): List of floor IDs.
        
    Returns:
        None
    '''
    print('Generating room geometries and floor trees...')

    room_geometries = {}
    floor_trees = {}
    
    for floor_id in tqdm(floor_ids):
        data_workspace = api.get_floor_workspace_info(floor_id)
        data_info = api.get_floor_info(floor_id)

        building_id = int(data_info['buildingId'])
        offset = get_floor_offset(building_id)
        
        if offset is None:
            continue

        current_room_geometries, current_floor_tree = generate_room_geometries(data_workspace, offset)
        room_geometries.update(current_room_geometries)
        floor_trees[floor_id] = current_floor_tree

    with open(f'../data/objects/room_geometries.pkl', 'wb') as file:
        pickle.dump(room_geometries, file)

    with open(f'../data/objects/floor_trees.pkl', 'wb') as file:
        pickle.dump(floor_trees, file)


def init_floor_to_rooms_mapping(floor_ids: list, api: Pythagoras_API) -> None:
    '''
    Generate and save the mapping of floor IDs to room IDs.
    
    Args:
        floor_ids (list): List of floor IDs.
        api (API_Requests): API_Requests object.
        
    Returns:
        None
    '''
    print('Generating floor to room mappings...')

    floorId_to_roomIds = {}

    for floor_id in tqdm(floor_ids):
        room_ids = api.get_floor_roomIds(floor_id)
        floorId_to_roomIds[floor_id] = room_ids

    with open(f'../data/id_mappings/floorId_to_roomIds.json', 'w') as file:
        json.dump(floorId_to_roomIds, file)


def init_department_mappings(api: Pythagoras_API) -> None:
    '''
    Map sub-departments to their parent departments and faculties.
    
    Args:
        api (API_Requests): API_Requests object.
        
    Returns:
        department_mappings (dict): Dictionary of department mappings.
    '''
    print('Generating department mappings...')

    organisations = api.get_organisations()

    department_mappings = {}
    for org in organisations:
        department_mappings[org['id']] = {
            'name': org['name'],
            'code': org['code'],
            'treeLevel': org['treeLevel'],
            'path': org['path'],
        }

    with open(f'../data/id_mappings/department_mappings.json', 'w') as file:
        json.dump(department_mappings, file)


def init_floorId_mapId_mapping() -> None:
    '''
    Generates floorId_to_mapId.json file from the floorplans-main folder.
    '''

    floorId_to_mapId = {}

    floor_ids = os.listdir(f'{PATH_FLOORPLANS}/floors_by_id')
    for floor_id in floor_ids:
        floor_id = int(floor_id)
        mapId = get_mapId_from_floorId(floor_id)

        if mapId is not None:
            floorId_to_mapId[floor_id] = mapId

    with open(f'../data/id_mappings/floorId_to_mapId.json', 'w') as file:
        json.dump(floorId_to_mapId, file)


def get_mapId_from_floorId(floor_id: int) -> str:
    '''
    Get the mapId from the floorId.
    
    Args:
        floor_id (int): Floor ID.
        
    Returns:
        mapId (str): Map ID.
    '''

    path_floor_state = f'{PATH_FLOORPLANS}/floors_by_id/{floor_id}/state.yaml'

    if not os.path.exists(path_floor_state):
        return None
    
    with open(path_floor_state) as file:
        data = yaml.safe_load(file)
    
    mapId = data['mist_mapid']

    return mapId


def get_floor_offset(building_id: int) -> list:
    '''
    Get the offset of the floor from state.yaml files.
    
    Args:
        building_id (int): Building ID.
        
    Returns:
        offset (list): Offset of the floor.
    '''

    path_buildingState = f'{PATH_FLOORPLANS}/buildings_by_id/{building_id}/state.yaml'

    if not os.path.exists(path_buildingState):
        return None

    with open(path_buildingState) as file:
        data = yaml.safe_load(file)

    if data['layout'] is None:
        return None

    viewbox = [float(num) for num in data['layout']['viewbox'].split()]
    offset = [-viewbox[0], -viewbox[1]]

    return offset


def generate_room_geometries(data_workspace: list, offset: list) -> tuple:
    '''
    Generate the room geometries and floor tree for a floor.
    
    Args:
        data_workspace (list): Workspace data of the floor.
        offset (list): Offset of the floor.
        
    Returns:
        room_geometries (dict): Dictionary of room geometries.
        floor_tree (STRtree): STRtree of room geometries.
    '''

    room_geometries = {}
    current_polygons = []

    for room in data_workspace:
        room_id = room['id']
        
        room_coords = []
        for coord in room['outline']['coords']:
            room_coords.append((coord['x'] + offset[0], coord['y'] + offset[1])) 
        
        room_polygon = Polygon(room_coords)
        room_geometries[room_id] = room_polygon
        current_polygons.append(room_polygon)

    floor_tree = STRtree(current_polygons)

    return room_geometries, floor_tree


if __name__ == '__main__':
    init()