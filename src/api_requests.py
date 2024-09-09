import requests

from dotenv import dotenv_values


class API_Requests:
    def __init__(self) -> None:
        config = dotenv_values("../.env")

        self.headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en;q=0.9',
            'api_key': config['PYTHAGORAS_API_KEY'],
            'Connection': 'keep-alive',
            'Host': 'pim.pythagoras.se',
            'Referer': 'https://pim.pythagoras.se/imp_datamanager/api/',
        }


    def get_floor_ids(self) -> list:
        '''
        Get the list of floor IDs.
        
        Returns:
            floor_ids (list): List of floor IDs.
        '''

        url = 'https://pim.pythagoras.se/imp_datamanager/rest/v1/floor'
        response = requests.get(url, headers=self.headers)

        assert response.status_code == 200, f'Error: {response.status_code}'
        floors = response.json()

        floor_ids = [floor['id'] for floor in floors]
        return floor_ids


    def get_floor_workspace_info(self, floor_id: int) -> list:
        '''
        Get the workspace data for a floor.
        
        Args:
            floor_id (int): Floor ID.
            
        Returns:
            data_workspace (dict): Workspace data for the floor.
        '''

        url = f'https://pim.pythagoras.se/imp_datamanager/rest/v1/floor/{floor_id}/workspace/info?includeOutline=true'
        response = requests.get(url, headers=self.headers)

        assert response.status_code == 200, f'Error: {response.status_code}'
        data_workspace = response.json()

        return data_workspace

    
    def get_floor_roomIds(self, floor_id: int) -> list:
        '''
        Get the room IDs for a floor.
        
        Args:
            floor_id (int): Floor ID.
            
        Returns:
            room_ids (list): List of room IDs.
        '''

        url = f'https://pim.pythagoras.se/imp_datamanager/rest/v1/floor/{floor_id}/workspace'
        response = requests.get(url, headers=self.headers)

        assert response.status_code == 200, f'Error: {response.status_code}'
        workspaces = response.json()
        room_ids = [workspace['id'] for workspace in workspaces]

        return room_ids


    def get_floor_info(self, floor_id: int) -> dict:
        '''
        Get the floor information.
        
        Args:
            floor_id (int): Floor ID.
            
        Returns:
            floor_info (dict): Floor information.
        '''

        url = f'https://pim.pythagoras.se/imp_datamanager/rest/v1/floor/{floor_id}/info'
        response = requests.get(url, headers=self.headers)

        assert response.status_code == 200, f'Error: {response.status_code}'
        floor_info = response.json()

        return floor_info


    def get_organisations(self) -> list:
        '''
        Get the list of organisations.
        
        Returns:
            organisations (list): List of organisations.
        '''

        url = "https://pim.pythagoras.se/imp_datamanager/rest/v1/organisation/info?orderAsc=true"
        response = requests.get(url, headers=self.headers)

        assert response.status_code == 200, f'Error: {response.status_code}'
        organisations = response.json()

        return organisations

# Testing the API_Requests class
if __name__ == '__main__':
    api_requests = API_Requests()
    organisations = api_requests.get_organisations()
    print(organisations)