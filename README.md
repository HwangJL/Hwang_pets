# 桌面宠物 DesktopPet

一个基于 PyQt5 的桌面宠物程序，支持多精灵动画、互动表情和系统托盘。

## 快速开始

直接运行已打包的 exe：

```
dist/DesktopPet.exe
```

双击即可启动，无需安装 Python 或任何依赖。

## 功能特性

- **多精灵素材**：6 种站姿、6 种动作、8 种表情
- **互动动画**：点击触发跳跃、压扁回弹、左右抖动
- **表情气泡**：互动时弹出随机表情图 + 中文对话
- **拖动定位**：左键拖动宠物到任意位置
- **滚轮缩放**：滚轮调整宠物大小（90~620px）
- **系统托盘**：关闭窗口隐藏到托盘，双击恢复
- **右键菜单**：调整大小、置顶开关、退出

## 操作说明

| 操作 | 效果 |
|------|------|
| 左键点击 | 触发互动动画（跳跃/压扁/抖动 + 表情气泡） |
| 左键拖动 | 移动宠物位置 |
| 滚轮 | 缩放宠物大小 |
| 右键 | 打开菜单（调整大小、置顶开关、退出） |
| 关闭窗口 | 隐藏到系统托盘，不退出 |
| 双击托盘图标 | 重新显示宠物 |

## 项目结构

```
.
├── dist/
│   └── DesktopPet.exe     # 打包好的可执行文件（直接双击运行）
├── desktop_pet.py          # 主程序源码
├── character.png           # 原始角色图（备用）
├── sprites/                 # 切片精灵图
│   ├── pose1~6.png          # 6 种站姿
│   ├── action1~6.png        # 6 种动作
│   └── face1~8.png          # 8 种表情
├── slice_sprites.py         # 精灵图切片脚本
├── remove_bg.py             # 背景去除脚本
└── DesktopPet.spec          # PyInstaller 打包配置
```

## 从源码运行

需要 Python 3.8+ 和 PyQt5：

```bash
pip install PyQt5
python desktop_pet.py
```

## 重新打包 exe

如需修改代码后重新打包：

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --add-data "sprites;sprites" --name DesktopPet desktop_pet.py
```

打包结果在 `dist/DesktopPet.exe`（约 36MB，单文件，内含所有精灵素材）。

## 从原始图重新切片

如需从新的参考图重新生成精灵：

```bash
# 1. 修改 slice_sprites.py 中的 SRC 路径指向新图
# 2. 运行切片
python slice_sprites.py

# 3. 去除背景色（修改 BG_COLOR 为实际背景色）
python remove_bg.py

# 4. 重新打包
pyinstaller --noconsole --onefile --add-data "sprites;sprites" --name DesktopPet desktop_pet.py
```
