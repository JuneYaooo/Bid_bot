import os
import json
import hashlib
from src.process.file_utils import process_pdf, ocr_images, save_results
from src.embeddings.embedding_utils import process_embedding_json

class ProjectManager:
    def __init__(self, project_dir='data/workspace'):
        self.project_dir = project_dir
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

    def create_project(self, project_name):
        project_path = os.path.join(self.project_dir, project_name)
        config_path = os.path.join(project_path, 'config.json')

        if os.path.exists(project_path):
            print(f"Project '{project_name}' already exists. Loading existing configuration.")
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return project_path

        os.makedirs(os.path.join(project_path, 'raw'), exist_ok=True)
        os.makedirs(os.path.join(project_path, 'parsed'), exist_ok=True)
        os.makedirs(os.path.join(project_path, 'reports'), exist_ok=True)
        
        self.config = {
            "project_name": project_name,
            "raw_files": {
                "toubiao_file_path": "",
                "zhaobiao_file_path": ""
            },
            "parsed_files": {
                "toubiao_file": {
                    "pdf_extract_path": "",
                    "ocr_images_path": "",
                    "ocr_results_path": "",
                    "image_index_path": "",
                    "ocr_pdf_extract_path": "",
                    "embedding_file_path": "",
                    "report_path" :"", 
                    "txt_finished": False,
                    "ocr_finished": False
                },
                "zhaobiao_file": {
                    "pdf_extract_path": "",
                    "ocr_images_path": "",
                    "ocr_results_path": "",
                    "image_index_path": "",
                    "ocr_pdf_extract_path": "",
                    "embedding_file_path": "",
                    "txt_finished": False,
                    "ocr_finished": False
                }
            },
            "reports": ""
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
        
        return project_path

    def _get_file_hash(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def _load_parsed_data(self, file_hash):
        parsed_file_path = os.path.join(self.project_dir, 'parsed_files', f"{file_hash}.json")
        if os.path.exists(parsed_file_path):
            with open(parsed_file_path, 'r') as f:
                return json.load(f)
        return None

    def _save_parsed_data(self, file_hash, data):
        parsed_file_path = os.path.join(self.project_dir, 'parsed_files', f"{file_hash}.json")
        with open(parsed_file_path, 'w') as f:
            json.dump(data, f)

    def parse_document(self, file_path, project_name, document_type, update=False, ocr_enabled=False):
        file_hash = self._get_file_hash(file_path)
        parsed_data = self._load_parsed_data(file_hash)
        project_path = os.path.join(self.project_dir, project_name)
       
        if parsed_data and not update:
            print("Using previously parsed data.")
            return parsed_data

        print("Parsing document...")
        embedding_file_path = os.path.join(self.project_dir, project_name,document_type+'.pkl')
        print('embedding_file_path',embedding_file_path)
        ocr_candidates, pdf_text = process_pdf(file_path,output_dir=os.path.join(project_path, 'parsed_files'))
        self.update_project_config(project_path, f"parsed_files.{document_type}.pdf_extract_path", os.path.join(project_path, 'parsed_files','pdf_text.json'))
        self.update_project_config(project_path, f"parsed_files.{document_type}.txt_finished", True)
        
        if ocr_enabled:
            print('ocr_enabled~~',ocr_enabled)
            ocr_results = ocr_images(ocr_candidates,output_dir=os.path.join(project_path, 'parsed_files'))
            save_results(ocr_results_file = os.path.join(project_path, 'parsed_files','ocr_results.json'), text_file=os.path.join(project_path, 'parsed_files','pdf_text.json'))
            self.update_project_config(project_path, f"parsed_files.{document_type}.ocr_results_path", os.path.join(project_path, 'parsed_files','ocr_results.json'))
            self.update_project_config(project_path, f"parsed_files.{document_type}.ocr_pdf_extract_path", os.path.join(project_path, 'parsed_files','ocr_pdf_document.json'))
            self.update_project_config(project_path, f"parsed_files.{document_type}.ocr_finished", True)
            process_embedding_json(os.path.join(project_path, 'parsed_files','ocr_pdf_document.json'), embedding_file_path)
        else:
            ocr_results = []
            process_embedding_json(os.path.join(project_path, 'parsed_files','ocr_pdf_document.json'), embedding_file_path)

        # parsed_data = {
        #     'pdf_text': pdf_text,
        #     'ocr_results': ocr_results
        # }

        # self._save_parsed_data(file_hash, parsed_data)
        return parsed_data

    def update_project_config(self, project_path, key, value):
        config_path = os.path.join(project_path, 'config.json')

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        keys = key.split('.')
        d = self.config
        for k in keys[:-1]:
            d = d[k]
        d[keys[-1]] = value

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    def load_project_config(self, project_path):
        config_path = os.path.join(project_path, 'config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
