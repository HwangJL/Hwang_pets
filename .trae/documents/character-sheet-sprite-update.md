# 工作台新增功能：上传图片 → 角色设定图生成 → 自动切片 → 更新桌宠外观

## 摘要

在控制台新增"功能四：角色设定与外观更新"模块，支持两种模式：
- **模式A（AI生成）**：上传参考图 → AI视觉模型分析提取特征 → AI图片生成API创建角色设定图 → 自动切片 → 更新桌宠
- **模式B（仅切片）**：用户直接上传已做好的角色设定图 → 自动连通区域检测切片 → 更新桌宠

切片使用 numpy 连通区域检测自动找到设定图中每个角色/表情的边界框，按行分组映射为 pose1-6 / action1-6 / face1-8。

## 当前状态分析

### 现有架构
- `console_window.py`：控制台含3个模块，通过 `_build_moduleN()` 构建，统一放入 QScrollArea
- `desktop_pet.py`：`DesktopPet` 类通过 `POSE_NAMES/ACTION_NAMES/FACE_NAMES` 常量加载 `sprites/` 下20张PNG，加载后过滤 `isNull()`
- `slice_sprites.py`：硬编码坐标切片脚本，非自动检测
- `remove_bg.py`：逐像素RGB容差去背景色
- `config_manager.py`：配置含 ai / knowledge_base / phrase 三段，`load_config()` 逐字段合并默认值
- `desktop_pet.py` 的 `_on_config_changed()` 仅重载配置，不重载精灵

### 关键限制
1. 当前 AI 配置仅支持文本 Chat Completions API，视觉分析和图片生成需要额外配置
2. `DesktopPet` 没有运行时重载精灵的方法
3. `slice_sprites.py` 是硬编码坐标，不支持自动检测

## 改动方案

### 1. 新建 `sprite_slicer.py` — 自动切片核心逻辑

**职责**：接收一张角色设定图 PNG，自动检测连通区域，按行分组映射为精灵图。

**实现要点**：
- 用 PIL 加载图片为 RGBA
- 用 numpy 创建二值掩码（alpha > 10 或与背景色差异大的像素 = 前景）
- 用 scipy.ndimage.label 做连通区域标记（如无 scipy 则用 BFS 实现）
- 过滤过小区域（面积 < 500像素），避免噪点
- 对每个连通区域计算 bounding box (left, top, right, bottom)
- 按 Y 坐标聚类分3行：
  - 第1行（y最小）→ pose1~6（按 x 排序）
  - 第2行 → action1~6（按 x 排序）
  - 第3行（y最大）→ face1~8（按 x 排序）
- 若某行检测到的数量与预期不符（非6/6/8），取前N个并补缺
- 裁剪每个区域，自动裁除透明边缘，保存到 `sprites/{name}.png`

**函数签名**：
```python
def slice_character_sheet(image_path, output_dir, bg_color=None, tolerance=30):
    """自动切片角色设定图，返回 [(name, path, w, h), ...] 和日志信息"""
```

### 2. 修改 `console_window.py` — 新增模块四

#### UI 结构（`_build_module4`）

```
QGroupBox "功能四：角色设定与外观更新"
├── 模式选择：QRadioButton "AI生成设定图" / "上传设定图切片"
├── [模式A] 参考图上传区
│   ├── QPushButton "选择参考图片"
│   ├── QLabel 显示缩略图预览 + 文件名
│   ├── QLabel "图片生成API地址" + QLineEdit（从渠道预设自动填充）
│   └── QPushButton "生成角色设定图"
├── [模式B] 设定图上传区
│   └── QPushButton "选择角色设定图"
├── QLabel 预览设定图（生成或上传后显示）
├── QPushButton "切片并更新桌宠外观"
├── QLabel lbl_sprite_result 状态标签（✓/✗ + 时间 + 详情）
```

#### 新增线程类

**`ImageAnalysisThread(QThread)`** — 模式A步骤1：视觉分析
- 接收：图片路径、api_url、api_key、model
- 将图片转为 base64，用 OpenAI Vision 格式发送到 Chat Completions API：
  ```json
  {"model": "...", "messages": [{"role": "user", "content": [
    {"type": "text", "text": "分析这张图片中的角色特征...（用户完整prompt）"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]}]}
  ```
- 返回：角色特征的文字描述

**`ImageGenThread(QThread)`** — 模式A步骤2：图片生成
- 接收：角色描述prompt、image_gen_url、api_key、model
- 用 OpenAI Images API 格式发送请求：
  ```json
  {"model": "dall-e-3", "prompt": "...", "n": 1, "size": "1024x1024"}
  ```
- 下载返回的图片URL，保存为临时文件
- 返回：生成图片的本地路径

**`SpriteSliceThread(QThread)`** — 切片（两种模式共用）
- 接收：设定图路径、输出目录
- 调用 `sprite_slicer.slice_character_sheet()`
- 返回：切片结果列表 + 日志

#### 模式切换逻辑
- `rb_ai_gen` 选中时：显示参考图上传区 + 图片生成API配置，隐藏设定图上传区
- `rb_upload_only` 选中时：显示设定图上传区，隐藏参考图上传区 + 图片生成API配置

