# -*- coding: utf-8 -*-
"""
桌面宠物程序
- 透明无边框置顶窗口
- 多精灵素材：6种站姿 / 6种动作 / 8种表情
- 左键拖动 / 点击触发互动(跳跃、压扁回弹、左右抖动)
- 互动时切换动作精灵 + 随机表情 + 中文气泡
- 闲置时自动切换站姿
- 右键菜单：调整大小、置顶开关、退出
- 滚轮缩放
- 系统托盘图标
"""
import sys
import os
import random
import traceback

# windowed 模式下重定向 stdout/stderr 到日志文件，避免因输出异常导致静默崩溃
try:
    _log = open(os.path.join(os.path.expanduser("~"), "DesktopPet_run.log"), "w", encoding="utf-8")
    sys.stdout = _log
    sys.stderr = _log
except Exception:
    pass

from PyQt5.QtWidgets import (QApplication, QWidget, QMenu, QSystemTrayIcon)
from PyQt5.QtCore import (Qt, QTimer, QRectF, QVariantAnimation,
                          QEasingCurve, QRect)
from PyQt5.QtGui import (QPixmap, QPainter, QColor, QFont, QPen, QBrush,
                         QPainterPath, QFontMetrics, QIcon)

from config_manager import load_config, save_config
from console_window import ConsoleWindow

