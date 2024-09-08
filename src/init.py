import os
import pickle
import json
import yaml

from api_requests import API_Requests

from tqdm import tqdm
from shapely.geometry import Polygon
from shapely.strtree import STRtree
import pandas as pd


PATH_FLOORPLANS = '../data/floorplans-main'


def init() -> None:
    floor_ids = get_floor_ids()
    api = API_Requests()

    init_saved_objects(floor_ids)
    init_floor_to_rooms_mapping(floor_ids)
    init_department_mappings(api)
    init_refined_data_file(floor_ids)


def init_saved_objects(floor_ids: list) -> None:
    '''
    Generate and save the room geometries and floor trees for each floor.
    
    Args:
        floor_ids (list): List of floor IDs.
        
    Returns:
        None
    '''

    room_geometries = {}
    floor_trees = {}
    
    for floor_id in tqdm(floor_ids):
        path_floorWorkspace = f'{PATH_FLOORPLANS}/floors_by_id/{floor_id}/workspace.json'
        path_floorInfo = f'{PATH_FLOORPLANS}/floors_by_id/{floor_id}/info.json'

        with open(path_floorWorkspace, 'r') as file:
            data_workspace = json.load(file)

        with open(path_floorInfo, 'r') as file:
            data_info = json.load(file)

        # data_workspace = get_data_workspace(floor_id)
        # data_info = get_data_info(floor_id)

        building_id = int(data_info['buildingId'])
        offset = get_floor_offset(building_id)
        
        if offset is None: continue

        current_room_geometries, current_floor_tree = generate_room_geometries(data_workspace, offset)
        room_geometries.update(current_room_geometries)
        floor_trees[floor_id] = current_floor_tree

    with open(f'../data/objects/room_geometries.pkl', 'wb') as file:
        pickle.dump(room_geometries, file)

    with open(f'../data/objects/floor_trees.pkl', 'wb') as file:
        pickle.dump(floor_trees, file)


def init_floor_to_rooms_mapping(floor_ids: list) -> None:
    '''
    Generate and save the mapping of floor IDs to room IDs.
    
    Args:
        floor_ids (list): List of floor IDs.
        
    Returns:
        None
    '''

    floorId_to_roomIds = {}

    for floor_id in tqdm(floor_ids):
        path_floorWorkspace = f'{PATH_FLOORPLANS}/floors_by_id/{floor_id}/workspace.json'

        with open(path_floorWorkspace, 'r') as file:
            data_workspace = json.load(file)

        room_ids = [room['id'] for room in data_workspace]
        floorId_to_roomIds[floor_id] = room_ids

    with open(f'../data/id_mappings/floorId_to_roomIds.json', 'w') as file:
        json.dump(floorId_to_roomIds, file)


def init_department_mappings(api: API_Requests) -> None:
    '''
    Map sub-departments to their parent departments and faculties.
    
    Args:
        api (API_Requests): API_Requests object.
        
    Returns:
        department_mappings (dict): Dictionary of department mappings.
    '''

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
    

def init_refined_data_file(floor_ids: list) -> None:
    '''
    Generate and save the empty refined data file.
    
    Args:
        floor_ids (list): List of floor IDs.
        
    Returns:
        None
    '''

    data_refined_columns = {
        'timestamp': [], 'mac': [], 'x': [], 'y': [], 'error': [], 'rssi': [], 'floor_id': [], 'room_id': []
    }

    df_refined = pd.DataFrame(data_refined_columns)
    df_refined.to_csv('../data/data_refined.csv', index=False, header=True)


def get_floor_ids() -> list:
    '''
    Retrieve the list of floor IDs from the floorplans directory.
    
    Returns:
        floor_ids (list): List of floor IDs.
    '''

    path_floorsById = f'{PATH_FLOORPLANS}/floors_by_id'

    all_entries = os.listdir(path_floorsById)
    floor_ids = [entry for entry in all_entries if os.path.isdir(os.path.join(path_floorsById, entry))]

    return floor_ids


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


def generate_room_geometries(data_workspace: dict, offset: list) -> tuple:
    '''
    Generate the room geometries and floor tree for a floor.
    
    Args:
        data_workspace (dict): Workspace data of the floor.
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