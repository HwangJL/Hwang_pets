# -*- coding: utf-8 -*-
"""
控制台窗口：四大功能模块
1. 知识库&本周待办梳理
2. 桌宠点击话术自定义
3. AI大模型接入配置
4. 角色设定与外观更新
"""
import os
import sys
import json
import base64
import shutil
import tempfile
import traceback
import urllib.request
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QTextEdit, QRadioButton,
    QButtonGroup, QCheckBox, QFileDialog, QScrollArea, QFrame,
    QSizePolicy, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap
from config_manager import load_config, save_config


def _log(msg):
    """打印带时间戳的日志到 stderr（桌面宠物运行时会被重定向到 ~/DesktopPet_run.log）"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [AITodo] {msg}", file=sys.stderr, flush=True)


# ---------- AI 渠道预设 ----------
# key -> (显示名, 默认API地址, 默认模型名)
AI_PROVIDERS = {
    "openai_compatible": ("OpenAI兼容", "https://api.openai.com/v1/chat/completions", "gpt-3.5-turbo"),
    "volcengine": ("火山引擎(豆包)", "https://ark.cn-beijing.volces.com/api/v3/chat/completions", "doubao-seed-1-8-251228"),
    "qwen": ("通义千问", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "qwen-plus"),
    "deepseek": ("DeepSeek", "https://api.deepseek.com/v1/chat/completions", "deepseek-chat"),
    "spark": ("讯飞星火", "https://spark-api-open.xf-yun.com/v1/chat/completions", "generalv3.5"),
}

# 图片生成 API 渠道预设: key -> (图片生成地址, 默认模型名)
IMAGE_GEN_PRESETS = {
    "openai_compatible": ("https://api.openai.com/v1/images/generations", "dall-e-3"),
    "volcengine": ("https://ark.cn-beijing.volces.com/api/v3/images/generations", "doubao-seedream-3-0-t2i-250415"),
    "qwen": ("https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis", "wanx2.1-t2i-turbo"),
    "deepseek": ("", ""),  # DeepSeek 暂不支持图片生成
    "spark": ("", ""),     # 星火暂不支持
    "siliconflow": ("https://api.siliconflow.cn/v1/images/generations", "Kwai-Kolors/Kolors"),
}

# 角色设定图分析的 prompt 模板
CHARACTER_ANALYSIS_PROMPT = """根据我上传的参考图片，将其中的主体重新设计为一个长期可复用、特征稳定、适合制作桌面宠物的原创 IP 角色。
参考图片中的主体可能是人物、猫、狗、其他动物、玩偶、机器人、生物、物体或虚构形象。
请先自动识别主体类型，再提取它最有辨识度的特征，包括整体轮廓、身体比例、头部形状、五官布局、毛发或发型、耳朵、尾巴、角、翅膀、花纹、配色、服装和配饰等。
保留最关键的识别点，减少无关细节，不要随意增加原图中不存在的新设定。
请把主体转化为一个简洁、清晰、容易重复生成的Q版卡通 IP。整体使用明确轮廓、大色块和有限配色，减少复杂纹理、写实毛发、渐变、透明材质和细碎装饰。
角色需要在小尺寸下依然容易识别，身体结构清楚，适合后续制作 Idle、Walk、Run、Jump、Sleep、Think、Happy、Error 等桌宠动画。
请输出一张完整的角色设定图，展示同一个角色的正面、背面、左侧面、右侧面、左前 3/4 视角和右前 3/4 视角，并补充自然站立、行走、奔跑、坐下、跳跃、趴卧或漂浮等适合该主体的动作。
不要强行让动物或物体采用人类姿态，动作方式应符合主体本身的身体结构。
所有视角和动作必须保持同一个角色身份。角色的头身比例、身体结构、五官位置、耳朵大小、尾巴长度、毛发轮廓、花纹分布、服装、配饰和配色不能发生变化。
另外展示默认、开心、困惑、专注、生气、受惊、得意和困倦等表情。表情变化应建立在固定角色结构之上，只调整神态，不改变脸型、五官比例或主体身份。
最终效果应接近动画、游戏或品牌 IP 的正式 Character Sheet，而不是一张单独插画。
请优先保证角色一致性、结构清晰度和后续动画适配性。
设定图要求：第1行6个全身站姿（从左到右排列），第2行6个动作姿态，第3行8个表情头像。背景使用纯色（如浅黄色），方便后续自动切片。"""


# ---------- 样式 ----------
COMMON_STYLE = """
QMainWindow { background: #f5f5f5; }
QGroupBox {
    font-family: 'Microsoft YaHei'; font-size: 13px; font-weight: bold;
    color: #333; border: 1px solid #ddd; border-radius: 8px;
    margin-top: 12px; padding-top: 16px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QLabel { font-family: 'Microsoft YaHei'; font-size: 12px; color: #555; }
QLineEdit {
    font-family: 'Microsoft YaHei'; font-size: 12px; padding: 6px 8px;
    border: 1px solid #ccc; border-radius: 4px; background: white;
}
QLineEdit:disabled { background: #eee; color: #999; }
QTextEdit {
    font-family: 'Microsoft YaHei'; font-size: 12px; padding: 6px;
    border: 1px solid #ccc; border-radius: 4px; background: white;
}
QPushButton {
    font-family: 'Microsoft YaHei'; font-size: 12px; padding: 6px 16px;
    border: 1px solid #4a90d9; border-radius: 4px; background: #4a90d9;
    color: white;
}
QPushButton:hover { background: #5aa0e9; }
QPushButton:pressed { background: #3a80c9; }
QPushButton:disabled { background: #ccc; border-color: #ccc; color: #999; }
QRadioButton { font-family: 'Microsoft YaHei'; font-size: 12px; }
"""


class ToastLabel(QLabel):
    """轻量悬浮提示，3秒自动消失"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            QLabel {
                background: rgba(50,50,50,220); color: white;
                font-family: 'Microsoft YaHei'; font-size: 12px;
                padding: 8px 20px; border-radius: 6px;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.hide)

    def show_msg(self, text, duration=3000):
        self.setText(text)
        self.adjustSize()
        if self.parent():
            px = (self.parent().width() - self.width()) // 2
            py = self.parent().height() - self.height() - 30
            self.move(px, py)
        self.show()
        self._timer.start(duration)


class AITodoThread(QThread):
    """AI 梳理待办的子线程"""
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, folder_path, api_url, api_key, model, provider="openai_compatible"):
        super().__init__()
        self.folder_path = folder_path
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.provider = provider

    def run(self):
        _log("=" * 50)
        _log("AI待办梳理线程启动")
        _log(f"渠道: {self.provider}")
        _log(f"文件夹路径: {self.folder_path}")
        _log(f"API地址: {self.api_url}")
        _log(f"模型: {self.model}")
        _log(f"API Key: {self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else f"API Key: {self.api_key}")
        try:
            # ---------- 步骤1：读取文件夹 ----------
            _log("步骤1：开始读取知识库文件夹")
            if not os.path.isdir(self.folder_path):
                _log(f"错误：文件夹不存在 -> {self.folder_path}")
                self.error_signal.emit("知识库文件夹不存在")
                return
            _log(f"文件夹存在，开始遍历")

            contents = []
            all_files = os.listdir(self.folder_path)
            _log(f"文件夹内共发现 {len(all_files)} 个文件/子目录: {all_files}")

            matched_files = []
            for fname in all_files:
                fpath = os.path.join(self.folder_path, fname)
                if os.path.isfile(fpath) and fname.lower().endswith(
                        ('.txt', '.md', '.csv', '.json', '.log')):
                    matched_files.append(fname)
                    try:
                        file_size = os.path.getsize(fpath)
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read(5000)  # 限制每个文件5KB
                            contents.append(f"--- {fname} ---\n{content}")
                        _log(f"  已读取: {fname} (原始大小 {file_size} 字节, 截取 {len(content)} 字符)")
                    except Exception as e:
                        _log(f"  读取失败: {fname} -> {e}")

            _log(f"步骤1完成：匹配 {len(matched_files)} 个文本文件: {matched_files}")

            if not contents:
                _log("错误：未找到任何可读取的文本文件，发送错误信号")
                self.error_signal.emit("文件夹内未找到可读取的文本文件")
                return

            # ---------- 步骤2：合并内容 ----------
            _log("步骤2：合并文件内容")
            combined = "\n\n".join(contents)[:10000]  # 总计限制10KB
            _log(f"合并完成，总内容长度: {len(combined)} 字符")
            _log(f"合并内容前100字符预览: {combined[:100]}...")

            # ---------- 步骤3：构造API请求 ----------
            _log("步骤3：构造AI API请求")
            data = json.dumps({
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个助手。请根据以下文件内容，梳理出本周待办事项清单。"
                                   "按条目列出，每条一行，简洁清晰。"
                    },
                    {"role": "user", "content": combined}
                ]
            }).encode("utf-8")
            _log(f"请求体已构造，大小: {len(data)} 字节")

            req = urllib.request.Request(
                self.api_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            _log(f"Request对象已创建，URL: {self.api_url}")

            # ---------- 步骤4：发送请求 ----------
            _log("步骤4：发送HTTP请求到AI接口（超时30秒）")
            resp = urllib.request.urlopen(req, timeout=30)
            _log(f"收到HTTP响应，状态码: {resp.status}")

            # ---------- 步骤5：解析响应 ----------
            _log("步骤5：解析AI返回内容")
            raw_body = resp.read().decode("utf-8")
            _log(f"响应体大小: {len(raw_body)} 字符")
            _log(f"响应体前200字符预览: {raw_body[:200]}")

            result = json.loads(raw_body)
            _log(f"JSON解析成功，顶层keys: {list(result.keys())}")

            if "choices" not in result or len(result["choices"]) == 0:
                _log(f"错误：响应中无choices字段或为空，完整响应: {raw_body[:500]}")
                self.error_signal.emit("AI返回数据格式异常：缺少choices")
                return

            todos = result["choices"][0]["message"]["content"]
            _log(f"成功提取待办内容，长度: {len(todos)} 字符")
            _log(f"待办内容前100字符预览: {todos[:100]}")

            # ---------- 步骤6：发送完成信号 ----------
            _log("步骤6：发送finished信号，线程即将结束")
            self.finished_signal.emit(todos)
            _log("线程正常结束")

        except urllib.error.HTTPError as e:
            _log(f"HTTPError异常: code={e.code}, reason={e.reason}")
            try:
                err_body = e.read().decode("utf-8", errors="ignore")
                _log(f"HTTPError响应体: {err_body[:500]}")
            except Exception:
                pass
            _log(f"完整堆栈:\n{traceback.format_exc()}")
            self.error_signal.emit(f"AI接口返回错误: {e.code}")
        except urllib.error.URLError as e:
            _log(f"URLError异常: reason={e.reason}")
            _log(f"完整堆栈:\n{traceback.format_exc()}")
            self.error_signal.emit(f"网络请求失败: {e.reason}")
        except Exception as e:
            _log(f"未知异常: {type(e).__name__}: {str(e)}")
            _log(f"完整堆栈:\n{traceback.format_exc()}")
            self.error_signal.emit(f"解析失败: {str(e)}")
        _log("=" * 50)


class AITestThread(QThread):
    """AI 连通性测试子线程"""
    success_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, api_url, api_key, model, provider="openai_compatible"):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.provider = provider

    def run(self):
        try:
            data = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 10
            }).encode("utf-8")

            req = urllib.request.Request(
                self.api_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read().decode("utf-8"))
            reply = result["choices"][0]["message"]["content"]
            self.success_signal.emit(f"连通成功，AI回复：{reply[:30]}")

        except urllib.error.HTTPError as e:
            self.error_signal.emit(f"接口返回错误: {e.code}")
        except urllib.error.URLError as e:
            self.error_signal.emit(f"网络请求失败: {e.reason}")
        except Exception as e:
            self.error_signal.emit(f"连接失败: {str(e)}")


class ImageAnalysisThread(QThread):
    """AI 视觉分析上传的参考图，返回角色描述"""
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, image_path, api_url, api_key, model):
        super().__init__()
        self.image_path = image_path
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def run(self):
        _log(f"图片分析线程启动: {self.image_path}")
        try:
            # 读取图片并转 base64
            with open(self.image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")

            ext = os.path.splitext(self.image_path)[1].lower().lstrip(".")
            mime = f"image/{ext}" if ext in ("png", "jpeg", "jpg", "gif", "webp") else "image/png"

            data = json.dumps({
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CHARACTER_ANALYSIS_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_data}"}}
                    ]
                }],
                "max_tokens": 2000
            }).encode("utf-8")

            _log(f"视觉分析请求已构造，图片base64大小: {len(img_data)} 字符")

            req = urllib.request.Request(
                self.api_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read().decode("utf-8"))
            description = result["choices"][0]["message"]["content"]
            _log(f"图片分析完成，描述长度: {len(description)} 字符")
            self.finished_signal.emit(description)

        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="ignore")
                _log(f"图片分析HTTP错误: {e.code}, body: {err_body[:300]}")
            except Exception:
                pass
            self.error_signal.emit(f"视觉分析失败(HTTP {e.code})")
        except Exception as e:
            _log(f"图片分析异常: {traceback.format_exc()}")
            self.error_signal.emit(f"视觉分析失败: {str(e)}")


