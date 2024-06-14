import fitz  # PyMuPDF
from PIL import Image
import io
import os
import json
import base64
from openai import OpenAI
from src.llms.gpt_client import GPTClient
from src.prompts.base_prompt import *
import re

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def resize_image(image, max_size=150):
    width, height = image.size
    if width > height:
        if width > max_size:
            height = int((max_size / width) * height)
            width = max_size
    else:
        if height > max_size:
            width = int((max_size / height) * width)
            height = max_size
    return image.resize((width, height), Image.Resampling.LANCZOS)

def process_pdf(file_path, output_dir=".", index_file="image_index.json", text_file="pdf_text.json"):
    # 创建保存图像的目录
    os.makedirs(os.path.join(output_dir, 'ocr_images'), exist_ok=True)
    
    doc = fitz.open(file_path)
    ocr_candidates = []
    pdf_text = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # 提取矢量文本部分
        text = page.get_text("text")
        # pdf_text.append({"page_num": page_num + 1, "text": text})
        
        # 查找图像区域进行OCR
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            # 图像标识
            image_identifier = f"[IMAGE_{page_num + 1}_{img_index + 1}]"
            
            # 在文本中插入图像标识
            text += f"\n{image_identifier}\n"
            
            # 保存需要OCR的部分
            ocr_candidates.append({
                "page_num": page_num + 1,
                "img_index": img_index + 1,
                "image_identifier": image_identifier,
                "image": image
            })
            
            # 保存图像到文件
            image_path = os.path.join(output_dir, f"page_{page_num + 1}_img_{img_index + 1}.png")
            image.save(image_path)
        pdf_text.append({"page_num": page_num + 1, "text": text})
    # 保存图片信息存储索引文件
    with open(os.path.join(output_dir, index_file), "w", encoding='utf-8') as json_file:
        json.dump([{"page_num": item["page_num"], "img_index": item["img_index"], "image_path": os.path.join(output_dir, 'ocr_images', f"page_{item['page_num']}_img_{item['img_index']}.png")} for item in ocr_candidates], json_file, ensure_ascii=False, indent=4)

    # 保存PDF文本
    with open(os.path.join(output_dir, text_file), "w", encoding='utf-8') as json_file:
        json.dump(pdf_text, json_file, ensure_ascii=False, indent=4)
    
    return ocr_candidates, pdf_text

def ocr_images(index_file="image_index.json", ocr_results_file="ocr_results.json", output_dir="."):
    # 创建保存OCR结果的目录
    os.makedirs(os.path.join(output_dir, 'ocr_results'), exist_ok=True)
    
    print('output_dir==',output_dir)
    with open(os.path.join(output_dir, index_file), "r", encoding='utf-8') as json_file:
        ocr_candidates = json.load(json_file)
    
    # 尝试读取已有的OCR结果
    if os.path.exists(os.path.join(output_dir, ocr_results_file)):
        with open(os.path.join(output_dir, ocr_results_file), "r", encoding='utf-8') as json_file:
            ocr_results = json.load(json_file)
    else:
        ocr_results = []

    # 找到未完成的图片索引
    completed_indexes = {(item["page_num"], item["img_index"]) for item in ocr_results}
    ocr_client = GPTClient()
    
    for item in ocr_candidates:
        page_num = item["page_num"]
        img_index = item["img_index"]
        image_path = item["image_path"]

        if (page_num, img_index) in completed_indexes:
            continue

        # 加载图像并调整大小
        image = Image.open(image_path)
        image = resize_image(image)
        resized_image_path = os.path.join(output_dir, f"resized_page_{page_num}_img_{img_index}.png")
        image.save(resized_image_path)

        # 编码图像为base64
        base64_image = encode_image(resized_image_path)
        print(f"Processing image {image_path}...")
        # 执行OCR
        try:
            ocr_result = ocr_client.extract_from_image(resized_image_path,ocr_prompt)
            # 保存OCR结果
            result = {
                "page_num": page_num,
                "img_index": img_index,
                "ocr_result": ocr_result,
                "image_path": image_path
            }
            ocr_results.append(result)

            # 每识别一张图片就保存OCR结果
            with open(os.path.join(output_dir, ocr_results_file), "w", encoding='utf-8') as json_file:
                json.dump(ocr_results, json_file, ensure_ascii=False, indent=4)
        except Exception as e:
                print(f"Failed to OCR image {image_path}: {e}")
                ocr_result = ""
    return ocr_results

