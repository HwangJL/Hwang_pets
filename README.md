# 桌面宠物 DesktopPet

一个基于 PyQt5 的桌面宠物程序，支持 AI 大模型接入、知识库待办梳理、话术自定义配置和多精灵动画。

## 快速开始

直接运行已打包的 exe：

```
dist/DesktopPet.exe
```

双击即可启动，无需安装 Python 或任何依赖。

## 版本记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-07-21 | 初始版本：透明置顶窗口、互动动画、气泡对话、系统托盘 |
| v1.1 | 2026-07-21 | 多精灵素材系统（6站姿/6动作/8表情）、精灵切片工具 |
| v1.2 | 2026-07-21 | 修复 drawLine 类型错误、toggle_top 气泡同步、清理死代码 |
| v2.0 | 2026-07-22 | 控制台三大模块（AI知识库待办、话术自定义、AI大模型接入）、配置持久化、气泡悬浮暂停 |
| v2.1 | 2026-07-22 | 测试连通性结果改为标签持久展示（✓/✗+时间戳）；待办生成结果展示成功/失败状态+时间+失败原因；AITodo线程添加详细分步日志 |
| v2.2 | 2026-07-22 | 新增AI渠道选择（火山引擎豆包/OpenAI/通义千问/DeepSeek/讯飞星火），切换渠道自动填充URL和模型名 |
| v2.3 | 2026-07-23 | 新增功能四：角色设定与外观更新（AI生成设定图/上传设定图切片），自动连通区域检测切片，桌宠外观实时更新 |

## 功能特性

### 桌宠基础

- **多精灵素材**：6 种站姿、6 种动作、8 种表情
- **互动动画**：点击触发跳跃、压扁回弹、左右抖动，动画中切换动作精灵
- **表情气泡**：互动时弹出表情图 + 话术内容，3 秒自动消失，鼠标悬浮暂停
- **拖动定位**：左键拖动宠物到任意位置
- **滚轮缩放**：滚轮调整宠物大小（90~620px）
- **系统托盘**：常驻后台运行，右键菜单操作

### 控制台（PRD 核心功能）

通过托盘右键菜单或桌宠右键菜单中的「打开控制台」唤起。

#### 功能一：知识库 & AI梳理本周待办

- 选择本地任意文件夹作为 AI 知识库
- 支持读取 `.txt`、`.md`、`.csv`、`.json`、`.log` 格式文件
- 调用已配置的 AI 大模型解析文件内容，自动生成本周待办清单
- 加载状态提示「正在AI解析梳理待办...」，处理期间按钮不可重复点击
- 结果在文本框中展示，支持滚动查看
- 生成完成后展示状态标签：成功显示绿色 ✓ + 时间戳，失败显示红色 ✗ + 时间戳 + 具体错误原因
- 数据本地留存，覆盖上一次梳理结果
- 全流程日志写入 `~/DesktopPet_run.log`，方便排查问题

#### 功能二：桌宠点击话术自定义

- **自定义文本模式**（默认）：自由输入多行话术内容
- **引用本周待办模式**：自动同步功能一 AI 梳理的待办清单，文本框锁定不可编辑
- 点击「保存配置」即时生效，无需重启桌宠
- 桌宠点击后弹出气泡展示已配置话术

#### 功能三：AI大模型接入配置

- **AI 总开关**：一键开启/关闭，关闭时所有 AI 相关功能禁用并置灰
- **AI 渠道选择**：内置 5 种渠道预设，切换后自动填充对应 URL 和模型名
  - 火山引擎(豆包)：`https://ark.cn-beijing.volces.com/api/v3/chat/completions`，模型 `doubao-seed-1-8-251228`
  - OpenAI 兼容：`https://api.openai.com/v1/chat/completions`，模型 `gpt-3.5-turbo`
  - 通义千问：`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`，模型 `qwen-plus`
  - DeepSeek：`https://api.deepseek.com/v1/chat/completions`，模型 `deepseek-chat`
  - 讯飞星火：`https://spark-api-open.xf-yun.com/v1/chat/completions`，模型 `generalv3.5`
- **API 接口地址**：选择渠道后自动填充，也支持手动修改为任意 OpenAI 兼容地址
- **API 密钥**：脱敏显示（星号隐藏），支持明文/隐藏切换
- **模型名称**：自定义输入（如 `gpt-3.5-turbo`、`qwen-plus`、`spark` 等）
- 保存时校验：AI 开启状态下任一配置为空则提示完善
- **测试连通性**：点击后调用 AI 接口验证配置有效性，结果持久展示在标签中--成功显示绿色 ✓ + 时间戳 + AI 回复摘要，失败显示红色 ✗ + 时间戳 + 错误原因

#### 功能四：角色设定与外观更新

