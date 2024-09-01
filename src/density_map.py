import json
import pickle
from io import BytesIO

import numpy as np
from shapely.geometry import Polygon, Point
from shapely.vectorized import contains, touches
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


MIN_DISPLAY_ERROR = 2
MAX_DISPLAY_ERROR = 10


def get_density_image(floor_id, batch, plot_devices=False):
    batch = batch[batch['floor_id'] == floor_id]
    batch = batch[~np.isnan(batch['room_id'])]
    batch = batch.reset_index(drop=True)

    with open('../../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
        floorId_to_roomIds = json.load(file)

    with open('../../data/objects/room_geometries.pkl', 'rb') as file:
        room_geometries = pickle.load(file)

    room_ids = floorId_to_roomIds[str(floor_id)]
    rooms = [room_geometries[room_id] for room_id in room_ids]

    min_x = min([room.bounds[0] for room in rooms])
    min_y = min([room.bounds[1] for room in rooms])
    max_x = max([room.bounds[2] for room in rooms])
    max_y = max([room.bounds[3] for room in rooms])

    grid_size = 0.1

    x = np.arange(min_x, max_x, grid_size)
    y = np.arange(min_y, max_y, grid_size)
    xx, yy = np.meshgrid(x, y)
    density_map = np.zeros(xx.shape)

    for i in range(len(batch)):
        current_pdf = pdf(xx, yy, batch['x'][i], batch['y'][i], batch['error'][i])
        density_map += current_pdf

    density_map = density_map / np.max(density_map)

    matrix = np.zeros_like(xx, dtype=int)
    for room in rooms:
        mask_contains = contains(room, xx, yy)
        mask_touches = touches(room, xx, yy)
        matrix |= (mask_contains | mask_touches)

    density_map = np.ma.masked_array(density_map, np.logical_not(matrix))

    fig, ax = plt.subplots()

    alpha = 0.6
    blue = np.array([71, 175, 255]) / 255
    yellow = np.array([255, 209, 71]) / 255
    red = np.array([254, 84, 72]) / 255

    colors = [(0, blue), (0.5, yellow), (1, red)]
    colors = [(c[0], [*c[1], alpha]) for c in colors]
    cmap = LinearSegmentedColormap.from_list('custom', colors)

    contour = ax.contourf(xx, yy, density_map, cmap=cmap)

    for room in rooms:
        x, y = room.exterior.xy
        ax.plot(x, y, color='silver', zorder=1)

    if plot_devices:
        for i in range(len(batch)):
            x = batch['x'][i]
            y = batch['y'][i]
            error = batch['error'][i]
            
            if error < MIN_DISPLAY_ERROR:
                error = MIN_DISPLAY_ERROR
            elif error > MAX_DISPLAY_ERROR:
                error = MAX_DISPLAY_ERROR
            
            circle = plt.Circle((x, y), error, color='black', fill=False)
            ax.add_patch(circle)


    ax.axis('off')
    ax.invert_yaxis()
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close(fig)

    image_bytes = buffer.getvalue()

    return image_bytes


def pdf(x, y, x0, y0, error):
    if error < MIN_DISPLAY_ERROR:
        error = MIN_DISPLAY_ERROR
    elif error > MAX_DISPLAY_ERROR:
        error = MAX_DISPLAY_ERROR

    return np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * error ** 2)) / (2 * np.pi * error ** 2)