class ImageGenThread(QThread):
    """调用图片生成 API，返回生成图片的本地路径"""
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, prompt, gen_url, api_key, model):
        super().__init__()
        self.prompt = prompt
        self.gen_url = gen_url
        self.api_key = api_key
        self.model = model

    def run(self):
        _log(f"图片生成线程启动: model={self.model}, url={self.gen_url}")
        _log(f"prompt前100字: {self.prompt[:100]}...")
        try:
            data = json.dumps({
                "model": self.model,
                "prompt": self.prompt,
                "n": 1,
                "size": "1024x1024",
                "response_format": "url"
            }).encode("utf-8")

            req = urllib.request.Request(
                self.gen_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            _log("发送图片生成请求（超时120秒）")
            resp = urllib.request.urlopen(req, timeout=120)
            raw = resp.read().decode("utf-8")
            _log(f"图片生成响应: {raw[:300]}")

            result = json.loads(raw)

            # 兼容 OpenAI 格式: {"data": [{"url": "..."}]}
            img_url = None
            if "data" in result and len(result["data"]) > 0:
                img_url = result["data"][0].get("url") or result["data"][0].get("b64_json")

            if not img_url:
                self.error_signal.emit("图片生成API未返回图片URL")
                return

            # 下载图片或解码 base64
            tmp_path = os.path.join(tempfile.gettempdir(), "pet_character_sheet.png")
            if img_url.startswith("http"):
                _log(f"下载图片: {img_url[:100]}")
                img_resp = urllib.request.urlopen(img_url, timeout=60)
                with open(tmp_path, "wb") as f:
                    f.write(img_resp.read())
            else:
                # base64 格式
                with open(tmp_path, "wb") as f:
                    f.write(base64.b64decode(img_url))

            _log(f"图片已保存到: {tmp_path}")
            self.finished_signal.emit(tmp_path)

        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="ignore")
                _log(f"图片生成HTTP错误: {e.code}, body: {err_body[:300]}")
            except Exception:
                pass
            self.error_signal.emit(f"图片生成失败(HTTP {e.code})")
        except Exception as e:
            _log(f"图片生成异常: {traceback.format_exc()}")
            self.error_signal.emit(f"图片生成失败: {str(e)}")


