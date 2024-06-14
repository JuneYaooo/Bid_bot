from dotenv import load_dotenv
import os
from src.llms.gpt_client import GPTClient
from src.llms.kimi_client import KimiClient

load_dotenv()

class LLMFactory:
    @staticmethod
    def create_client(model_name=None):
        if model_name is None:
            model_name = os.getenv('LLM_MODEL', 'gpt')

        if model_name == 'gpt':
            return GPTClient()
        elif model_name == 'kimi':
            return KimiClient()
        else:
            raise ValueError(f"Unknown model name: {model_name}")
