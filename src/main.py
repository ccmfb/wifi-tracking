from device import Device

from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree


ACTIVE_TIME = 3*60 # If devices is not seen for 3 minutes, it is considered inactive -> probably left the building
ACTIVE_COUNT = 2 # If device is not at least seen 2 times, it is considered inactive -> probably only passing through


def generate_refined_data(batch):
    mapId_to_floorId = {} # Load from json
    zValue_to_pValue = {} # Load from json

    recent_devices = {} # Load from .pkl, format is {mac: Device}
    devices_in_batch = {}

    floorId_to_roomIds = {} # Load from json
    floor_str_trees = {} # Load from .pkl

    rooms_geometries = {}
    floor_trees = {}


    # Data to collect
    timestamp = batch['timestamp'].to_list()[0]
    data_batch_timestamp = [timestamp for _ in range(len(batch))]
    data_mac = []
    data_x, data_y = [], []
    data_rssi = []
    data_floor_id = []
    data_room_id = []

    # Loading devices in current batch
    for i in range(len(batch)):

        if batch['mac'][i] not in recent_devices:
            recent_devices[batch['mac'][i]] = Device(batch['mac'][i])

        current_device = recent_devices[batch['mac'][i]]
        floor_id = mapId_to_floorId[batch['site_id'][i]]
        current_device.add_data(
            batch['x'][i],
            batch['y'][i],
            batch['rssi'][i],
            batch['timestamp'][i],
            floor_id
        )

        if current_device.mac not in devices_in_batch:
            devices_in_batch[current_device.mac] = current_device


    for device in devices_in_batch.values():
        
        if device.timestamp[-1] < timestamp - ACTIVE_TIME:
            continue

        if len(device.positions) < ACTIVE_COUNT:
            continue

        if device.floor_ids[-1] != device.floor_ids[-2]:
            continue

        device.update_position(zValue_to_pValue)

        floor_id = device.floor_ids[-1]
        floor_tree = floor_str_trees[floor_id]
        room_ids = floorId_to_roomIds[floor_id]

        point = Point(device.x, device.y)
        matches = room_ids.take(floor_tree.query(point))

        room_id = 'None'
        for room_id_ in matches:
            room = floor_id_to_roomIds[floor_id][room_id_]

            if room.polygon.contains(point):
                room_id = room_id_
                break








        point = Point(device.x, device.y)
        possible_room_ids = self.room_ids.take(self.str_tree.query(point))

        actual_room_id = 'None'
        for room_id in possible_room_ids:
            room = self.rooms[self.room_ids.tolist().index(room_id)]

            if room.polygon.contains(point):
                actual_room_id = room_id




