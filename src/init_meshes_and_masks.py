'''
Not implemented yet, but would speed up the process of creating the density maps significantly...
'''
import json
import pickle

from shapely.geometry import Polygon, Point
from shapely.vectorized import contains, touches
import numpy as np
from tqdm import tqdm



def create():
    with open('../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
        floorId_to_roomIds = json.load(file)

    with open('../data/objects/room_geometries.pkl', 'rb') as file:
        room_geometries = pickle.load(file)

    data = {}
    for floor_id in tqdm(floorId_to_roomIds):
        room_ids = floorId_to_roomIds[floor_id]
        rooms = [room_geometries[room_id] for room_id in room_ids]
        x, y, mask_density_map = get_mesh_and_mask(rooms)

        data[floor_id] = {
            'x': x,
            'y': y,
            'mask_density_map': mask_density_map
        }

    with open('../data/objects/meshes_and_masks.pkl', 'wb') as file:
        pickle.dump(data, file)


def get_mesh_and_mask(rooms):
    min_x = min([room.bounds[0] for room in rooms])
    min_y = min([room.bounds[1] for room in rooms])
    max_x = max([room.bounds[2] for room in rooms])
    max_y = max([room.bounds[3] for room in rooms])

    grid_size = 0.05

    x = np.arange(min_x, max_x, grid_size)
    y = np.arange(min_y, max_y, grid_size)
    xx, yy = np.meshgrid(x, y)

    matrix = np.zeros_like(xx, dtype=int)

    # Rasterize polygons into the matrix
    for room in rooms:
        mask_contains = contains(room, xx, yy)
        mask_touches = touches(room, xx, yy)
        matrix |= (mask_contains | mask_touches)

    return xx, yy, matrix


if __name__ == '__main__':
    create()