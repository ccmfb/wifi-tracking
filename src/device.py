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
        positions = np.array(self.positions)
        positions = positions[::-1]
        weights = np.array(self.weights)
        weights = weights[::-1]

        if len(positions) == 1:
            self.x = positions[0][0]
            self.y = positions[0][1]
            self.error = WIFI_ERROR
            return

        prev_x = positions[0][0]
        prev_y = positions[0][1]
        prev_error = WIFI_ERROR

        for i, position in enumerate(positions[1:]):

            curr_x = position[0]
            curr_y = position[1]
            radius_to_prev = np.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)

            z = radius_to_prev / prev_error
            probability_moved = 1 - 2 * self.closest_cdf(z, zValue_to_pValue)
            probability_moved = probability_moved * weights[i]

            if probability_moved > 0.8:
                break

            upper_limit = i + 2
            x_estimate = np.sum(weights[:upper_limit] * positions[:upper_limit, 0]) / np.sum(weights[:upper_limit])
            y_estimate = np.sum(weights[:upper_limit] * positions[:upper_limit, 1]) / np.sum(weights[:upper_limit])

            if i == 0:
                error_estimate = WIFI_ERROR
            else:
                error_x = np.sqrt(np.sum(weights[:upper_limit] * (positions[:upper_limit, 0] - x_estimate)**2) / np.sum(weights[:upper_limit]))
                error_y = np.sqrt(np.sum(weights[:upper_limit] * (positions[:upper_limit, 1] - y_estimate)**2) / np.sum(weights[:upper_limit]))
                error_estimate = np.sqrt(error_x**2 + error_y**2)

            prev_x = x_estimate
            prev_y = y_estimate
            if np.isnan(error_estimate) or error_estimate > WIFI_ERROR:
                prev_error = WIFI_ERROR
            else:
                prev_error = error_estimate

        self.x = prev_x
        self.y = prev_y
        self.error = prev_error


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