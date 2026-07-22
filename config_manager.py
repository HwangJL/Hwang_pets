# -*- coding: utf-8 -*-
"""配置持久化管理：JSON 格式存储到用户目录"""
import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".desktop_pet")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "ai": {
        "enabled": False,
        "provider": "openai_compatible",  # 渠道：openai_compatible / volcengine / qwen / deepseek / spark
        "api_url": "",
        "api_key": "",
        "model": ""
    },
    "knowledge_base": {
        "folder_path": "",
        "todos": ""
    },
    "phrase": {
        "mode": "custom",  # "custom" 或 "todo"
        "custom_text": ""
    }
}


def load_config():
    """加载配置，不存在则返回默认配置"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 补全缺失字段
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    # 合并默认值
    result = {}
    for section, defaults in DEFAULT_CONFIG.items():
        result[section] = {}
        section_data = config.get(section, {})
        for key, default_val in defaults.items():
            result[section][key] = section_data.get(key, default_val)
    return result


def save_config(config):
    """保存配置到本地文件"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