# 确保 Qt 能找到平台插件（PyInstaller windowed 模式必需）
if hasattr(sys, '_MEIPASS'):
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(
        sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')


def resource_path(relative):
    """获取资源路径，兼容 PyInstaller 打包后的 _MEIPASS"""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def load_sprite(name):
    """加载 sprites 目录下的精灵图"""
    path = resource_path(os.path.join("sprites", f"{name}.png"))
    pm = QPixmap(path)
    return pm


# 互动时随机显示的中文短句
PHRASES = [
    "今天也要元气满满哦！",
    "别戳我啦，会痒的~",
    "想去爬山吗？",
    "嘿嘿，你好呀！",
    "我又不是玩具…",
    "再戳我就生气了！",
    "陪我聊聊天呗~",
    "世界那么大，想去看看！",
    "哼，才不理你呢。",
    "今天天气真不错呀~",
    "要不要一起去旅行？",
    "我可是专业的探险家！",
    "咦，你发现我了？",
    "嘘…让我再眯一会儿。",
    "你的鼠标手感不错嘛！",
    "咔哒咔哒，好有趣~",
    "别拉我，我晕车！",
    "咕噜噜…肚子饿了。",
    "我在思考人生…",
    "戳我之交，胜过点赞！",
    "哇哦，飞起来啦！",
    "我扁了，但没完全扁！",
    "摇摇晃晃，我醉了吗？",
    "探险家从不认输！",
]

# 不同互动类型对应的短语
INTERACTION_PHRASES = {
    "jump": ["哇哦，飞起来啦！", "世界那么大，想去看看！", "想去爬山吗？", "探险家从不认输！"],
    "squash": ["我扁了，但没完全扁！", "别戳我啦，会痒的~", "再戳我就生气了！", "咕噜噜…肚子饿了。"],
    "shake": ["摇摇晃晃，我醉了吗？", "别拉我，我晕车！", "嘿嘿，你好呀！", "我在思考人生…"],
    "idle": ["今天也要元气满满哦！", "今天天气真不错呀~", "嘘…让我再眯一会儿。", "陪我聊聊天呗~"],
}


class BubbleWidget(QWidget):
    """对话气泡：不透明白色圆角背景 + 下方小尾巴 + 可选表情图，支持悬浮暂停"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_Hover)
        self.text = ""
        self.face_pixmap = None
        self.font = QFont("Microsoft YaHei", 10, QFont.Bold)
        self.pad_x = 16
        self.pad_y = 10
        self.tail_h = 10
        self.face_size = 32
        self.max_width = 360
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)
        self._duration = 3000

    def enterEvent(self, event):
        """鼠标悬浮时暂停自动消失"""
        self.timer.stop()

    def leaveEvent(self, event):
        """鼠标离开时恢复计时"""
        self.timer.start(self._duration)

    def set_content(self, text, face_pixmap=None):
        self.text = text
        self.face_pixmap = face_pixmap
        fm = QFontMetrics(self.font)
        face_w = self.face_size + 8 if face_pixmap else 0
        # 可用文本宽度（减去内边距和表情图）
        avail_w = self.max_width - self.pad_x * 2 - 6 - face_w
        if avail_w < 80:
            avail_w = 80
        # 用 boundingRect 计算自动换行后的实际尺寸
        text_flags = Qt.TextWordWrap
        br = fm.boundingRect(0, 0, avail_w, 9999, text_flags, text)
        tw = br.width()
        th = br.height()
        w = tw + self.pad_x * 2 + 6 + face_w
        h = max(th, self.face_size if face_pixmap else th) + self.pad_y * 2
        self.resize(w, h + self.tail_h)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self.font)
        w = self.width()
        body_h = self.height() - self.tail_h
        rect = QRect(2, 2, w - 4, body_h - 4)

        # 气泡主体
        p.setPen(QPen(QColor(120, 120, 120), 1.4))
        p.setBrush(QBrush(QColor(255, 255, 255, 250)))
        p.drawRoundedRect(rect, 14, 14)

        # 尾巴
        tail_w = 16
        half_tail = tail_w // 2
        cx = w // 2
        path = QPainterPath()
        path.moveTo(cx - half_tail, body_h - 2)
        path.lineTo(cx + half_tail, body_h - 2)
        path.lineTo(cx, body_h + self.tail_h - 1)
        path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 250)))
        p.drawPath(path)
        p.setPen(QPen(QColor(120, 120, 120), 1.4))
        p.drawLine(cx - half_tail, body_h - 2, cx, body_h + self.tail_h - 1)
        p.drawLine(cx + half_tail, body_h - 2, cx, body_h + self.tail_h - 1)

        # 表情图（左侧）
        text_x_offset = 0
        if self.face_pixmap and not self.face_pixmap.isNull():
            fy = (body_h - self.face_size) // 2
            p.drawPixmap(QRect(self.pad_x, fy, self.face_size, self.face_size),
                         self.face_pixmap)
            text_x_offset = self.face_size + 8

        # 文字（支持多行自动换行）
        text_rect = QRect(rect.x() + text_x_offset + self.pad_x, rect.y(),
                          rect.width() - text_x_offset - self.pad_x * 2, rect.height())
        p.setPen(QColor(55, 55, 55))
        p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, self.text)

    def show_phrase(self, text, face_pixmap=None, duration=3000):
        self.set_content(text, face_pixmap)
        self.show()
        self.raise_()
        self._duration = duration
        self.timer.start(duration)


class DesktopPet(QWidget):
    # 精灵类型
    POSE_NAMES = ["pose1", "pose2", "pose3", "pose4", "pose5", "pose6"]
    ACTION_NAMES = ["action1", "action2", "action3", "action4", "action5", "action6"]
    FACE_NAMES = ["face1", "face2", "face3", "face4", "face5", "face6", "face7", "face8"]

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # 加载所有精灵
        self.poses = [load_sprite(n) for n in self.POSE_NAMES]
        self.actions = [load_sprite(n) for n in self.ACTION_NAMES]
        self.faces = [load_sprite(n) for n in self.FACE_NAMES]

        # 过滤无效精灵
        self.poses = [pm for pm in self.poses if not pm.isNull()]
        self.actions = [pm for pm in self.actions if not pm.isNull()]
        self.faces = [pm for pm in self.faces if not pm.isNull()]

        if not self.poses:
            raise FileNotFoundError("无法加载任何站姿精灵图，请检查 sprites/ 目录")

        # 当前显示的精灵
        self.pose_index = 0
        self.current_pixmap = self.poses[0]

        # 动画状态
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.current_anim = None

        # 尺寸管理
        self.target_height = 220
        self.always_on_top = True

        # 互动循环
        self.interaction_index = 0
        self.interactions = [self.play_jump, self.play_squash, self.play_shake]

        # 拖动状态
        self._press_pos = None
        self._drag_offset = None
        self._dragging = False
        self._drag_threshold = 5

        # 气泡
        self.bubble = BubbleWidget()

        # 配置
        self.config = load_config()

        # 系统托盘
        self._tray = None
        self._closing = False
        self._console = None  # 控制台窗口引用

        self._update_window_size()
        self._set_initial_position()

    # ---------- 精灵管理 ----------
    def _switch_pose(self, index):
        """切换站姿精灵"""
        if self.poses:
            self.pose_index = index % len(self.poses)
            self.current_pixmap = self.poses[self.pose_index]
            self.update()

    def _random_pose(self):
        """随机切换到一个不同的站姿"""
        if len(self.poses) > 1:
            new_idx = random.randint(0, len(self.poses) - 1)
            if new_idx == self.pose_index:
                new_idx = (new_idx + 1) % len(self.poses)
            self._switch_pose(new_idx)

    # ---------- 尺寸 / 位置 ----------
    def _update_window_size(self):
        pm = self.current_pixmap
        aspect = pm.width() / pm.height()
        self.char_w = int(self.target_height * aspect)
        self.char_h = int(self.target_height)
        self.pad_x = max(28, int(self.char_w * 0.20))
        self.pad_top = int(self.char_h * 0.45) + 20  # 跳跃余量
        self.win_w = self.char_w + self.pad_x * 2
        self.win_h = self.char_h + self.pad_top
        self.setFixedSize(self.win_w, self.win_h)
        self.update()

    def _set_initial_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.win_w - 40
        y = screen.height() - self.win_h - 20
        self.move(x, y)

    # ---------- 绘制 ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        pm = self.current_pixmap

        pw = self.char_w * self.scale_x
        ph = self.char_h * self.scale_y
        bottom_y = self.win_h - 2
        left_x = (self.win_w - pw) / 2.0 + self.offset_x
        top_y = bottom_y - ph + self.offset_y
        p.drawPixmap(QRectF(left_x, top_y, pw, ph), pm,
                     QRectF(0, 0, pm.width(), pm.height()))

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPos()
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._dragging = False

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._press_pos is not None:
            if (event.globalPos() - self._press_pos).manhattanLength() > self._drag_threshold:
                self._dragging = True
                self.move(event.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._dragging:
                self.trigger_interaction()
            self._press_pos = None
            self._dragging = False

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 18 if delta > 0 else -18
        new_h = max(90, min(620, self.target_height + step))
        if new_h != self.target_height:
            self.target_height = new_h
            self._update_window_size()

    def closeEvent(self, event):
        """关闭窗口时隐藏到系统托盘，而不是退出程序"""
        if not self._closing:
            self.hide()
            event.ignore()
        else:
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#ffffff;border:1px solid #bbb;border-radius:8px;"
            "padding:6px;color:#333;font-family:'Microsoft YaHei';font-size:13px;}"
            "QMenu::item{padding:6px 26px;border-radius:5px;}"
            "QMenu::item:selected{background:#4a90d9;color:white;}"
            "QMenu::separator{height:1px;background:#ddd;margin:4px 8px;}"
        )

        console_act = menu.addAction("打开控制台")
        console_act.triggered.connect(self.open_console)

        size_menu = menu.addMenu("调整大小")
        for label, h in [("小  120", 120), ("中  220", 220),
                         ("大  320", 320), ("超大 450", 450)]:
            act = size_menu.addAction(label)
            act.triggered.connect(lambda _=False, h=h: self._set_size(h))

        top_label = "置顶：开 ✓" if self.always_on_top else "置顶：关"
        top_act = menu.addAction(top_label)
        top_act.triggered.connect(self.toggle_top)

        menu.addSeparator()
        exit_act = menu.addAction("退出程序")
        exit_act.triggered.connect(self._quit)
        menu.exec_(event.globalPos())

    # ---------- 菜单动作 ----------
    def _set_size(self, h):
        self.target_height = h
        self._update_window_size()

    def toggle_top(self):
        self.always_on_top = not self.always_on_top
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()
        # 同步气泡窗口置顶状态
        bubble_flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool if self.always_on_top else Qt.FramelessWindowHint | Qt.Tool
        self.bubble.setWindowFlags(bubble_flags)
        self.bubble.setAttribute(Qt.WA_TranslucentBackground)
        self.bubble.setAttribute(Qt.WA_ShowWithoutActivating)
        self.bubble.setAttribute(Qt.WA_Hover)

    def open_console(self):
        """打开控制台窗口"""
        if self._console is None:
            self._console = ConsoleWindow(self.config, self._on_config_changed)
        self._console.show()
        self._console.raise_()
        self._console.activateWindow()

    def _on_config_changed(self):
        """控制台配置变更回调，重新加载配置"""
        self.config = load_config()

    def _quit(self):
        self._closing = True
        self.bubble.close()
        if self._console is not None:
            self._console.close()
        if self._tray is not None:
            self._tray.hide()
        QApplication.quit()

    # ---------- 互动 ----------
    def trigger_interaction(self):
        if self.current_anim is not None:
            return
        action = self.interactions[self.interaction_index % len(self.interactions)]
        self.interaction_index += 1
        action()
        # 始终显示气泡（PRD：点击桌宠弹出已配置话术）
        self.show_bubble()

    def _get_phrase_text(self):
        """根据配置获取话术文本"""
        phrase = self.config.get("phrase", {})
        mode = phrase.get("mode", "custom")
        if mode == "todo":
            todos = self.config.get("knowledge_base", {}).get("todos", "")
            if todos:
                return todos
            return "暂无本周待办内容，请先梳理知识库"
        else:
            custom = phrase.get("custom_text", "")
            if custom:
                return custom
            # 无自定义内容时使用随机默认话术
            interaction_type = ["jump", "squash", "shake"][
                (self.interaction_index - 1) % 3]
            return random.choice(INTERACTION_PHRASES.get(interaction_type, PHRASES))

    def _run_anim(self, keyframes, duration, sprite_switches=None):
        """以进度 0->1 驱动，自行对各通道做线性插值。
        keyframes: [(t, {channel: value}), ...]
        sprite_switches: 可选，[(t, pixmap), ...] 在指定时间点切换精灵图"""
        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Linear)
        channels = list(keyframes[0][1].keys())
        chan_keys = {ch: [(kf[0], kf[1][ch]) for kf in keyframes] for ch in channels}
        # 记录原始精灵，动画结束后恢复
        original_pixmap = self.current_pixmap

        def on_value(progress):
            for ch in channels:
                setattr(self, ch, self._interp(chan_keys[ch], progress))
            # 切换精灵
            if sprite_switches:
                for t_switch, pm in sprite_switches:
                    if progress >= t_switch:
                        self.current_pixmap = pm
            self.update()

        def on_finished():
            self._finish_anim()
            self.current_pixmap = original_pixmap
            self.update()

        anim.valueChanged.connect(on_value)
        anim.finished.connect(on_finished)
        anim.start()
        self.current_anim = anim

    @staticmethod
    def _interp(keys, t):
        if t <= keys[0][0]:
            return keys[0][1]
        if t >= keys[-1][0]:
            return keys[-1][1]
        for i in range(len(keys) - 1):
            t0, v0 = keys[i]
            t1, v1 = keys[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return v1
                f = (t - t0) / (t1 - t0)
                return v0 + (v1 - v0) * f
        return keys[-1][1]

    def _finish_anim(self):
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.update()
        self.current_anim = None

    # 跳跃：抛物线 + 切换动作精灵
    def play_jump(self):
        jh = self.char_h * 0.40
        steps = 10
        keys = []
        for i in range(steps + 1):
            t = i / steps
            y = -4.0 * jh * t * (1.0 - t)  # 抛物线，峰在 t=0.5
            keys.append((t, {"offset_y": y}))
        keys.append((1.0, {"offset_y": 0.0}))

        # 跳跃过程中切换动作精灵
        sprite_switches = []
        if self.actions:
            n = len(self.actions)
            for i in range(n):
                sprite_switches.append((i / n, self.actions[i % n]))

        self._run_anim(keys, 620, sprite_switches)

    # 压扁回弹
    def play_squash(self):
        keys = [
            (0.00, {"scale_x": 1.00, "scale_y": 1.00}),
            (0.20, {"scale_x": 1.18, "scale_y": 0.66}),
            (0.45, {"scale_x": 0.93, "scale_y": 1.14}),
            (0.70, {"scale_x": 1.04, "scale_y": 0.97}),
            (1.00, {"scale_x": 1.00, "scale_y": 1.00}),
        ]
        # 压扁时切换到第2个动作精灵（如果有）
        sprite_switches = []
        if len(self.actions) > 1:
            sprite_switches.append((0.0, self.actions[1]))
        self._run_anim(keys, 620, sprite_switches)

    # 左右抖动：阻尼振荡
    def play_shake(self):
        amp = self.char_w * 0.08
        keys = [
            (0.00, {"offset_x": 0.0}),
            (0.12, {"offset_x": -amp * 1.0}),
            (0.24, {"offset_x": amp * 0.85}),
            (0.36, {"offset_x": -amp * 0.65}),
            (0.48, {"offset_x": amp * 0.45}),
            (0.62, {"offset_x": -amp * 0.28}),
            (0.76, {"offset_x": amp * 0.15}),
            (0.88, {"offset_x": -amp * 0.06}),
            (1.00, {"offset_x": 0.0}),
        ]
        # 抖动时切换到第3个动作精灵（如果有）
        sprite_switches = []
        if len(self.actions) > 2:
            sprite_switches.append((0.0, self.actions[2]))
        self._run_anim(keys, 620, sprite_switches)

    # ---------- 气泡 ----------
    def show_bubble(self, text=None, face=None):
        if text is None:
            text = self._get_phrase_text()
        if face is None and self.faces:
            face = random.choice(self.faces)
        self.bubble.set_content(text, face)
        bx = self.x() + (self.win_w - self.bubble.width()) // 2
        by = self.y() - self.bubble.height() - 4
        screen = QApplication.primaryScreen().availableGeometry()
        bx = max(screen.x() + 4, min(bx, screen.right() - self.bubble.width() - 4))
        by = max(screen.y() + 4, by)
        self.bubble.move(bx, by)
        self.bubble.show_phrase(text, face, 3000)


def main():
    # 全局异常捕获，写入日志文件
    def _excepthook(exc_type, exc_value, exc_tb):
        log_path = os.path.join(os.path.expanduser("~"), "DesktopPet_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    pet = DesktopPet()
    pet.show()

    # 创建系统托盘图标
    tray_icon = QSystemTrayIcon()
    # 使用第一个站姿精灵作为托盘图标
    tray_pixmap = pet.poses[0].scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    tray_icon.setIcon(QIcon(tray_pixmap))
    tray_icon.setToolTip("桌面宠物")

    # 托盘右键菜单（PRD：打开控制台、退出程序）
    tray_menu = QMenu()
    tray_menu.setStyleSheet(
        "QMenu{background:#ffffff;border:1px solid #bbb;border-radius:8px;"
        "padding:6px;color:#333;font-family:'Microsoft YaHei';font-size:13px;}"
        "QMenu::item{padding:6px 26px;border-radius:5px;}"
        "QMenu::item:selected{background:#4a90d9;color:white;}"
        "QMenu::separator{height:1px;background:#ddd;margin:4px 8px;}"
    )

    console_action = tray_menu.addAction("打开控制台")
    console_action.triggered.connect(pet.open_console)
    tray_menu.addSeparator()
    show_action = tray_menu.addAction("显示/隐藏")
    show_action.triggered.connect(
        lambda: pet.show() if pet.isHidden() else pet.hide())
    tray_menu.addSeparator()
    quit_action = tray_menu.addAction("退出程序")
    quit_action.triggered.connect(pet._quit)

    tray_icon.setContextMenu(tray_menu)

    # 双击托盘图标显示宠物
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if pet.isHidden():
                pet.show()
    tray_icon.activated.connect(on_tray_activated)

    tray_icon.show()
    pet._tray = tray_icon

    app._pet = pet  # 防止被回收
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
