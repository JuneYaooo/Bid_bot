import os
import shutil
import pandas as pd
from dotenv import load_dotenv
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
    for doc_type in ["toubiao_file", "zhaobiao_file"]:
        file_name = input(f"Enter the file name for {doc_type}: ")
        raw_file_path = os.path.join("data", "raw_files", file_name)
        if not os.path.exists(raw_file_path):
            print(f"File '{file_name}' not found in raw_files directory.")

            raise NotImplementedError("File '{file_name}' not found in raw_files directory.")
        
        # 将文件复制到项目的raw文件夹中
        shutil.copy(raw_file_path, os.path.join(project_path, 'raw', file_name))
        print(f"Copied {file_name} to project directory.")
        
        # 解析文件
        project_data_config = project_manager.load_project_config(project_path)
        if (os.getenv('OCR_ENABLED')==False and project_data_config['parsed_files'][doc_type]["txt_finished"]) or (os.getenv('OCR_ENABLED') and project_data_config['parsed_files'][doc_type]["txt_finished"] and project_data_config['parsed_files'][doc_type]["ocr_finished"]):
            update_parse = input(f"Do you want to update the parsing for {file_name}? (yes/no): ").lower() == 'yes'
            if update_parse:
                parsed_data = project_manager.parse_document(raw_file_path,project_name, document_type=doc_type, update=True, ocr_enabled=os.getenv('OCR_ENABLED'))
        else:
            print("os.getenv('OCR_ENABLED')",os.getenv('OCR_ENABLED'))
            parsed_data = project_manager.parse_document(raw_file_path,project_name, document_type=doc_type, update=False, ocr_enabled=os.getenv('OCR_ENABLED'))            
        # # 更新项目配置
        # project_manager.update_project_config(project_path, f"{doc_type}_path", raw_file_path)
        # project_manager.update_project_config(project_path, f"{doc_type}_parsed", parsed_data)
        # print(f"{doc_type} parsed and configuration updated.")

    # 解析后的数据
    config_data = project_manager.load_project_config(project_path)
    tender_document_parsed = config_data.get("parsed_files", {}).get("zhaobiao_file", {})
    bid_document_parsed = config_data.get("parsed_files", {}).get("toubiao_file", {})

    tender_document_text = "\n\n".join([item['text'] for item in tender_document_parsed.get('pdf_text', [])])
    bid_document_text = "\n\n".join([item['text'] for item in bid_document_parsed.get('pdf_text', [])])
    
    # # 处理投标文件并获取嵌入
    # bid_document_embeddings = process_document(bid_document_text)
    # print("Bid document processing and embeddings generation completed.")
    
    # 使用LLM进行招标要求提取
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": extract_requirements_prompt + tender_document_text}
    ]
    tender_requirements = llm_client.get_completion(messages)
    print("Extracted requirements from tender document.")
    parsed_json_tender_requirements = extract_list_from_text(tender_requirements)
    
    # 分析投标文件
    for requirement_item in parsed_json_tender_requirements:
        # 调用函数并打印结果
        keywords = requirement_item['关键词']
        print('keywords~',keywords)
        keywords_list = keywords.split(',')
        print('keywords_list~',keywords_list)
        top_paragraphs_list  = []
        for key in keywords_list:
            bid_document_similar_paragraphs = find_similar_paragraphs(key)
            top_paragraphs_list += bid_document_similar_paragraphs
            print('type',type(key),key)
        top_paragraphs= remove_duplicates_and_sort(top_paragraphs_list)
        requirement_item['检索文档'] = top_paragraphs
        bid_document_references = format_references(top_paragraphs)
        print('formatted_references~~`',bid_document_references)
        messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": eval_requirements_prompt + bid_document_references}
        ]
        requirement_eval_res= llm_client.get_completion(messages)
        requirement_item['评估结果'],requirement_item['参考内容'] = adjust_order(requirement_eval_res, top_paragraphs)
        print(requirement_eval_res)
        
    print("Bid document analyzed and references formatted.")

    toubiao_eval_df = pd.DataFrame(parsed_json_tender_requirements)
    output_report_path = os.path.join(project_manager.project_dir, project_name, 'reports','投标评估表.xlsx')
    toubiao_eval_df[['序号', '要求类型', '关键词', '具体要求', '评估结果', '参考内容']].to_excel(output_report_path, index=False)
    project_manager.update_project_config(project_path, f"parsed_files.reports", output_report_path)
    
    # # 生成投标分析报告（假设用pandas生成excel文件）
    # tender_requirements_df = pd.DataFrame([{"requirement": req} for req in tender_requirements])
    # bid_document_references_df = pd.DataFrame(bid_document_references)

    # report_path = os.path.join(project_path, 'reports', 'bid_analysis_report.xlsx')
    # with pd.ExcelWriter(report_path) as writer:
    #     tender_requirements_df.to_excel(writer, sheet_name='Tender Requirements', index=False)
    #     bid_document_references_df.to_excel(writer, sheet_name='Bid Document References', index=False)
    # print(f"Bid analysis report generated at {report_path}")

if __name__ == "__main__":
    main()
