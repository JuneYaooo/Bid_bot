import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
from src.llms.base import BaseClient
import base64
from openai import OpenAI
import os

# 加载 .env 文件
load_dotenv()
class GPTClient(BaseClient):
    def __init__(self, model=None):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = os.getenv('OPENAI_BASE_URL')
        self.model = model if model else os.getenv('OPENAI_MODEL_NAME') 
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_completion(self, messages):
        completion = self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        temperature=0.3,
        )
        res = completion.choices[0].message.content
        return res

    def extract_from_image(self, image_path, prompt):
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个OCR模型，可以帮我理解图像内容！"},
                    {"role": "user", "content": [{"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}]
                    }
                ],
                temperature=0.0,
            )

        ocr_result = response.choices[0].message.content
        ocr_result = response['choices'][0]['message']['content']
        return ocr_result
    
    def get_embedding(self, text):
        if not text.strip():  # Ensure text is not empty or just whitespace
            raise ValueError("The text to be embedded is empty.")
        text = text.replace("\n", " ")
        embedding = self.client.embeddings.create(input=[text], model=self.model).data[0].embedding
        if not embedding:  # Ensure embedding is not empty
            raise ValueError("The embedding is empty.")
        return embedding