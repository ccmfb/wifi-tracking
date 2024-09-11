import json
import time
import sqlite3

from api_requests import API_Requests

import pandas as pd
from tqdm import tqdm


PATH_FLOORPLANS = '../data/floorplans-main'


def generate_occupancy_data(dataframe: pd.DataFrame) -> None:
    '''
    Uses the refined data to create 'room summaries' and enrich with pythagoras data.
    
    Args:
        dataframe (pd.DataFrame): Data.
        
    Returns:
        None
    '''

    # splits data into batches
    batches = []
    unique_timestamps = dataframe['timestamp'].unique()
    for timestamp in unique_timestamps:
        batch = dataframe[dataframe['timestamp'] == timestamp]
        batches.append(batch)

    # Loading additional data
    department_mappings = get_department_mappings()
    api = API_Requests()

    floor_infos = {}
    floor_workspaces = {}
    for floor_id in tqdm(dataframe['floor_id'].unique()):
        floor_infos[floor_id] = api.get_floor_info(floor_id)
        floor_workspaces[floor_id] = api.get_floor_workspace_info(floor_id)

    # Populate the data
    data = init_data()
    data = populate_data(data, batches, floor_infos, floor_workspaces, department_mappings)

    # Add data to database
    add_to_db(data)


def init_data() -> dict:
    '''
    Initialize the data dictionary.
    
    Returns:
        dict: Data.
    '''

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

    data['celcat_name'] = []

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


def populate_data(data: dict, batches: list, floor_infos: dict, floor_workspaces: dict, department_mappings: dict) -> list:
    '''
    Populates the data dictionary.

    Args:
        data (dict): Dictionary.
        batches (list): List of batches.
        floor_infos (dict): Floor infos.
        floor_workspaces (dict): Floor workspaces.
        department_mappings (dict): Department mappings.

    Returns:
        list: Data.
    '''

    for batch in tqdm(batches):
        room_ids = batch['room_id'].unique()

        for room_id in room_ids:
            if room_valid(batch, room_id) == False: continue
            room_id = int(room_id)

            room = batch[batch['room_id'] == room_id]
            floor_id = room['floor_id'].to_list()[0]

            floor_info = floor_infos[floor_id]
            floor_workspace = floor_workspaces[floor_id]
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

            # celcat info
            floor_name = floor_info['name']
            room_name = floor_workspace[room_id]['name']
            data['celcat_name'].append(f'{floor_name}-{room_name}')

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

    data = [data[key] for key in data.keys()]
    data = list(map(list, zip(*data)))

    return data


def add_to_db(data: list) -> None:
    '''
    Add data to the database.
    
    Args:
        data (list): Data.
        
    Returns:
        None
    '''

    conn = sqlite3.connect('../data/occupancy.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS occupancy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        date_time TEXT,
        num_devices INTEGER,
        room_id TEXT,
        room_uid TEXT,
        room_name TEXT,
        room_popular_name TEXT,
        room_gross_area REAL,
        room_net_area REAL,
        room_type_id INTEGER,
        room_type_name TEXT,
        floor_id TEXT,
        floor_uid TEXT,
        floor_name TEXT,
        floor_popular_name TEXT,
        celcat_name TEXT,
        building_id TEXT,
        building_uid TEXT,
        building_name TEXT,
        building_popular_name TEXT,
        room_owner_sub_department_id INTEGER,
        room_owner_sub_department_code TEXT,
        room_owner_sub_department_name TEXT,
        room_owner_department_id INTEGER,
        room_owner_department_code TEXT,
        room_owner_department_name TEXT,
        room_owner_faculty_id INTEGER,
        room_owner_faculty_code TEXT,
        room_owner_faculty_name TEXT
    )
    ''')

    cursor.executemany(
        "INSERT INTO occupancy (timestamp, date_time, num_devices, room_id, room_uid, room_name, room_popular_name, celcat_name, room_gross_area, room_net_area, room_type_id, room_type_name, floor_id, floor_uid, floor_name, floor_popular_name, building_id, building_uid, building_name, building_popular_name, room_owner_sub_department_id, room_owner_sub_department_code, room_owner_sub_department_name, room_owner_department_id, room_owner_department_code, room_owner_department_name, room_owner_faculty_id, room_owner_faculty_code, room_owner_faculty_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        data
    )

    conn.commit()
    conn.close()


def room_valid(batch: pd.DataFrame, room_id: str) -> bool:
    '''
    Check if the room is valid.
    
    Args:
        room_id (int): Room ID.
        
    Returns:
        bool: True if the room is valid, False otherwise.
    '''

    if room_id == 'None':
        return False

    room_id = int(room_id)
    room = batch[batch['room_id'] == room_id]
    if len(room) == 0:
        return False

    return True


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


def retrieve_data_from_db() -> pd.DataFrame:
    '''
    Retrieve data from the database.

    Returns:
        pd.DataFrame: Data.
    '''

    conn = sqlite3.connect('../data/refined_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM data_refined")
    column_names = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    data = pd.DataFrame(rows, columns=column_names)

    conn.close()

    return data


if __name__ == '__main__':
    df = retrieve_data_from_db()
    generate_occupancy_data(df)