支持两种模式更新桌宠外观，切片后自动重载精灵图，无需重启程序。

**模式A：AI生成设定图**
- 上传任意参考图片（人物、动物、玩偶、机器人等）
- AI 视觉模型（如 GPT-4o）分析参考图，提取角色特征（轮廓、配色、五官、服装等）
- AI 图片生成 API（如 DALL-E 3）根据特征描述生成 Q版卡通角色设定图
- 设定图包含多视角（正面/背面/侧面/3/4视角）、多动作（站立/行走/奔跑/坐下/跳跃）、多表情（默认/开心/困惑/专注/生气/受惊/得意/困倦）
- 图片生成 API 地址和模型名切换 AI 渠道时自动填充

**模式B：上传设定图切片**
- 直接上传已做好的角色设定图，跳过 AI 生成步骤

**自动切片算法**
- 使用 numpy 连通区域检测自动找到设定图中每个角色/表情的边界框
- 按 Y 坐标聚类分3行：第1行映射为 pose1-6、第2行 action1-6、第3行 face1-8
- 行内按 X 坐标排序，自动裁除透明边缘
- 切片完成后覆盖 `sprites/` 目录下同名文件，桌宠外观立即更新

**设定图布局要求**：第1行6个全身站姿从左到右排列，第2行6个动作姿态，第3行8个表情头像，背景使用纯色

## 操作说明

| 操作 | 效果 |
|------|------|
| 左键点击 | 触发互动动画 + 弹出话术气泡（3秒消失，悬浮暂停） |
| 左键拖动 | 移动宠物位置 |
| 滚轮 | 缩放宠物大小 |
| 右键（桌宠） | 菜单：打开控制台、调整大小、置顶开关、退出 |
| 右键（托盘） | 菜单：打开控制台、显示/隐藏、退出程序 |
| 关闭窗口 | 隐藏到系统托盘，不退出 |
| 双击托盘图标 | 重新显示宠物 |

## 项目结构

```
.
├── dist/
│   └── DesktopPet.exe      # 打包好的可执行文件（直接双击运行）
├── desktop_pet.py            # 主程序源码
├── config_manager.py         # 配置持久化管理
├── console_window.py         # 控制台窗口（四大功能模块）
├── sprite_slicer.py          # 自动切片工具（连通区域检测）
├── character.png             # 原始角色图（备用）
├── sprites/                   # 切片精灵图
│   ├── pose1~6.png            # 6 种站姿
│   ├── action1~6.png          # 6 种动作
│   └── face1~8.png            # 8 种表情
├── slice_sprites.py           # 精灵图切片脚本（硬编码坐标，备用）
├── remove_bg.py               # 背景去除脚本
├── DesktopPet.spec            # PyInstaller 打包配置
├── PRD.md                     # 产品需求文档
└── README.md                  # 本文件
```

## 配置存储

所有控制台配置自动保存到本地文件，重启桌宠或重启电脑后配置不丢失：

- **路径**：`C:\Users\<用户名>\.desktop_pet\config.json`

```json
{
  "ai": {
    "enabled": false,
    "provider": "openai_compatible",
    "api_url": "",
    "api_key": "",
    "model": ""
  },
  "knowledge_base": {
    "folder_path": "",
    "todos": ""
  },
  "phrase": {
    "mode": "custom",
    "custom_text": ""
  },
  "character_sheet": {
    "mode": "upload",
    "reference_image": "",
    "sheet_image": "",
    "image_gen_url": "",
    "image_gen_model": ""
  }
}
```

## AI 接口说明

本程序使用 OpenAI 兼容的 Chat Completions API 格式，支持以下服务商：

- OpenAI（`https://api.openai.com/v1/chat/completions`）
- 通义千问（`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`）
- 讯飞星火（OpenAI 兼容地址）
- 其他兼容 OpenAI 格式的第三方服务

配置时填入完整的 API 地址、密钥和模型名称即可。

## 从源码运行

需要 Python 3.8+ 和 PyQt5：

```bash
pip install PyQt5 numpy Pillow
python desktop_pet.py
```

## 重新打包 exe

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --add-data "sprites;sprites" --add-data "sprite_slicer.py;." --name DesktopPet desktop_pet.py
```

打包结果在 `dist/DesktopPet.exe`（约 42MB，单文件，内含所有精灵素材和切片工具）。

## 从原始图重新切片

如需从新的参考图重新生成精灵素材：

```bash
# 1. 修改 slice_sprites.py 中的 SRC 路径指向新图
python slice_sprites.py    # 2. 切片
python remove_bg.py        # 3. 去背景色
# 4. 重新打包 exe
pyinstaller --noconsole --onefile --add-data "sprites;sprites" --name DesktopPet desktop_pet.py
```
