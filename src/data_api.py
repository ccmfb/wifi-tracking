import requests
import json

from dotenv import dotenv_values
import pandas as pd


class Data_API:
    def __init__(self) -> None:
        config = dotenv_values("../.env")
        
        self.headers = {
            "Authorization": f"Splunk {config['DATA_API_KEY']}",
        }

        self.data = {
            "search": 'search index=wireless_anonymised topic=loc | table timestamp, type, mac, map_id, site_id, rssi, x, y',
            "exec_mode": "oneshot",
            "output_mode": "json",
            "earliest_time": "-10m@m",
        }

    
    def get_last_batch(self) -> pd.DataFrame:
        '''
        Get the most recent batch of data.
        
        Returns:
            pd.Dataframe: Most recent batch of data.
        '''

        url = 'https://imperial-college.splunkcloud.com:8089/servicesNS/occupancy_api/imperial_college/search/v2/jobs/export'
        response = requests.post(url, headers=self.headers, data=self.data)

        assert response.status_code == 200, f'Error: {response.status_code}'

        data = self.parse_multiple_json(response.text)
        data = [entry['result'] for entry in data]
        data = pd.DataFrame(data)
        print(data.head())
        # data = data.sort_values(by='timestamp', ascending=True)
        # data = data.reset_index(drop=True)

        return data


    def parse_multiple_json(self, text):
        '''
        Convert a string with multiple JSON objects to a list of JSON objects.
        
        Args:
            text (str): String with multiple JSON objects.
        '''

        json_objects = []
        buffer = ""
        open_brackets = 0

        for char in text:
            buffer += char
            if char == '{':
                open_brackets += 1
            elif char == '}':
                open_brackets -= 1
                if open_brackets == 0:
                    try:
                        json_objects.append(json.loads(buffer))
                    except json.JSONDecodeError:
                        print("Failed to decode JSON:", buffer)
                    buffer = ""

        return json_objects



if __name__ == '__main__':
    api = Data_API()
    api.get_last_batch()
