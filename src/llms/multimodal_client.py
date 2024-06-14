import os
import requests
from src.llms.base import BaseClient

class MultimodalClient(BaseClient):
    def __init__(self):
        self.api_key = os.getenv('MULTIMODAL_API_KEY')
        self.base_url = os.getenv('MULTIMODAL_BASE_URL')

    def get_completion(self, messages):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.post(
            f'{self.base_url}/v1/completions',
            json={'messages': messages},
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    def extract_from_image(self, image_path):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f'{self.base_url}/v1/extract',
                headers=headers,
                files=files
            )
        response.raise_for_status()
        return response.json()
