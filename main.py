import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

from src.llms.llm_factory import LLMFactory
from src.embeddings.embedding_utils import find_similar_paragraphs
from src.process.project_manager import ProjectManager
from src.memory.memory_manager import MemoryManager
from src.prompts.base_prompt import extract_requirements_prompt,eval_requirements_prompt
from src.process.file_utils import extract_list_from_text, remove_duplicates_and_sort,adjust_order, format_references


def main():
    llm_client = LLMFactory.create_client()
    memory_manager = MemoryManager() #目前还没写入
    project_manager = ProjectManager()
    print("Clients and project manager initialized.")

    # 创建项目
    project_name = input("Enter project name: ")
    project_path = project_manager.create_project(project_name)
    print(f"Project '{project_name}' created at {project_path}")

    # 上传并解析招标文件和投标文件
    for doc_type in ["zhaobiao_file","toubiao_file"]:
        file_name = input(f"Enter the file name for {doc_type}: ")
        raw_file_path = os.path.join("data", "raw_files", file_name)
        if not os.path.exists(raw_file_path):
            print(f"File '{file_name}' not found in raw_files directory.")
            raise NotImplementedError("File '{file_name}' not found in raw_files directory.")
        
        
        # 解析文件
        project_data_config = project_manager.load_project_config(project_path)
        if (os.getenv('OCR_ENABLED')=='False' and project_data_config['parsed_files'][doc_type]["txt_finished"]==True) or (os.getenv('OCR_ENABLED')=='True' and project_data_config['parsed_files'][doc_type]["txt_finished"]==True and project_data_config['parsed_files'][doc_type]["ocr_finished"])==True:
            update_parse = input(f"Do you want to update the parsing for {file_name}? (yes/no): ").lower() == 'yes'
            if update_parse:
                parsed_data = project_manager.parse_document(raw_file_path,file_name,project_name, document_type=doc_type, update=True, ocr_enabled=os.getenv('OCR_ENABLED'))
        else:
            parsed_data = project_manager.parse_document(raw_file_path,file_name,project_name, document_type=doc_type, update=False, ocr_enabled=os.getenv('OCR_ENABLED'))            

    # 解析后的数据
    config_data = project_manager.load_project_config(project_path)
    tender_document_parsed = config_data.get("parsed_files", {}).get("zhaobiao_file", {})
    bid_document_parsed = config_data.get("parsed_files", {}).get("toubiao_file", {})

    tender_document_text = "\n\n".join([item['text'] for item in tender_document_parsed.get('pdf_text', [])])
    bid_document_text = "\n\n".join([item['text'] for item in bid_document_parsed.get('pdf_text', [])])
    
    
    # 使用LLM进行招标要求提取
    parsed_json_tender_requirements = None
    max_attempts = 3

    for attempt in range(max_attempts):
        messages = [
            {"role": "system", "content": "You are a Bid and Tender Specialist."},
            {"role": "user", "content": extract_requirements_prompt + tender_document_text}
        ]
        tender_requirements = llm_client.get_completion(messages)
        print(f"Attempt {attempt + 1}: Extracted requirements from tender document.")
        
        parsed_json_tender_requirements = extract_list_from_text(tender_requirements)
        
        if parsed_json_tender_requirements is not None:
            break
        
        print(f"Attempt {attempt + 1} failed. Retrying...")

    if parsed_json_tender_requirements is None:
        print("Failed to extract requirements after 3 attempts.")
    else:
        print("Successfully extracted requirements.")
    
    
    if os.getenv('SUMMARY_ENABLED') == 'True' or os.getenv('SUMMARY_ENABLED'):
        # 分析投标文件
        for requirement_item in parsed_json_tender_requirements:
            # 调用函数并打印结果
            keywords = requirement_item['关键词']
            keywords_list = keywords.split(',')
            top_paragraphs_list  = []
            for key in keywords_list:
                bid_document_similar_paragraphs = find_similar_paragraphs(key,bid_document_parsed['embedding_file_path'])
                top_paragraphs_list += bid_document_similar_paragraphs
                print('type',type(key),key)
            top_paragraphs= remove_duplicates_and_sort(top_paragraphs_list)
            requirement_item['检索文档'] = top_paragraphs
            bid_document_references = format_references(top_paragraphs)
            messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": eval_requirements_prompt.replace('{具体要求}',requirement_item['具体要求']) + bid_document_references}
            ]
            requirement_eval_res= llm_client.get_completion(messages)
            requirement_item['评估结果'],requirement_item['精筛参考内容'] = adjust_order(requirement_eval_res, top_paragraphs)
            select_columns = ['序号', '要求类型', '关键词', '具体要求', '评估结果', '精筛参考内容','检索文档']
    else:
        # 分析投标文件
        for requirement_item in parsed_json_tender_requirements:
            # 调用函数并打印结果
            keywords = requirement_item['关键词']
            keywords_list = keywords.split(',')
            top_paragraphs_list  = []
            for key in keywords_list:
                bid_document_similar_paragraphs = find_similar_paragraphs(key,bid_document_parsed['embedding_file_path'])
                top_paragraphs_list += bid_document_similar_paragraphs
                print('type',type(key),key)
            top_paragraphs= remove_duplicates_and_sort(top_paragraphs_list)
            requirement_item['检索文档'] = top_paragraphs
            bid_document_references = format_references(top_paragraphs)
            select_columns = ['序号', '要求类型', '关键词', '具体要求', '检索文档']

    
    current_time = datetime.now().strftime('%Y%m%d%H%M%S')
    toubiao_eval_df = pd.DataFrame(parsed_json_tender_requirements)
    output_report_path = os.path.join(project_manager.project_dir, project_name,"toubiao_file", 'reports',f'投标评估表_{current_time}.xlsx')
    toubiao_eval_df[select_columns].to_excel(output_report_path, index=False)
    project_manager.update_project_config(project_path, f"parsed_files.reports", output_report_path)
    print("Bid document analyzed and output report:",output_report_path)

if __name__ == "__main__":
    main()
