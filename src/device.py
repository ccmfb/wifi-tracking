import numpy as np
import scipy.stats as stats
import bisect


WIFI_ERROR = 10


class Device:
    def __init__(self, mac: str) -> None:
        '''
        Initializes the device object.
        
        Args:
            mac (str): The MAC address of the device.
            
        Returns:
            None
        '''

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


    def add_data(self, x: float, y: float, rssi: float, timestamp: int, floor_id: int) -> None:
        '''
        Add data to the device object.
        
        Args:
            x (float): x-coordinate of the device.
            y (float): y-coordinate of the device.
            rssi (float): RSSI value of the device.
            timestamp (int): Timestamp of the data.
            floor_id (int): Floor ID of the data.
            
        Returns:
            None
        '''

        self.positions.append([x, y])
        self.rssi_values.append(rssi)
        self.timestamps.append(timestamp)
        self.floor_ids.append(floor_id)

        self.weights.append((1/2) * np.tanh(0.1*rssi + 8) + 0.5) # rssi < -80: approx 0, rssi = -70: 0.5, rssi > -60: approx 1
    

    def update_position(self, zValue_to_pValue: dict) -> None:
        '''
        Calculates the optimized position of the device based on averages of past positions and probability of movement.
        
        Args:
            zValue_to_pValue (dict): A dictionary mapping z-values (normalized distance) to p-values (probabilities).
            
        Returns:
            None
        '''

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


    def is_active(self, active_time: float, active_count: int) -> bool:
        '''
        Checks if the device is active based on certain criteria.
        
        Args:
            active_time (float): The time in seconds since the last data point.
            active_count (int): The number of data points to be considered active.
            
        Returns:
            bool: True if the device is active, False otherwise.
        '''

        if self.timestamps[-1] < self.timestamps[-1] - active_time:
            return False

        if len(self.positions) < active_count:
            return False

        if self.floor_ids[-1] != self.floor_ids[-2]:
            return False

        return True


    def closest_cdf(self, z_value: float, table: dict) -> float:
        '''
        Returns the closest p-value to the given z-value from the given table. Replaces explicit calculations of the CDF.
        
        Args:
            z_value (float): The z-value.
            table (dict): A dictionary mapping z-values to p-values.
            
        Returns:
            float: The closest p-value to the given z-value.
        '''

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