class SpriteSliceThread(QThread):
    """自动切片设定图为精灵图"""
    finished_signal = pyqtSignal(list)   # [(name, path, w, h), ...]
    log_signal = pyqtSignal(list)         # [str, ...]
    error_signal = pyqtSignal(str)

    def __init__(self, sheet_path, output_dir):
        super().__init__()
        self.sheet_path = sheet_path
        self.output_dir = output_dir

    def run(self):
        _log(f"切片线程启动: {self.sheet_path} -> {self.output_dir}")
        try:
            from sprite_slicer import slice_character_sheet
            results, log_lines = slice_character_sheet(self.sheet_path, self.output_dir)
            self.log_signal.emit(log_lines)
            if results:
                self.finished_signal.emit(results)
            else:
                self.error_signal.emit("未检测到可切片的角色区域")
        except Exception as e:
            _log(f"切片异常: {traceback.format_exc()}")
            self.error_signal.emit(f"切片失败: {str(e)}")


class ConsoleWindow(QMainWindow):
    """控制台主窗口"""

    def __init__(self, config, on_config_changed=None, on_sprites_updated=None):
        super().__init__()
        self.config = config
        self.on_config_changed = on_config_changed
        self.on_sprites_updated = on_sprites_updated
        self._ai_thread = None
        self._test_thread = None
        self._analysis_thread = None
        self._gen_thread = None
        self._slice_thread = None
        self._current_sheet_path = ""

        self.setWindowTitle("桌面宠物 - 控制台")
        self.setMinimumSize(560, 760)
        self.setStyleSheet(COMMON_STYLE)

        self._toast = ToastLabel(self)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        central = QWidget()
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(self._build_module1())
        layout.addWidget(self._build_module2())
        layout.addWidget(self._build_module3())
        layout.addWidget(self._build_module4())
        layout.addStretch()

        self._load_config_to_ui()

    # ---------- 模块一：知识库&待办 ----------
    def _build_module1(self):
        grp = QGroupBox("功能一：知识库 & AI梳理本周待办")
        layout = QVBoxLayout(grp)

        # 文件夹选择
        row1 = QHBoxLayout()
        self.btn_select_folder = QPushButton("选择知识库文件夹")
        self.btn_select_folder.clicked.connect(self._select_folder)
        self.lbl_folder = QLabel("未选择任何文件夹")
        self.lbl_folder.setWordWrap(True)
        self.lbl_folder.setStyleSheet("color: #999;")
        row1.addWidget(self.btn_select_folder)
        row1.addWidget(self.lbl_folder, 1)
        layout.addLayout(row1)

        # AI梳理按钮
        self.btn_ai_todo = QPushButton("AI梳理本周待办")
        self.btn_ai_todo.clicked.connect(self._ai_generate_todo)
        layout.addWidget(self.btn_ai_todo)

        # 结果展示
        self.txt_todo = QTextEdit()
        self.txt_todo.setReadOnly(True)
        self.txt_todo.setPlaceholderText("梳理结果将显示在此处...")
        self.txt_todo.setMinimumHeight(120)
        layout.addWidget(self.txt_todo)

        # 生成状态标签
        self.lbl_todo_result = QLabel("尚未生成待办")
        self.lbl_todo_result.setWordWrap(True)
        self.lbl_todo_result.setStyleSheet("color: #999; font-size: 12px; padding: 4px;")
        layout.addWidget(self.lbl_todo_result)

        return grp

    def _select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择知识库文件夹")
        if path:
            self.config["knowledge_base"]["folder_path"] = path
            self.lbl_folder.setText(path)
            self.lbl_folder.setStyleSheet("color: #555;")
            save_config(self.config)
            self._update_ai_todo_button()
            self._toast.show_msg("知识库路径已保存")

    def _ai_generate_todo(self):
        if not self.config["ai"]["enabled"]:
            self._toast.show_msg("AI能力已关闭，请先开启")
            return
        folder = self.config["knowledge_base"]["folder_path"]
        if not folder:
            self._toast.show_msg("请先选择知识库文件夹")
            return

        self.btn_ai_todo.setEnabled(False)
        self.btn_ai_todo.setText("正在AI解析梳理待办...")

        self._ai_thread = AITodoThread(
            folder,
            self.config["ai"]["api_url"],
            self.config["ai"]["api_key"],
            self.config["ai"]["model"],
            self.config["ai"].get("provider", "openai_compatible")
        )
        self._ai_thread.finished_signal.connect(self._on_todo_finished)
        self._ai_thread.error_signal.connect(self._on_todo_error)
        self._ai_thread.start()

    def _on_todo_finished(self, todos):
        self.txt_todo.setPlainText(todos)
        self.config["knowledge_base"]["todos"] = todos
        save_config(self.config)
        self.btn_ai_todo.setEnabled(True)
        self.btn_ai_todo.setText("AI梳理本周待办")
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_todo_result.setStyleSheet("color: #2e8b57; font-size: 12px; padding: 4px;")
        self.lbl_todo_result.setText(f"✓ {now} 待办梳理成功")
        if self.on_config_changed:
            self.on_config_changed()

    def _on_todo_error(self, err):
        self.btn_ai_todo.setEnabled(True)
        self.btn_ai_todo.setText("AI梳理本周待办")
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_todo_result.setStyleSheet("color: #c0392b; font-size: 12px; padding: 4px;")
        self.lbl_todo_result.setText(f"✗ {now} {err}")

    # ---------- 模块二：话术自定义 ----------
    def _build_module2(self):
        grp = QGroupBox("功能二：桌宠点击话术自定义")
        layout = QVBoxLayout(grp)

        # 模式切换
        row = QHBoxLayout()
        self.rb_custom = QRadioButton("自定义文本")
        self.rb_todo = QRadioButton("引用本周待办")
        self._phrase_group = QButtonGroup(self)
        self._phrase_group.addButton(self.rb_custom)
        self._phrase_group.addButton(self.rb_todo)
        self.rb_custom.toggled.connect(self._on_phrase_mode_changed)
        row.addWidget(self.rb_custom)
        row.addWidget(self.rb_todo)
        row.addStretch()
        layout.addLayout(row)

        # 文本框
        self.txt_phrase = QTextEdit()
        self.txt_phrase.setPlaceholderText("请输入自定义话术内容...")
        self.txt_phrase.setMinimumHeight(100)
        layout.addWidget(self.txt_phrase)

        # 保存按钮
        self.btn_save_phrase = QPushButton("保存配置")
        self.btn_save_phrase.clicked.connect(self._save_phrase)
        layout.addWidget(self.btn_save_phrase)

        return grp

    def _on_phrase_mode_changed(self):
        if self.rb_custom.isChecked():
            self.txt_phrase.setReadOnly(False)
            self.txt_phrase.setPlaceholderText("请输入自定义话术内容...")
        else:
            self.txt_phrase.setReadOnly(True)
            todos = self.config["knowledge_base"]["todos"]
            if todos:
                self.txt_phrase.setPlainText(todos)
            else:
                self.txt_phrase.setPlainText("")
                self.txt_phrase.setPlaceholderText("暂无本周待办内容，请先梳理知识库")

    def _save_phrase(self):
        if self.rb_custom.isChecked():
            self.config["phrase"]["mode"] = "custom"
            self.config["phrase"]["custom_text"] = self.txt_phrase.toPlainText()
        else:
            self.config["phrase"]["mode"] = "todo"
        save_config(self.config)
        if self.on_config_changed:
            self.on_config_changed()
        self._toast.show_msg("话术配置保存成功")

    # ---------- 模块三：AI配置 ----------
    def _build_module3(self):
        grp = QGroupBox("功能三：AI大模型接入配置")
        layout = QVBoxLayout(grp)

        # AI开关
        row = QHBoxLayout()
        self.chk_ai_enabled = QCheckBox("AI能力总开关")
        self.chk_ai_enabled.toggled.connect(self._on_ai_toggle)
        row.addWidget(self.chk_ai_enabled)
        row.addStretch()
        layout.addLayout(row)

        # 渠道选择
        row_provider = QHBoxLayout()
        row_provider.addWidget(QLabel("AI渠道："))
        self.cmb_provider = QComboBox()
        for key, (display, _url, _model) in AI_PROVIDERS.items():
            self.cmb_provider.addItem(display, key)
        self.cmb_provider.currentIndexChanged.connect(self._on_provider_changed)
        row_provider.addWidget(self.cmb_provider, 1)
        layout.addLayout(row_provider)

        # 接口地址
        layout.addWidget(QLabel("AI接口地址："))
        self.edt_api_url = QLineEdit()
        self.edt_api_url.setPlaceholderText("https://api.example.com/v1/chat/completions")
        layout.addWidget(self.edt_api_url)

        # API Key
        row_key = QHBoxLayout()
        row_key.addWidget(QLabel("AI密钥(Key)："))
        self.btn_show_key = QPushButton("显示")
        self.btn_show_key.setFixedWidth(60)
        self.btn_show_key.clicked.connect(self._toggle_key_visible)
        row_key.addStretch()
        row_key.addWidget(self.btn_show_key)
        layout.addLayout(row_key)
        self.edt_api_key = QLineEdit()
        self.edt_api_key.setEchoMode(QLineEdit.Password)
        self.edt_api_key.setPlaceholderText("输入API密钥...")
        layout.addWidget(self.edt_api_key)

        # 模型名称
        layout.addWidget(QLabel("模型名称："))
        self.edt_model = QLineEdit()
        self.edt_model.setPlaceholderText("如: gpt-3.5-turbo, qwen-plus 等")
        layout.addWidget(self.edt_model)

        # 保存 + 测试按钮
        row_btn = QHBoxLayout()
        self.btn_save_ai = QPushButton("保存AI配置")
        self.btn_save_ai.clicked.connect(self._save_ai)
        self.btn_test_ai = QPushButton("测试连通性")
        self.btn_test_ai.clicked.connect(self._test_ai_connection)
        row_btn.addWidget(self.btn_save_ai)
        row_btn.addWidget(self.btn_test_ai)
        layout.addLayout(row_btn)

        # 测试结果展示
        self.lbl_test_result = QLabel("尚未测试连通性")
        self.lbl_test_result.setWordWrap(True)
        self.lbl_test_result.setStyleSheet("color: #999; font-size: 12px; padding: 4px;")
        layout.addWidget(self.lbl_test_result)

        return grp

    def _on_provider_changed(self, index):
        """切换渠道时自动填充 URL 和模型名（仅当用户未手动修改或字段为空时）"""
        key = self.cmb_provider.itemData(index)
        if key not in AI_PROVIDERS:
            return
        _display, url, model = AI_PROVIDERS[key]
        # 当 URL 为空或等于某个预设值时自动填充
        current_url = self.edt_api_url.text().strip()
        preset_urls = {v[1] for v in AI_PROVIDERS.values()}
        if not current_url or current_url in preset_urls:
            self.edt_api_url.setText(url)
        # 模型名同理
        current_model = self.edt_model.text().strip()
        preset_models = {v[2] for v in AI_PROVIDERS.values()}
        if not current_model or current_model in preset_models:
            self.edt_model.setText(model)
        # 联动填充图片生成API地址
        if key in IMAGE_GEN_PRESETS:
            gen_url, gen_model = IMAGE_GEN_PRESETS[key]
            cur_gen_url = self.edt_gen_url.text().strip()
            preset_gen_urls = {v[0] for v in IMAGE_GEN_PRESETS.values()}
            if gen_url and (not cur_gen_url or cur_gen_url in preset_gen_urls):
                self.edt_gen_url.setText(gen_url)
            cur_gen_model = self.edt_gen_model.text().strip()
            preset_gen_models = {v[1] for v in IMAGE_GEN_PRESETS.values()}
            if gen_model and (not cur_gen_model or cur_gen_model in preset_gen_models):
                self.edt_gen_model.setText(gen_model)

    def _toggle_key_visible(self):
        if self.edt_api_key.echoMode() == QLineEdit.Password:
            self.edt_api_key.setEchoMode(QLineEdit.Normal)
            self.btn_show_key.setText("隐藏")
        else:
            self.edt_api_key.setEchoMode(QLineEdit.Password)
            self.btn_show_key.setText("显示")

    def _test_ai_connection(self):
        """测试 AI 接口连通性"""
        url = self.edt_api_url.text().strip()
        key = self.edt_api_key.text().strip()
        model = self.edt_model.text().strip()
        if not url or not key or not model:
            self._toast.show_msg("请先填写完整的AI配置信息")
            return

        self.btn_test_ai.setEnabled(False)
        self.btn_test_ai.setText("正在测试...")

        provider = self.cmb_provider.itemData(self.cmb_provider.currentIndex())
        self._test_thread = AITestThread(url, key, model, provider)
        self._test_thread.success_signal.connect(self._on_test_success)
        self._test_thread.error_signal.connect(self._on_test_error)
        self._test_thread.start()

    def _on_test_success(self, msg):
        self.btn_test_ai.setEnabled(True)
        self.btn_test_ai.setText("测试连通性")
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_test_result.setStyleSheet("color: #2e8b57; font-size: 12px; padding: 4px;")
        self.lbl_test_result.setText(f"✓ {now} {msg}")

    def _on_test_error(self, err):
        self.btn_test_ai.setEnabled(True)
        self.btn_test_ai.setText("测试连通性")
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_test_result.setStyleSheet("color: #c0392b; font-size: 12px; padding: 4px;")
        self.lbl_test_result.setText(f"✗ {now} {err}")

    def _on_ai_toggle(self, checked):
        enabled = checked
        self.cmb_provider.setEnabled(enabled)
        self.edt_api_url.setEnabled(enabled)
        self.edt_api_key.setEnabled(enabled)
        self.edt_model.setEnabled(enabled)
        self.btn_save_ai.setEnabled(enabled)
        self.btn_test_ai.setEnabled(enabled)
        if enabled:
            self.chk_ai_enabled.setText("AI能力总开关：已开启")
        else:
            self.chk_ai_enabled.setText("AI能力总开关：已关闭")
        self._update_ai_todo_button()

    def _save_ai(self):
        if self.chk_ai_enabled.isChecked():
            url = self.edt_api_url.text().strip()
            key = self.edt_api_key.text().strip()
            model = self.edt_model.text().strip()
            if not url or not key or not model:
                self._toast.show_msg("请完善AI接口配置信息")
                return
        self.config["ai"]["enabled"] = self.chk_ai_enabled.isChecked()
        self.config["ai"]["provider"] = self.cmb_provider.itemData(self.cmb_provider.currentIndex())
        self.config["ai"]["api_url"] = self.edt_api_url.text().strip()
        self.config["ai"]["api_key"] = self.edt_api_key.text().strip()
        self.config["ai"]["model"] = self.edt_model.text().strip()
        save_config(self.config)
        self._update_ai_todo_button()
        if self.on_config_changed:
            self.on_config_changed()
        self._toast.show_msg("AI配置保存成功")

    # ---------- 模块四：角色设定与外观更新 ----------
    def _build_module4(self):
        grp = QGroupBox("功能四：角色设定与外观更新")
        layout = QVBoxLayout(grp)

        # 模式选择
        row_mode = QHBoxLayout()
        self.rb_ai_gen = QRadioButton("AI生成设定图")
        self.rb_upload_only = QRadioButton("上传设定图切片")
        self._sheet_mode_group = QButtonGroup(self)
        self._sheet_mode_group.addButton(self.rb_ai_gen)
        self._sheet_mode_group.addButton(self.rb_upload_only)
        self.rb_upload_only.setChecked(True)
        self.rb_ai_gen.toggled.connect(self._on_sheet_mode_changed)
        row_mode.addWidget(self.rb_ai_gen)
        row_mode.addWidget(self.rb_upload_only)
        row_mode.addStretch()
        layout.addLayout(row_mode)

        # --- 模式A：AI生成设定图 ---
        self._ai_gen_container = QFrame()
        ai_gen_layout = QVBoxLayout(self._ai_gen_container)
        ai_gen_layout.setContentsMargins(0, 0, 0, 0)

        # 参考图选择
        row_ref = QHBoxLayout()
        self.btn_select_ref = QPushButton("选择参考图片")
        self.btn_select_ref.clicked.connect(self._select_reference_image)
        self.lbl_ref_image = QLabel("未选择参考图")
        self.lbl_ref_image.setStyleSheet("color: #999;")
        row_ref.addWidget(self.btn_select_ref)
        row_ref.addWidget(self.lbl_ref_image, 1)
        ai_gen_layout.addLayout(row_ref)

        # 图片生成API地址
        ai_gen_layout.addWidget(QLabel("图片生成API地址："))
        self.edt_gen_url = QLineEdit()
        self.edt_gen_url.setPlaceholderText("https://api.openai.com/v1/images/generations")
        ai_gen_layout.addWidget(self.edt_gen_url)

        # 图片生成模型
        ai_gen_layout.addWidget(QLabel("图片生成模型："))
        self.edt_gen_model = QLineEdit()
        self.edt_gen_model.setPlaceholderText("如: dall-e-3, Kwai-Kolors/Kolors 等")
        ai_gen_layout.addWidget(self.edt_gen_model)

        # 生成按钮
        self.btn_generate = QPushButton("生成角色设定图")
        self.btn_generate.clicked.connect(self._generate_character_sheet)
        ai_gen_layout.addWidget(self.btn_generate)

        layout.addWidget(self._ai_gen_container)

        # --- 模式B：上传设定图 ---
        self._upload_container = QFrame()
        upload_layout = QVBoxLayout(self._upload_container)
        upload_layout.setContentsMargins(0, 0, 0, 0)

        row_sheet = QHBoxLayout()
        self.btn_select_sheet = QPushButton("选择角色设定图")
        self.btn_select_sheet.clicked.connect(self._select_sheet_image)
        self.lbl_sheet_image = QLabel("未选择设定图")
        self.lbl_sheet_image.setStyleSheet("color: #999;")
        row_sheet.addWidget(self.btn_select_sheet)
        row_sheet.addWidget(self.lbl_sheet_image, 1)
        upload_layout.addLayout(row_sheet)

        layout.addWidget(self._upload_container)

        # 设定图预览
        self.lbl_sheet_preview = QLabel()
        self.lbl_sheet_preview.setAlignment(Qt.AlignCenter)
        self.lbl_sheet_preview.setMinimumHeight(100)
        self.lbl_sheet_preview.setStyleSheet("border: 1px dashed #ccc; border-radius: 4px; color: #999;")
        self.lbl_sheet_preview.setText("设定图预览（生成或上传后显示）")
        layout.addWidget(self.lbl_sheet_preview)

        # 切片按钮
        self.btn_slice = QPushButton("切片并更新桌宠外观")
        self.btn_slice.clicked.connect(self._slice_and_update)
        self.btn_slice.setEnabled(False)
        layout.addWidget(self.btn_slice)

        # 状态标签
        self.lbl_sprite_result = QLabel("尚未更新外观")
        self.lbl_sprite_result.setWordWrap(True)
        self.lbl_sprite_result.setStyleSheet("color: #999; font-size: 12px; padding: 4px;")
        layout.addWidget(self.lbl_sprite_result)

        return grp

    def _on_sheet_mode_changed(self):
        """切换模式时显示/隐藏对应区域"""
        if self.rb_ai_gen.isChecked():
            self._ai_gen_container.show()
            self._upload_container.hide()
        else:
            self._ai_gen_container.hide()
            self._upload_container.show()

    def _select_reference_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择参考图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self.config["character_sheet"]["reference_image"] = path
            self.lbl_ref_image.setText(os.path.basename(path))
            self.lbl_ref_image.setStyleSheet("color: #555;")
            save_config(self.config)

    def _select_sheet_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择角色设定图", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self._current_sheet_path = path
            self.config["character_sheet"]["sheet_image"] = path
            self.lbl_sheet_image.setText(os.path.basename(path))
            self.lbl_sheet_image.setStyleSheet("color: #555;")
            save_config(self.config)
            self._show_sheet_preview(path)
            self.btn_slice.setEnabled(True)

    def _show_sheet_preview(self, path):
        """显示设定图缩略预览"""
        pm = QPixmap(path)
        if not pm.isNull():
            scaled = pm.scaled(400, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_sheet_preview.setPixmap(scaled)
            self.lbl_sheet_preview.setStyleSheet("")

    def _generate_character_sheet(self):
        """模式A：AI生成设定图（视觉分析 + 图片生成）"""
        ref_path = self.config["character_sheet"].get("reference_image", "")
        if not ref_path or not os.path.isfile(ref_path):
            self._toast.show_msg("请先选择参考图片")
            return

        gen_url = self.edt_gen_url.text().strip()
        gen_model = self.edt_gen_model.text().strip()
        if not gen_url or not gen_model:
            self._toast.show_msg("请填写图片生成API地址和模型名")
            return

        api_key = self.edt_api_key.text().strip()
        if not api_key:
            self._toast.show_msg("请先在模块三配置API密钥")
            return

        chat_url = self.edt_api_url.text().strip()
        chat_model = self.edt_model.text().strip()
        if not chat_url or not chat_model:
            self._toast.show_msg("请先在模块三配置视觉模型（如gpt-4o）")
            return

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("正在AI分析参考图...")
        self.lbl_sprite_result.setStyleSheet("color: #555; font-size: 12px; padding: 4px;")
        self.lbl_sprite_result.setText("步骤1/2：AI视觉分析参考图中...")

        # 步骤1：视觉分析
        self._analysis_thread = ImageAnalysisThread(ref_path, chat_url, api_key, chat_model)
        self._analysis_thread.finished_signal.connect(self._on_analysis_finished)
        self._analysis_thread.error_signal.connect(self._on_analysis_error)
        self._analysis_thread.start()

    def _on_analysis_finished(self, description):
        """视觉分析完成，进入步骤2：图片生成"""
        _log(f"视觉分析完成，开始图片生成")
        self.btn_generate.setText("正在生成设定图...")
        self.lbl_sprite_result.setText("步骤2/2：AI生成角色设定图中...")

        gen_url = self.edt_gen_url.text().strip()
        gen_model = self.edt_gen_model.text().strip()
        api_key = self.edt_api_key.text().strip()

        # 用分析结果作为图片生成的prompt
        prompt = description + "\n\n请严格按照以下布局生成：第1行6个全身站姿从左到右排列，第2行6个动作姿态，第3行8个表情头像。背景使用纯色。"

        self._gen_thread = ImageGenThread(prompt, gen_url, api_key, gen_model)
        self._gen_thread.finished_signal.connect(self._on_gen_finished)
        self._gen_thread.error_signal.connect(self._on_gen_error)
        self._gen_thread.start()

    def _on_analysis_error(self, err):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("生成角色设定图")
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_sprite_result.setStyleSheet("color: #c0392b; font-size: 12px; padding: 4px;")
        self.lbl_sprite_result.setText(f"✗ {now} {err}")

    def _on_gen_finished(self, image_path):
        """图片生成完成，显示预览"""
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("生成角色设定图")
        self._current_sheet_path = image_path
        self.config["character_sheet"]["sheet_image"] = image_path
        save_config(self.config)
        self._show_sheet_preview(image_path)
        self.btn_slice.setEnabled(True)
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_sprite_result.setStyleSheet("color: #2e8b57; font-size: 12px; padding: 4px;")
        self.lbl_sprite_result.setText(f"✓ {now} 设定图生成成功，可点击下方切片")

    def _on_gen_error(self, err):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("生成角色设定图")
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_sprite_result.setStyleSheet("color: #c0392b; font-size: 12px; padding: 4px;")
        self.lbl_sprite_result.setText(f"✗ {now} {err}")

    def _slice_and_update(self):
        """切片设定图并更新桌宠外观"""
        if not self._current_sheet_path or not os.path.isfile(self._current_sheet_path):
            self._toast.show_msg("请先生成或上传设定图")
            return

        sprites_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sprites")
        # 兼容打包后的路径
        import sys as _sys
        if hasattr(_sys, '_MEIPASS'):
            sprites_dir = os.path.join(_sys._MEIPASS, "sprites")

        self.btn_slice.setEnabled(False)
        self.btn_slice.setText("正在切片...")
        self.lbl_sprite_result.setStyleSheet("color: #555; font-size: 12px; padding: 4px;")
        self.lbl_sprite_result.setText("正在检测角色区域并切片...")

        self._slice_thread = SpriteSliceThread(self._current_sheet_path, sprites_dir)
        self._slice_thread.finished_signal.connect(self._on_slice_finished)
        self._slice_thread.error_signal.connect(self._on_slice_error)
        self._slice_thread.start()

    def _on_slice_finished(self, results):
        self.btn_slice.setEnabled(True)
        self.btn_slice.setText("切片并更新桌宠外观")
        now = datetime.now().strftime("%H:%M:%S")
        names = [r[0] for r in results]
        self.lbl_sprite_result.setStyleSheet("color: #2e8b57; font-size: 12px; padding: 4px;")
        self.lbl_sprite_result.setText(f"✓ {now} 成功切出 {len(results)} 个精灵: {', '.join(names)}")
        # 通知桌宠重载精灵
        if self.on_sprites_updated:
            self.on_sprites_updated()

    def _on_slice_error(self, err):
        self.btn_slice.setEnabled(True)
        self.btn_slice.setText("切片并更新桌宠外观")
        now = datetime.now().strftime("%H:%M:%S")
        self.lbl_sprite_result.setStyleSheet("color: #c0392b; font-size: 12px; padding: 4px;")
        self.lbl_sprite_result.setText(f"✗ {now} {err}")

    # ---------- 配置加载 ----------
    def _load_config_to_ui(self):
        kb = self.config["knowledge_base"]
        if kb["folder_path"]:
            self.lbl_folder.setText(kb["folder_path"])
            self.lbl_folder.setStyleSheet("color: #555;")
        self.txt_todo.setPlainText(kb["todos"])

        phrase = self.config["phrase"]
        if phrase["mode"] == "todo":
            self.rb_todo.setChecked(True)
        else:
            self.rb_custom.setChecked(True)
        self.txt_phrase.setPlainText(phrase["custom_text"])

        ai = self.config["ai"]
        self.chk_ai_enabled.setChecked(ai["enabled"])
        # 加载渠道
        provider = ai.get("provider", "openai_compatible")
        for i in range(self.cmb_provider.count()):
            if self.cmb_provider.itemData(i) == provider:
                self.cmb_provider.setCurrentIndex(i)
                break
        self.edt_api_url.setText(ai["api_url"])
        self.edt_api_key.setText(ai["api_key"])
        self.edt_model.setText(ai["model"])
        self._on_ai_toggle(ai["enabled"])

        # 模块四：角色设定
        cs = self.config.get("character_sheet", {})
        if cs.get("mode") == "ai_gen":
            self.rb_ai_gen.setChecked(True)
        else:
            self.rb_upload_only.setChecked(True)
        if cs.get("reference_image"):
            self.lbl_ref_image.setText(os.path.basename(cs["reference_image"]))
            self.lbl_ref_image.setStyleSheet("color: #555;")
        self.edt_gen_url.setText(cs.get("image_gen_url", ""))
        self.edt_gen_model.setText(cs.get("image_gen_model", ""))
        if cs.get("sheet_image") and os.path.isfile(cs["sheet_image"]):
            self._current_sheet_path = cs["sheet_image"]
            self.lbl_sheet_image.setText(os.path.basename(cs["sheet_image"]))
            self.lbl_sheet_image.setStyleSheet("color: #555;")
            self._show_sheet_preview(cs["sheet_image"])
            self.btn_slice.setEnabled(True)
        self._on_sheet_mode_changed()

    def _update_ai_todo_button(self):
        # 检查 UI 实时状态，而非 config（config 可能尚未保存）
        if not self.chk_ai_enabled.isChecked():
            self.btn_ai_todo.setEnabled(False)
            self.btn_ai_todo.setToolTip("AI能力已关闭，请开启后使用")
        elif not self.config["knowledge_base"]["folder_path"]:
            self.btn_ai_todo.setEnabled(False)
            self.btn_ai_todo.setToolTip("请先选择知识库文件夹")
        else:
            self.btn_ai_todo.setEnabled(True)
            self.btn_ai_todo.setToolTip("")

    def closeEvent(self, event):
        if self._ai_thread and self._ai_thread.isRunning():
            self._ai_thread.quit()
            self._ai_thread.wait(3000)
        if self._test_thread and self._test_thread.isRunning():
            self._test_thread.quit()
            self._test_thread.wait(3000)
        if self._analysis_thread and self._analysis_thread.isRunning():
            self._analysis_thread.quit()
            self._analysis_thread.wait(3000)
        if self._gen_thread and self._gen_thread.isRunning():
            self._gen_thread.quit()
            self._gen_thread.wait(5000)
        if self._slice_thread and self._slice_thread.isRunning():
            self._slice_thread.quit()
            self._slice_thread.wait(5000)
        event.accept()