#### 状态标签
- 与模块一/三一致：成功绿色 ✓ + 时间，失败红色 ✗ + 时间 + 原因
- 切片完成后显示"✓ HH:MM:SS 成功切出 N 个精灵，已更新桌宠外观"

### 3. 修改 `desktop_pet.py` — 新增精灵重载方法

在 `DesktopPet` 类中新增：

```python
def reload_sprites(self):
    """重新加载 sprites 目录下的所有精灵图"""
    self.poses = [pm for pm in (load_sprite(n) for n in self.POSE_NAMES) if not pm.isNull()]
    self.actions = [pm for pm in (load_sprite(n) for n in self.ACTION_NAMES) if not pm.isNull()]
    self.faces = [pm for pm in (load_sprite(n) for n in self.FACE_NAMES) if not pm.isNull()]
    if self.poses:
        self.pose_index = 0
        self.current_pixmap = self.poses[0]
    self._update_window_size()
    self.update()
```

修改 `open_console` 传给 ConsoleWindow 的回调，增加一个 `on_sprites_updated` 回调：
```python
def open_console(self):
    if self._console is None:
        self._console = ConsoleWindow(self.config, self._on_config_changed, self._on_sprites_updated)
    ...

def _on_sprites_updated(self):
    """精灵图更新后重新加载"""
    self.reload_sprites()
```

ConsoleWindow 的 `__init__` 增加第三个参数 `on_sprites_updated=None`。

### 4. 修改 `config_manager.py` — 新增配置段

```python
"character_sheet": {
    "mode": "upload",          # "ai_gen" 或 "upload"
    "reference_image": "",     # 参考图路径
    "sheet_image": "",         # 设定图路径
    "image_gen_url": "",       # 图片生成API地址
    "image_gen_model": ""      # 图片生成模型名
}
```

### 5. 图片生成 API 渠道预设

在 `console_window.py` 的 `AI_PROVIDERS` 旁新增图片生成预设：

```python
IMAGE_GEN_PRESETS = {
    "openai_compatible": ("https://api.openai.com/v1/images/generations", "dall-e-3"),
    "volcengine": ("https://ark.cn-beijing.volces.com/api/v3/images/generations", "doubao-seedream-3-0-t2i-250415"),
    "qwen": ("https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis", "wanx2.1-t2i-turbo"),
    "siliconflow": ("https://api.siliconflow.cn/v1/images/generations", "Kwai-Kolors/Kolors"),
}
```

切换AI渠道时自动填充对应的图片生成地址。

## 实施步骤

1. **新建 `sprite_slicer.py`**：实现 `slice_character_sheet()` 函数，连通区域检测 + 按行分组 + 裁剪保存
2. **修改 `config_manager.py`**：新增 `character_sheet` 配置段
3. **修改 `console_window.py`**：
   - 新增 `IMAGE_GEN_PRESETS` 常量
   - 新增 `ImageAnalysisThread`、`ImageGenThread`、`SpriteSliceThread` 三个线程类
   - 新增 `_build_module4()` 方法
   - 在 `__init__` 布局中添加 `layout.addWidget(self._build_module4())`
   - 新增模式切换、上传、生成、切片、状态展示等方法
   - `__init__` 增加 `on_sprites_updated` 参数
   - `_load_config_to_ui()` 加载新配置段
4. **修改 `desktop_pet.py`**：
   - 新增 `reload_sprites()` 方法
   - 修改 `open_console()` 传入 `on_sprites_updated` 回调
   - 新增 `_on_sprites_updated()` 方法
5. **打包测试**：PyInstaller 重新打包，验证两种模式均可正常工作

## 验证步骤

1. **模式B验证**：上传一张已有的角色设定图 → 点击"切片并更新桌宠外观" → 检查 sprites/ 目录下20个PNG被正确替换 → 桌宠外观实时更新
2. **模式A验证**：上传参考图 → 配置图片生成API → 点击"生成角色设定图" → 预览生成的设定图 → 点击"切片并更新桌宠外观" → 检查切片结果和桌宠更新
3. **异常处理验证**：上传非图片文件、API调用失败、切片检测到异常数量时，状态标签正确展示错误原因
4. **打包验证**：exe 运行后功能正常，日志输出到 `~/DesktopPet_run.log`

## 假设与决策

- **切片检测算法**：使用 alpha 通道判断前景（非透明 = 角色），若图片无 alpha 通道则用与边缘像素的色差判断背景
- **行分组策略**：按 Y 坐标的中点聚类为3行，每行内按 X 排序。若检测到数量不匹配6/6/8，取前N个并日志告警
- **图片生成API格式**：采用 OpenAI Images API 格式（`POST /images/generations`），兼容 SiliconFlow、Volcengine 等平台
- **视觉分析格式**：采用 OpenAI Vision API 格式（`image_url` + base64），兼容 GPT-4o、Qwen-VL 等
- **精灵文件覆盖**：切片时直接覆盖 sprites/ 目录下同名文件，不备份（用户可从 git 恢复）
- **依赖**：新增 `scipy` 依赖用于连通区域检测（若不想引入 scipy 可用纯 numpy BFS 替代，但性能稍差）
