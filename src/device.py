import numpy as np
import scipy.stats as stats
import bisect


WIFI_ERROR = 10


class Device:
    def __init__(self, mac) -> None:
        self.mac = mac

        self.positions = []
        self.rssi_values = []
        self.timestamps = []

        self.weights = []

        self.x = None
        self.y = None
        self.error = None

        self.room_id = None
        self.floor_ids = []


    def add_data(self, x, y, rssi, timestamp, floor_id):
        self.positions.append([x, y])
        self.rssi_values.append(rssi)
        self.timestamps.append(timestamp)
        self.floor_ids.append(floor_id)

        self.weights.append((1/2) * np.tanh(0.1*rssi + 8) + 0.5) # rssi < -80: approx 0, rssi = -70: 0.5, rssi > -60: approx 1
    

    def pdf(self, x, y, min_error = 0):
        error = self.error if self.error > min_error else min_error
        pdf = np.exp(
            (- (x - self.x)**2 - (y - self.y)**2) / (2 * np.pi * error**2)
        )

        return pdf


    def update_position(self, zValue_to_pValue):
        N = len(self.positions)
        weights = np.array(self.weights)
        positions = np.array(self.positions)

        prev_x = 0
        prev_y = 0
        prev_error = 0

        for i in range(N - 1, -1, -1): # Reverse iteration

            if N - i == 1:
                avg_x = positions[i][0]
                avg_y = positions[i][1]
                error = WIFI_ERROR

            else:
                curr_x = positions[i][0]
                curr_y = positions[i][1]
                radius_to_prev = np.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)

                z = radius_to_prev / prev_error
                prob_moved = 1 - 2 * self.closest_cdf(z, zValue_to_pValue)
                # Alternatively (slower):
                # prob_moved = 1 - 2 * stats.norm.cdf(-radius_to_prev, 0, prev_error)
                prob_moved = prob_moved * weights[i]

                print(f'prob_moved: {prob_moved}')
                if prob_moved > 0.7:
                    break
                else:
                    avg_x = np.sum(weights[i:] * positions[i:, 0]) / np.sum(weights[i:])
                    avg_y = np.sum(weights[i:] * positions[i:, 1]) / np.sum(weights[i:])

                    num_data_points = N - i
                    if num_data_points > 3:
                        error_x = np.sqrt(np.sum(weights[i:] * (positions[i:, 0] - avg_x)**2) / np.sum(weights[i:]))
                        error_y = np.sqrt(np.sum(weights[i:] * (positions[i:, 1] - avg_y)**2) / np.sum(weights[i:]))
                        error = np.sqrt(error_x**2 + error_y**2)
                    else:
                        error = WIFI_ERROR

            prev_x = avg_x
            prev_y = avg_y
            prev_error = error

        self.x = avg_x
        self.y = avg_y
        if error < 1e-1 or np.isnan(error) or error > WIFI_ERROR:
            self.error = WIFI_ERROR 
        else:
            self.error = error


    def closest_cdf(self, z_value, table):
        z_values = list(table.keys())
        closest_index = bisect.bisect_left(z_values, z_value)
        
        if closest_index == 0:
            return table[z_values[0]]
        elif closest_index == len(z_values):
            return table[z_values[-1]]
        else:
            lower_value = z_values[closest_index - 1]
            upper_value = z_values[closest_index]
            
            if abs(z_value - lower_value) < abs(z_value - upper_value):
                return table[lower_value]
            else:
                return table[upper_value]