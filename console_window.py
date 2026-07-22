# -*- coding: utf-8 -*-
"""
控制台窗口：三大功能模块
1. 知识库&本周待办梳理
2. 桌宠点击话术自定义
3. AI大模型接入配置
"""
import os
import sys
import json
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
from PyQt5.QtGui import QFont
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


class ConsoleWindow(QMainWindow):
    """控制台主窗口"""

    def __init__(self, config, on_config_changed=None):
        super().__init__()
        self.config = config
        self.on_config_changed = on_config_changed
        self._ai_thread = None
        self._test_thread = None

        self.setWindowTitle("桌面宠物 - 控制台")
        self.setMinimumSize(560, 720)
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
        event.accept()
