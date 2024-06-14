from src.llms.base import BaseClient
import os
import requests
from openai import OpenAI

class KimiClient(BaseClient):
    def __init__(self):
        self.api_key = os.getenv('MOONSHOT_API_KEY')
        self.base_url = os.getenv('MOONSHOT_BASE_URL')
        self.model = os.getenv('MOONSHOT_MODEL_NAME')
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_completion(self, messages):
        completion = self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        temperature=0.3,
        )
        res = completion.choices[0].message.content
        return res

