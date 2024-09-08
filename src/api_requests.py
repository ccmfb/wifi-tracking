import requests
import warnings

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