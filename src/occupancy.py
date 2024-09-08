import json
import time

import pandas as pd
from tqdm import tqdm


PATH_FLOORPLANS = '../data/floorplans-main'


def generate_occupancy_data(dataframe: pd.DataFrame) -> None:

    # splits data into batches
    batches = []
    unique_timestamps = dataframe['timestamp'].unique()
    for timestamp in unique_timestamps:
        batch = dataframe[dataframe['timestamp'] == timestamp]
        batches.append(batch)

    department_mappings = get_department_mappings()

    data = init_data()
    for batch in tqdm(batches):
        room_ids = batch['room_id'].unique()

        for room_id in room_ids:
            if room_valid(batch, room_id) == False: continue

            room = batch[batch['room_id'] == room_id]
            floor_id = room['floor_id'].to_list()[0]

            floor_info = get_floor_info(floor_id)
            floor_workspace = get_floor_workspace(floor_id)
            floor_workspace = {item['id']: item for item in floor_workspace}

            data['timestamp'].append(room['timestamp'].to_list()[0])
            data['date_time'].append(convert_timestamp_to_dateTime(room['timestamp'].to_list()[0]))
            data['num_devices'].append(len(room))

            # room info
            data['room_id'].append(room_id)
            data['room_uid'].append(floor_workspace[room_id]['uid'])
            data['room_name'].append(floor_workspace[room_id]['name'])
            data['room_popular_name'].append(floor_workspace[room_id]['popularName'])
            data['room_gross_area'].append(floor_workspace[room_id]['grossarea'])
            data['room_net_area'].append(floor_workspace[room_id]['netarea'])
            data['room_type_id'].append(floor_workspace[room_id]['typeId'])
            data['room_type_name'].append(floor_workspace[room_id]['typeName'])

            # floor info
            data['floor_id'].append(floor_id)
            data['floor_uid'].append(floor_info['uid'])
            data['floor_name'].append(floor_info['name'])
            data['floor_popular_name'].append(floor_info['popularName'])

            # building info
            data['building_id'].append(floor_info['buildingId'])
            data['building_uid'].append(floor_info['buildingUid'])
            data['building_name'].append(floor_info['buildingName'])
            data['building_popular_name'].append(floor_info['buildingPopularName'])

            # room owner info
            if 'ownerId' not in floor_workspace[room_id] or floor_workspace[room_id]['ownerId'] is None:
                data = add_no_owner_data(data)
            else: 
                data = add_owner_data(data, floor_workspace, department_mappings, room_id)


    occupancy = pd.DataFrame(data)
    occupancy.to_csv('../data/occupancy.csv', index=False)


def init_data() -> dict:
    data = {}

    data['timestamp'] = []
    data['date_time'] = []
    data['num_devices'] = []

    # room info
    data['room_id'] = []
    data['room_uid'] = []
    data['room_name'] = []
    data['room_popular_name'] = []
    data['room_gross_area'] = []
    data['room_net_area'] = []
    data['room_type_id'] = []
    data['room_type_name'] = []

    # floor info
    data['floor_id'] = []
    data['floor_uid'] = []
    data['floor_name'] = []
    data['floor_popular_name'] = []

    # building info
    data['building_id'] = []
    data['building_uid'] = []
    data['building_name'] = []
    data['building_popular_name'] = []

    # room owner info
    data['room_owner_sub_department_id'] = []
    data['room_owner_sub_department_code'] = []
    data['room_owner_sub_department_name'] = []

    data['room_owner_department_id'] = []
    data['room_owner_department_code'] = []
    data['room_owner_department_name'] = []

    data['room_owner_faculty_id'] = []
    data['room_owner_faculty_code'] = []
    data['room_owner_faculty_name'] = []

    return data


def room_valid(batch: pd.DataFrame, room_id: int) -> bool:
    '''
    Check if the room is valid.
    
    Args:
        room_id (int): Room ID.
        
    Returns:
        bool: True if the room is valid, False otherwise.
    '''

    if room_id == 'None':
        return False

    room = batch[batch['room_id'] == room_id]
    if len(room) == 0:
        return False

    return True


def get_floor_info(floor_id: int) -> dict:
    '''
    Get the info.json file for the floor.
    
    Args:
        floor_id (int): Floor ID.
        
    Returns:
        dict: Floor information.
    '''

    path_floorInfo = f'{PATH_FLOORPLANS}/floors_by_id/{floor_id}/info.json'

    with open(path_floorInfo, 'r') as file:
        floor_info = json.load(file)

    return floor_info


def get_floor_workspace(floor_id: int) -> dict:
    '''
    Get the workspace.json file for the floor.
    
    Args:
        floor_id (int): Floor ID.
        
    Returns:
        dict: Floor workspace.
    '''

    path_floorWorkspace = f'{PATH_FLOORPLANS}/floors_by_id/{floor_id}/workspace.json'

    with open(path_floorWorkspace, 'r') as file:
        floor_workspace = json.load(file)

    return floor_workspace


def convert_timestamp_to_dateTime(timestamp: int) -> str:
    '''
    Convert timestamp to readable format.

    Args:
        timestamp (int): Timestamp.

    Returns:
        str: Datetime.
    '''
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(timestamp))
    

def get_department_mappings() -> dict:
    '''
    Get the department mappings for sub-departments, departments, and faculties.

    Returns:
        department_mappings (dict): Dictionary of department mappings.
    '''

    with open('../data/id_mappings/department_mappings.json', 'r') as file:
        department_mappings = json.load(file)

    return department_mappings


def add_owner_data(data: dict, floor_workspace: dict, department_mappings: dict, room_id: int) -> dict:
    ''''
    Add owner data to the dictionary.
    
    Args:
        data (dict): Dictionary.
        
    Returns:
        dict: Dictionary with owner data.
    '''

    owner_id = str(floor_workspace[room_id]['ownerId'])
    tree_lvl = department_mappings[owner_id]['treeLevel']
    assert tree_lvl == 2

    data['room_owner_sub_department_id'].append(floor_workspace[room_id]['ownerId'])
    data['room_owner_sub_department_code'].append(floor_workspace[room_id]['ownerCode'])
    data['room_owner_sub_department_name'].append(floor_workspace[room_id]['ownerName'])

    organisation_path = department_mappings[owner_id]['path'].split('/')
    department_id = organisation_path[-2]
    faculty_id = organisation_path[-3]

    data['room_owner_department_id'].append(department_id)
    data['room_owner_department_code'].append(department_mappings[department_id]['code'])
    data['room_owner_department_name'].append(department_mappings[department_id]['name'])

    data['room_owner_faculty_id'].append(faculty_id)
    data['room_owner_faculty_code'].append(department_mappings[faculty_id]['code'])
    data['room_owner_faculty_name'].append(department_mappings[faculty_id]['name'])

    return data


def add_no_owner_data(data: dict) -> dict:
    '''
    Add no owner data to the dictionary.
    
    Args:
        data (dict): Dictionary.
        
    Returns:
        dict: Dictionary with no owner data.
    '''

    data['room_owner_sub_department_id'].append('None')
    data['room_owner_sub_department_code'].append('None')
    data['room_owner_sub_department_name'].append('None')

    data['room_owner_department_id'].append('None')
    data['room_owner_department_code'].append('None')
    data['room_owner_department_name'].append('None')

    data['room_owner_faculty_id'].append('None')
    data['room_owner_faculty_code'].append('None')
    data['room_owner_faculty_name'].append('None')

    return data


if __name__ == '__main__':
    df = pd.read_csv('../data/data_refined.csv')
    generate_occupancy_data(df)