def save_results(ocr_results_file = "ocr_results.json", text_file="pdf_text.json", output_dir="."):
    # 创建保存最终结果的目录
    os.makedirs(os.path.join(output_dir, "pdf_withocr"), exist_ok=True)

    # 读取PDF文本
    with open(text_file, "r", encoding='utf-8') as json_file:
        pdf_text = json.load(json_file)
    with open(ocr_results_file, "r", encoding='utf-8') as ocr_file:
        ocr_results = json.load(ocr_file)

    # 将PDF文本中的图片标识替换为OCR结果
    ocr_text = []
    for item in pdf_text:
        text = item["text"]
        page_num = item["page_num"]
        for result in ocr_results:
            if result["page_num"] == page_num:
                image_identifier = f"""[IMAGE_{result["page_num"]}_{result["img_index"]}]"""
                text = text.replace(image_identifier, result["ocr_result"])
        item['full_text'] = text
        ocr_text.append(text)

    with open(os.path.join(output_dir, "pdf_withocr", "ocr_pdf_document.json"), "w", encoding='utf-8') as json_file:
        json.dump(pdf_text, json_file, ensure_ascii=False, indent=4)




def extract_list_from_text(text):
    """
    从文本中提取列表内容并返回解析后的Python对象。

    :param text: 包含列表内容的输入文本
    :return: 解析后的Python对象，若未找到或解析失败则返回None
    """
    def try_json_loads(text):
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"json.loads解析错误: {e}")
            return None

    def extract_json_from_text(text):
        # 使用正则表达式匹配大括号中的JSON对象
        json_pattern = re.compile(r'{.*}', re.DOTALL)
        match = json_pattern.search(text)
        if match:
            return match.group(0)
        else:
            return None

    json_text = extract_json_from_text(text)
    
    if not json_text:
        print("未找到有效的JSON内容")
        return None

    data = try_json_loads(json_text)
    
    if data is not None and isinstance(data, dict):
        # 验证字典是否包含 "招标要求" 键
        if "招标要求" in data:
            data = data["招标要求"]
            if isinstance(data, list):
                valid_data = [item for item in data if isinstance(item, dict) and "关键词" in item and "具体要求" in item and "要求类型" in item]
                return valid_data
        else:
            print("未找到有效的列表内容")
            return None
    else:
        print("未找到有效的列表内容")
        return None
    

def adjust_order(llm_res, knowledge_res):
    # 解析llm_res中的文段标号
    llm_paragraphs = [int(num) for num in re.findall(r'\[No\.(\d+)\]', llm_res) if num.isdigit()]
    sort_llm_paragraphs = sorted(list(set(llm_paragraphs)))
    # 将列表转换成字典
    sort_llm_paragraphs_dict = {value: index+1 for index, value in enumerate(sort_llm_paragraphs)}

    # 根据文段标号过滤knowledge_res中的内容
    filtered_knowledge_res = [knowledge_res[i-1] for i in sort_llm_paragraphs]

    # 重新编码filtered_knowledge_res中的文段标号
    matches = re.findall(r'\[No\.(\d+)\]', llm_res)
    for match in matches:
        if int(match) in sort_llm_paragraphs_dict:
            llm_res = llm_res.replace(f'[No.{match}]', f'[No.{sort_llm_paragraphs_dict[int(match)]}]')

    return llm_res,filtered_knowledge_res

def remove_duplicates_and_sort(data):
    # 使用集合去重，但需要保持字典的顺序
    seen = set()
    unique_data = []
    for item in data:
        sentence_key = tuple(sorted(item['sentences']))  # 使用sentences列表的排序元组作为键
        if sentence_key not in seen:
            seen.add(sentence_key)
            unique_data.append(item)

    # 根据similarity排序
    unique_data.sort(key=lambda x: x['similarity'], reverse=True)  # 降序排序

    return unique_data

def format_references(data):
    references = []
    for index, item in enumerate(data, start=1):
        # 获取段落中的句子并添加参考文献编号
        sentence = item['sentences']
        reference = f"[No.{index}]{sentence}"
        references.append(reference)
    # 将所有句子拼接成一个字符串
    result = "\n\n".join(references)
    return result