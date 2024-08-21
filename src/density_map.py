'''
Script to generate density maps for a given floor.
'''

import json
import pickle

import numpy as np
from shapely.geometry import Polygon, Point


MIN_DISPLAY_ERROR = 3


def get_density_map(floor_id, batch):
    batch = batch[batch['floor_id'] == floor_id]
    batch = batch.reset_index(drop=True)

    with open('../../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
        floorId_to_roomIds = json.load(file)

    with open('../../data/objects/room_geometries.pkl', 'rb') as file:
        room_geometries = pickle.load(file)


    room_ids = floorId_to_roomIds[str(floor_id)]
    rooms = [room_geometries[room_id] for room_id in room_ids]
    x, y, mask_density_map = get_meshgrid_and_mask(rooms)

    density_map = np.zeros_like(mask_density_map)

    for i in range(len(batch)):
        current_pdf = pdf(x, y, batch['x'][i], batch['y'][i], batch['error'][i])

        if np.isnan(current_pdf).any():
            print('NAN')
            continue
        else:
            density_map += current_pdf

    density_map[density_map < 1.5] = 0
    # density_map[density_map > 1.5 + np.pi] = 1
    
    # mask = (density_map > 1.5) & (density_map < 1.5 + np.pi)
    # density_map[mask] = - (1/2) * np.cos(density_map[density_map > 1.5] - 1.5) + (1/2)

    # cmap = mpl.cm.get_cmap('coolwarm')
    density_map = density_map * mask_density_map
    density_map = density_map / np.max(density_map)

    rgba_density_map = np.zeros((len(density_map), len(density_map[0]), 3))
    for i in range(len(density_map)):
        for j in range(len(density_map[0])):
            rgba_density_map[i][j] = get_rgba(density_map[i][j])

    return rgba_density_map
    



def pdf(x, y, x0, y0, error):
    if error < MIN_DISPLAY_ERROR:
        error = MIN_DISPLAY_ERROR
    return np.exp(
        (- (x - x0)**2 - (y - y0)**2) / (2 * np.pi * error**2)
    )


def get_meshgrid_and_mask(rooms):
    min_x, min_y, max_x, max_y = 0, 0, 0, 0

    for room in rooms:
        current_min_x, current_min_y, current_max_x, current_max_y = room.bounds

        if current_min_x < min_x:
            min_x = current_min_x
        if current_min_y < min_y:
            min_y = current_min_y
        if current_max_x > max_x:
            max_x = current_max_x
        if current_max_y > max_y:
            max_y = current_max_y

    x, y = np.meshgrid(
        np.linspace(min_x, max_x, int(max_x - min_x)*4), 
        np.linspace(min_y, max_y, int(max_y - min_y)*4)
    )

    # optimise!!!
    mask = np.zeros_like(x)
    for i in range(len(x)):
        for j in range(len(x[0])):

            point = Point(x[i][j], y[i][j])
            for room in rooms:

                if room.contains(point):
                    mask[i][j] = 1
                    break

    return x, y, mask


def get_rgba(value):
    # value needs to be between 0 and 1
    white = np.array([255, 255, 255])
    blue = np.array([129, 169, 238])
    red = np.array([242, 95, 92])

    color = None

    if value == 0:
        color = white

    elif 0 < value < 0.5:
        factor = value / 0.5
        color = white + factor * (blue - white)

    elif value == 0.5:
        color = blue

    elif 0.5 < value < 1:
        factor = (value - 0.5) / 0.5
        color = blue + factor * (red - blue)

    elif value == 1:
        color = red

    return [int(num) for num in color]


if __name__ == '__main__':
    density_map = get_density_map(floor_id=1654)