'''
Script to generate density maps for a given floor.
'''

import json
import pickle
from io import BytesIO

import numpy as np
from shapely.geometry import Polygon, Point
from shapely.vectorized import contains, touches
import matplotlib.pyplot as plt

MIN_DISPLAY_ERROR = 3


def get_density_image(floor_id, batch):
    density_map, rooms = get_density_map(floor_id, batch)

    fig, ax = plt.subplots(figsize=(10, 10))

    x = np.arange(density_map.shape[1])
    y = np.arange(density_map.shape[0])
    xs, ys = np.meshgrid(x, y)

    min_x = min([room.bounds[0] for room in rooms])
    min_y = min([room.bounds[1] for room in rooms])
    max_x = max([room.bounds[2] for room in rooms])
    max_y = max([room.bounds[3] for room in rooms])

    for room in rooms:
        coords = np.array(list(room.exterior.coords))
        scale = 20
        xs = (coords[:, 0] - min_x) * scale
        ys = (coords[:, 1] - min_y) * scale

        ax.plot(xs, ys, 'grey')

    ax.imshow(density_map / 255, zorder=0)
    ax.axis('off')
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close(fig)

    image_bytes = buffer.getvalue()

    return image_bytes


def get_density_map(floor_id, batch):
    batch = batch[batch['floor_id'] == floor_id]
    batch = batch.reset_index(drop=True)

    with open('../../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
        floorId_to_roomIds = json.load(file)

    with open('../../data/objects/room_geometries.pkl', 'rb') as file:
        room_geometries = pickle.load(file)


    room_ids = floorId_to_roomIds[str(floor_id)]
    rooms = [room_geometries[room_id] for room_id in room_ids]
    # x, y, mask_density_map = get_meshgrid_and_mask(rooms)
    x, y, mask_density_map = get_mesh_and_mask(rooms)

    density_map = np.zeros_like(mask_density_map, dtype=float)

    for i in range(len(batch)):
        current_pdf = pdf(x, y, batch['x'][i], batch['y'][i], batch['error'][i])

        if np.isnan(current_pdf).any():
            print('NAN')
            continue
        else:
            density_map += current_pdf

    density_map[density_map < 1.5] = 0
    density_map = density_map * mask_density_map
    density_map = density_map / np.max(density_map)

    rgba_density_map = np.zeros((len(density_map), len(density_map[0]), 4))
    for i in range(len(density_map)):
        for j in range(len(density_map[0])):
            rgba_density_map[i][j] = get_contour_rgba(density_map[i][j])

    return rgba_density_map, rooms


def pdf(x, y, x0, y0, error):
    if error < MIN_DISPLAY_ERROR:
        error = MIN_DISPLAY_ERROR
    return np.exp(
        (- (x - x0)**2 - (y - y0)**2) / (2 * np.pi * error**2)
    )


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


def get_contour_rgba(value):
    assert 0 <= value <= 1

    bounds = np.linspace(0, 1, 8)
    alpha = 0.8 * 255

    if value == 0:
        return [255, 255, 255, 0]
    elif bounds[0] < value < bounds[1]:
        return [255, 255, 255, alpha]
    elif bounds[1] <= value < bounds[2]:
        return [197, 212, 245, alpha]
    elif bounds[2] <= value < bounds[3]:
        return [135, 171, 235, alpha]
    elif bounds[3] <= value < bounds[4]:
        return [52, 132, 223, alpha]
    elif bounds[4] <= value < bounds[5]:
        return [157, 122, 175, alpha]
    elif bounds[5] <= value < bounds[6]:
        return [212, 106, 128, alpha]
    elif bounds[6] <= value <= bounds[7]:
        return [255, 82, 82, alpha]



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