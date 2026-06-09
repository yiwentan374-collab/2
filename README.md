# 比熊桌面宠物 🐶 (Bichon Desktop Pet)

基于 **Python + tkinter + Pillow** 的 Windows 桌面宠物。无边框、透明、置顶，会在桌面底部自己走来走去；点它会开心跳跃，拖它会惊讶挣扎，右键有菜单。最终可打包成**免安装、双击即运行的 `.exe`**。

---

## 1. 项目目录结构

```
desktop_pet/
├── app.py                # 主程序（全部逻辑都在这里）
├── assets/               # 动画资源（会被打包进 exe）
│   ├── bichon_idle.gif   # 待机/呼吸
│   ├── bichon_walk.gif   # 走路
│   ├── bichon_happy.gif  # 开心/跳跃（点击）
│   ├── bichon_drag.gif   # 挣扎/惊讶（拖拽）
│   └── bichon_sleep.gif  # 睡觉（长时间待机后）
├── pet.spec              # PyInstaller 打包配置
├── build.bat             # 一键打包脚本（Windows）
├── requirements.txt      # 依赖清单
└── README.md             # 本文件
```

> 可选：放一个 `icon.ico` 在根目录作为 exe 图标（`pet.spec` 里已引用；不需要就删掉那一行）。

---

## 2. 直接运行（开发调试）

```bat
pip install pillow
python app.py
```

操作方式：

| 操作 | 效果 |
|------|------|
| 左键**点击** | 开心跳跃 + 头顶气泡文字 |
| 左键**拖动** | 抓起来挣扎/惊讶，松手落回地面 |
| **右键** | 弹出菜单：隐藏 / 关于 / 退出 |
| 不理它 | 自己在底部左右走动，偶尔停下；很久没动会睡觉 |

---

## 3. 资源是怎么打进 exe 的

运行时用 `resource_path()` 统一取资源路径：

```python
def resource_path(rel_path):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)
```

- **源码运行**：`sys._MEIPASS` 不存在 → 用脚本所在目录 → 读 `./assets/xxx.gif`
- **打包后运行**：PyInstaller 把 exe 解压到临时目录并设置 `sys._MEIPASS` → 读 `临时目录/assets/xxx.gif`

而资源能进 exe，靠的是 `pet.spec` 里的：

```python
datas=[('assets', 'assets')]      # (源目录, 解压后相对目录)
```

纯命令行等价写法（**Windows 用分号 `;`**，Linux/Mac 用冒号 `:`）：

```bat
--add-data "assets;assets"
```

---

## 4. 一键打包

**方式 A：双击 `build.bat`**（最省事）

**方式 B：命令行用 spec**

```bat
pip install pillow pyinstaller
pyinstaller pet.spec --clean --noconfirm
```

**方式 C：一行命令（不写 spec）**

```bat
pyinstaller --noconfirm --clean --onefile --noconsole ^
  --name BichonPet ^
  --add-data "assets;assets" ^
  app.py
```

产物：`dist\BichonPet.exe`，可拷到任何 Windows 电脑双击运行，**无需安装 Python**。

关键参数说明：
- `--onefile` 打成单个 exe
- `--noconsole`（spec 里是 `console=False`）：运行时**不弹黑色控制台窗口**
- `--add-data` / `datas`：把 GIF 资源嵌进 exe

---

## 5. 常见问题排查

**Q1. 打包后双击闪退（源码运行却正常）**
多半是资源没打进去或路径不对。排查：
1. 程序已内置崩溃日志——闪退后看 exe 同目录的 `pet_error.log`，里面有完整堆栈。
2. 确认用了 `resource_path()` 读取，而不是写死 `./assets/...`。
3. 确认 `--add-data "assets;assets"`（Windows 是**分号**，写成冒号会失败）。
4. 先用 `console=True` / 去掉 `--noconsole` 打一版，让控制台把报错打出来，定位后再关。

**Q2. 提示找不到 GIF / `FileNotFoundError`**
- spec 的 `datas` 路径写错，或打包时 `assets` 目录不在当前工作目录。请在**项目根目录**执行打包命令。
- 检查文件名大小写（Windows 不敏感，但保持一致更稳）。

**Q3. 狗周围有彩色（洋红）毛边或白色身体里出现透明空洞**
- 程序用"硬边遮罩 + 色键透明"。若仍有毛边，可调大遮罩阈值（`load_frames` 里 `a >= 128` 改成 `>= 160`）。
- 若身体被抠出空洞，说明素材里恰好出现了色键色 `#FF00FF`。换一个素材里绝不出现的色键即可（改顶部 `COLORKEY`）。

**Q4. `-transparentcolor` 报错 / 在别的系统不透明**
- `-transparentcolor` 是 **Windows 专有**特性。本程序面向 Windows；macOS/Linux 下透明需改用其它方案（如带 alpha 的 `pygame`+无边框，或平台相关 API）。

**Q5. exe 体积大 / 启动慢**
- `--onefile` 启动时要先解压到临时目录，略慢属正常。想更快可去掉 `--onefile` 打成文件夹版（`--onedir`）。
- 开启 `upx=True`（spec 已开）可压缩体积；需本机装有 UPX，否则忽略该选项即可。

**Q6. 杀毒软件误报**
- PyInstaller 单文件 exe 常被误报。可加入信任名单，或改用 `--onedir`，或对 exe 做代码签名。

**Q7. 点了"隐藏"怎么找回来**
- 标准库没有系统托盘，所以"隐藏"会在 `HIDE_SECONDS`（默认 15 秒）后自动回来。
- 想要常驻托盘图标，可加装 `pystray`：`pip install pystray`，再在隐藏时创建托盘图标、点击恢复（README 外的增强项，按需扩展）。

---

## 6. 自定义

- 换形象：把 `assets/` 里的 GIF 换成你自己的同名文件即可（建议透明背景、尺寸一致）。
- 调走路速度：`app.py` 顶部 `WALK_SPEED`。
- 改气泡台词：`BUBBLE_TEXTS` 列表。
- 调睡觉触发时间：`SLEEP_AFTER_IDLE`（秒）。
