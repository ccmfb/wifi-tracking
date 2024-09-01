import json
import pickle
from io import BytesIO

import numpy as np
import pandas as pd
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

    rooms = get_rooms(floor_id)
    xx, yy = meshgrid(rooms, grid_size=0.1)

    # Density map
    density_map = get_density_map(batch, xx, yy)
    density_map = scale_density_map(density_map)
    density_map = mask_density_map(density_map, rooms, xx, yy)

    # Plotting
    buffer = plot_density_map(density_map, xx, yy, rooms, batch, plot_devices=plot_devices)
    image_bytes = buffer.getvalue()

    return image_bytes


def get_rooms(floor_id: int) -> list:
    '''
    Returns a list of shapely Polygon objects representing the rooms in the given floor.

    Args:
        floor_id (int): The floor id.

    Returns:
        list: A list of shapely Polygon objects.
    '''

    with open('../../data/id_mappings/floorId_to_roomIds.json', 'r') as file:
        floorId_to_roomIds = json.load(file)

    with open('../../data/objects/room_geometries.pkl', 'rb') as file:
        room_geometries = pickle.load(file)

    room_ids = floorId_to_roomIds[str(floor_id)]
    rooms = [room_geometries[room_id] for room_id in room_ids]

    return rooms


def meshgrid(rooms: list, grid_size: float = 0.1) -> tuple:
    '''
    Returns a meshgrid of x and y coordinates based on the rooms.
    
    Args:
        rooms (list): A list of shapely Polygon objects.
        grid_size (float): The grid size.
        
    Returns:
        tuple: A tuple of numpy arrays representing the mesh
    '''

    min_x = min([room.bounds[0] for room in rooms])
    min_y = min([room.bounds[1] for room in rooms])
    max_x = max([room.bounds[2] for room in rooms])
    max_y = max([room.bounds[3] for room in rooms])

    x = np.arange(min_x, max_x, grid_size)
    y = np.arange(min_y, max_y, grid_size)
    xx, yy = np.meshgrid(x, y)

    return xx, yy


def get_density_map(batch: pd.DataFrame, xx: np.ndarray, yy: np.ndarray) -> np.ndarray:
    '''
    Generates a density map based on the devices in the batch.
    
    Args:
        batch (pandas.DataFrame): The batch of devices.
        xx (numpy.ndarray): The x coordinates.
        yy (numpy.ndarray): The y coordinates.
        
    Returns:
        numpy.ndarray: The density map
    '''

    density_map = np.zeros(xx.shape)

    for i in range(len(batch)):
        current_pdf = pdf(xx, yy, batch['x'][i], batch['y'][i], batch['error'][i])
        density_map += current_pdf

    return density_map


def scale_density_map(density_map: np.ndarray) -> np.ndarray:
    '''
    Removes single device peaks and scales the density map.
    
    Args:
        density_map (numpy.ndarray): The density map.
        
    Returns:
        numpy.ndarray: The scaled density map.
    '''

    density_map[density_map < 1.1] = 0
    density_map = density_map / np.max(density_map)
    density_map = ( np.sin(density_map * np.pi / 2) )**2

    return density_map


def mask_density_map(density_map, rooms, xx, yy) -> np.ndarray:
    '''
    Masks the area outside the rooms in the density map.
    
    Args:
        density_map (numpy.ndarray): The density map.
        rooms (list): A list of shapely Polygon objects.
        xx (numpy.ndarray): The x coordinates.
        yy (numpy.ndarray): The y coordinates.
        
    Returns:
        numpy.ndarray: The masked density map.
    '''

    matrix = np.zeros_like(xx, dtype=int)

    for room in rooms:
        mask_contains = contains(room, xx, yy)
        mask_touches = touches(room, xx, yy)
        matrix |= (mask_contains | mask_touches)

    masked_density_map = np.ma.masked_array(density_map, np.logical_not(matrix))

    return masked_density_map


def custom_colormap(
        color1: list = [71, 175, 255], 
        color2: list = [255, 209, 71],
        color3: list = [254, 84, 72]) -> LinearSegmentedColormap:
    '''
    Custom colormap based on three colours.
    
    Args:
        color1 (list): The first color.
        color2 (list): The second color.
        color3 (list): The third color.
        
    Returns:
        matplotlib.colors.LinearSegmentedColormap: The custom colormap.
    '''

    color1 = [c / 255 for c in color1]
    color2 = [c / 255 for c in color2]
    color3 = [c / 255 for c in color3]

    colors = [(0, color1), (0.5, color2), (1, color3)]
    cmap = LinearSegmentedColormap.from_list('custom', colors)
    cmap = 'coolwarm'

    return cmap


def plot_density_map(
        density_map: np.ndarray, 
        xx: np.ndarray, 
        yy: np.ndarray, 
        rooms: list, 
        batch: pd.DataFrame, 
        plot_devices: bool = False) -> BytesIO:
    '''
    Plots the density map.
    
    Args:
        density_map (numpy.ndarray): The density map.
        xx (numpy.ndarray): The x coordinates.
        yy (numpy.ndarray): The y coordinates.
        rooms (list): A list of shapely Polygon objects.
        batch (pandas.DataFrame): The batch of devices.
        plot_devices (bool): Whether to plot the devices.
        
    Returns:
        BytesIO: The image buffer.
    '''

    fig, ax = plt.subplots(figsize=(8, 8))

    cmap = custom_colormap()
    alpha = 0.6
    ax.contourf(xx, yy, density_map, cmap=cmap, alpha=alpha)

    for room in rooms:
        x, y = room.exterior.xy
        ax.plot(x, y, color='silver', zorder=1)

    if plot_devices:
        plot_devices_in_batch(batch, ax)

    ax.axis('off')
    ax.invert_yaxis()
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close(fig)

    return buffer


def plot_devices_in_batch(batch: pd.DataFrame, ax) -> None:
    '''
    Plots the devices in the batch.
    
    Args:
        batch (pandas.DataFrame): The batch of devices.
        ax (matplotlib.axes.Axes): The axes.

    Returns:
        None
    '''

    for i in range(len(batch)):
        x = batch['x'][i]
        y = batch['y'][i]
        error = batch['error'][i]
        
        if error < MIN_DISPLAY_ERROR:
            error = MIN_DISPLAY_ERROR
        elif error > MAX_DISPLAY_ERROR:
            error = MAX_DISPLAY_ERROR
        
        circle = plt.Circle((x, y), error, color='black', fill=False, zorder=2)
        ax.add_patch(circle)


def pdf(x: np.ndarray, y: np.ndarray, x0: float, y0: float, error: float) -> np.ndarray:
    '''
    Probability density function.
    
    Args:
        x (numpy.ndarray): The x coordinates.
        y (numpy.ndarray): The y coordinates.
        x0 (float): The x coordinate of the device.
        y0 (float): The y coordinate of the device.
        error (float): The error of the device.
        
    Returns:
        numpy.ndarray: The probability density function.
    '''

    if error < MIN_DISPLAY_ERROR:
        error = MIN_DISPLAY_ERROR
    elif error > MAX_DISPLAY_ERROR:
        error = MAX_DISPLAY_ERROR

    return np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * error ** 2))
