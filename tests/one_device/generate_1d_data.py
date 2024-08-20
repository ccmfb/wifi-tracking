'''
Generate data for 1 device.
'''

import numpy as np
import pandas as pd


def generate_data(map_id, mac, positions, errors):
    type = 'wifi'
    site_id = '48b01af6-138b-465d-8996-bace824f5726'

    xs, ys = [], []
    rssi_vals = []
    for position, error in zip(positions, errors):
        curr_xs = np.random.normal(position[0], error, 15)
        curr_ys = np.random.normal(position[1], error, 15)
        curr_rssi_vals = np.random.normal(-70, 5, 15)

        xs.extend(curr_xs)
        ys.extend(curr_ys)
        rssi_vals.extend(curr_rssi_vals)

    data = {
        'timestamp': [i*60 for i in range(len(xs))],
        'mac': [mac for _ in range(len(xs))],
        'map_id': [map_id for _ in range(len(xs))],
        'rssi': rssi_vals,
        'site_id' : [site_id for _ in range(len(xs))],
        'type': [type for _ in range(len(xs))],
        'x': xs,
        'y': ys,
    }

    df = pd.DataFrame(data)
    print(df.head())
    df.to_csv('data_1d.csv', index=False)



if __name__ == '__main__':
    generate_data(
        map_id = '674f1f22-b555-4cb0-bdd4-df5ffe9d195f',
        mac = 'ad8f9759e8fff5207fce65da0c68f12ef2fa0446cfecf1f5ec1e01156d7843ea',
        positions = [[10,10], [60,60], [20,70], [50,15]],
        errors = [4, 1, 3, 3]
    )
