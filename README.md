# Bid_bot

## 项目简介
Bid_bot 是一个允许用户输入投标文件的路径和招标文件的路径，然后自动提取投标文件中的要求，并检索到招标文件相应的响应内容的项目。

## 安装步骤

### 使用 Conda 创建环境

1. 克隆仓库到本地：
    ```bash
    git clone https://github.com/JuneYaooo/Bid_bot.git
    cd Bid_bot
    ```

2. 使用 Conda 创建环境：
    ```bash
    conda env create -f environment.yml
    conda activate bidenv
    ```

### 使用 Python 虚拟环境

#### Linux 或 macOS

1. 克隆仓库到本地：
    ```bash
    git clone https://github.com/JuneYaooo/Bid_bot.git
    cd Bid_bot
    ```

2. 创建并激活虚拟环境：
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. 安装依赖项：
    ```bash
    pip install -r requirements.txt
    ```

#### Windows

1. 克隆仓库到本地：
    ```bash
    git clone https://github.com/JuneYaooo/Bid_bot.git
    cd Bid_bot
    ```

2. 创建并激活虚拟环境：
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3. 安装依赖项：
    ```bash
    pip install -r requirements.txt
    ```

## 使用方法

1. 配置环境变量：
    在项目根目录下复制 `.env.template` 文件并重命名为 `.env`，然后根据需要填写配置项：
    ```bash
    cp .env.template .env
    ```

    `.env` 文件中的配置项说明：
    - `OCR_ENABLED`: 是否启用OCR（光学字符识别）功能，`True` 或 `False`。
    - `SUMMARY_ENABLED`: 是否启用模型检索后总结能力（如果出于隐私考虑，不想让模型读取自己的投标文件，可以不启用这个，不启用的状态下，只包含招标要求对投标文件的检索能力），`True` 或 `False`。
    - `LLM_TYPE`: 使用的语言模型类型，可以是 `gpt` 或 `kimi`。
    - `OPENAI_MODEL_NAME`: OpenAI 模型名称，例如 `gpt-4o`。
    - `OPENAI_API_KEY`: 你的 OpenAI API 密钥。
    - `OPENAI_BASE_URL`: OpenAI API 的基础URL。
    - `MOONSHOT_MODEL_NAME`: Moonshot 模型名称，例如 `moonshot-v1-32k`。
    - `MOONSHOT_API_KEY`: 你的 Moonshot API 密钥。
    - `MOONSHOT_BASE_URL`: Moonshot API 的基础URL。

2. 上传文件：
    将你的招标文件和投标文件上传到当前目录的 `./data/raw_files` 文件夹下。

3. 运行主脚本：
    ```bash
    python main.py
    ```

    启动后，命令行界面会提示你输入项目名称和文件名，并询问是否更新解析结果。例如：
    ```
    Clients and project manager initialized.
    Enter project name: shidong_hospital
    Project 'data/workspace/shidong_hospital/config.json' already exists. Loading existing configuration.
    Project 'shidong_hospital' created at data/workspace/shidong_hospital
    Enter the file name for zhaobiao_file: 招标文件.pdf
    Do you want to update the parsing for 招标文件.pdf? (yes/no): no
    Enter the file name for toubiao_file: 投标文件.pdf
    Do you want to update the parsing for 投标文件.pdf? (yes/no): no
    Extracted requirements from tender document.
    ```

    如果项目之前已经解析过某个文件，系统会提示你是否更新解析结果；如果没有解析过，则会自动进行解析。

## 待优化列表

- [ ] 单独把关键词放在记忆模块中
- [ ] 添加本地 embedding 模型
- [ ] 添加 UI 界面
