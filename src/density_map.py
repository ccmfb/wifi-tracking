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

MIN_DISPLAY_ERROR = 1
MAX_DISPLAY_ERROR = 6


def get_density_image(floor_id, batch):
    batch = batch[batch['floor_id'] == floor_id]
    batch = batch.reset_index(drop=True)
    print(len(batch))

    density_map, rooms = get_density_map(floor_id, batch)
    print(density_map)

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

    for i in range(len(batch)):
        if batch['room_id'][i] is None:
            continue
        #circle
        x = (batch['x'][i] - min_x) * 20
        y = (batch['y'][i] - min_y) * 20
        error = batch['error'][i] * 20
        circle = plt.Circle((x, y), error, color='black', fill=False)
        ax.add_patch(circle)

    ax.imshow(density_map/ 255, zorder=0, alpha=0.6)
    #ax.contourf(density_map, zorder=0, alpha=0.6)
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

    density_map = np.array(density_map)
    # density_map = np.power(density_map, 3)
    # density_map = (1/2) * np.sin(np.pi * density_map - np.pi/2) + 1/2
    # density_map = np.sin(density_map * np.pi/2) * np.sin(density_map * np.pi/2) * np.sin(density_map * np.pi/2) * np.sin(density_map * np.pi/2) * np.sin(density_map * np.pi/2)
    density_map = (np.sin(density_map * np.pi/2))**4

    rgba_density_map = np.zeros((len(density_map), len(density_map[0]), 4))
    for i in range(len(density_map)):
        for j in range(len(density_map[0])):
            rgba_density_map[i][j] = get_contour_rgba(density_map[i][j])
            # rgba_density_map[i][j] = get_rgba(density_map[i][j])
            # rgba_density_map[i][j] = get_cmap_value(density_map[i][j])


    return rgba_density_map, rooms


def pdf(x, y, x0, y0, error):
    if error < MIN_DISPLAY_ERROR:
        error = MIN_DISPLAY_ERROR
    elif error > MAX_DISPLAY_ERROR:
        error = MAX_DISPLAY_ERROR
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


def get_cmap_value(value):
    cmap = plt.get_cmap('coolwarm')

    contour_bounds = np.linspace(0, 1, 8)
    contour_values = np.linspace(0, 1, 7)

    if value < 0:
        return [255, 255, 255, 0]
    
    for i in range(len(contour_values)):
        if contour_bounds[i] <= value < contour_bounds[i + 1]:
            return cmap(contour_values[i])
        
    return cmap(1)


def get_contour_rgba(value):
    assert 0 <= value <= 1

    bounds = np.linspace(0, 1, 8)
    alpha = 0.8 * 255
    color1 = np.array([77, 103, 255])
    color2 = np.array([255, 240, 102])
    color3 = np.array([255, 96, 96])

    gradient = [
        color1,
        color1 + (1/3) * (color2 - color1), color1 + (2/3) * (color2 - color1),
        color2,
        color2 + (1/3) * (color3 - color2), color2 + (2/3) * (color3 - color2),
        color3
    ]
    gradient = [np.append(color, alpha) for color in gradient]


    if value == 0:
        return [255, 255, 255, 0]
    
    for i in range(7):
        if bounds[i] <= value < bounds[i + 1]:
            return gradient[i]

    if value == 1:
        return [255, 96, 96, alpha]



def get_rgba(value):
    '''
    Pure gradient
    '''
    assert 0 <= value <= 1

    alpha = 0.8 * 255
    color1 = np.array(
        [77, 103, 255]
    )
    color2 = np.array(
        [255, 240, 102]
    )
    color3 = np.array(
        [255, 96, 96]
    )

    color = None

    if value == 0:
        return np.array([255, 255, 255, 0])

    elif 0 < value < 0.5:
        factor = value / 0.5
        color = color1 + factor * (color2 - color1)

    elif value == 0.5:
        color = color2

    elif 0.5 < value < 1:
        factor = (value - 0.5) / 0.5
        color = color2 + factor * (color3 - color2)

    elif value == 1:
        color = color3

    color = np.append(color, alpha)
    return color


if __name__ == '__main__':
    density_map = get_density_map(floor_id=1654)