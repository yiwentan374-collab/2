# -*- coding: utf-8 -*-
"""
桌面宠物 · 比熊 (Bichon Desktop Pet)
====================================
一个基于 tkinter + Pillow 的 Windows 桌面宠物。

特性：
  - 无边框、背景透明、始终置顶、不在任务栏显示
  - 鼠标左键拖拽移动；点击触发"开心/跳跃"动画 + 气泡文字
  - 状态机：待机(底部随机走动 / 停下摇尾巴) → 拖拽(挣扎惊讶) → 点击(开心)
  - 右键菜单：隐藏 / 关于 / 退出

依赖：Pillow（仅此一个第三方库，tkinter 为标准库自带）
打包：PyInstaller（见 pet.spec / build.bat）
"""

import os
import sys
import time
import random
import traceback
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk, ImageSequence

# =============================================================
# 1. 资源路径（兼容源码运行 与 PyInstaller 打包后运行）
# =============================================================
def resource_path(rel_path: str) -> str:
    """
    返回资源的绝对路径。
    PyInstaller 打包后，资源被解压到临时目录 sys._MEIPASS；
    源码直接运行时，则用脚本所在目录。
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


# =============================================================
# 2. 全局配置
# =============================================================
COLORKEY = "#FF00FF"          # 透明色键：窗口里这个颜色的像素会变透明（洋红几乎不会出现在素材里）
ASSET_DIR = "assets"          # 资源目录（相对路径，会被打包进 exe）

# 各状态对应的 GIF 文件名
GIFS = {
    "idle":  "bichon_idle.gif",    # 待机/呼吸（停下时使用）
    "walk":  "bichon_walk.gif",    # 走路
    "happy": "bichon_happy.gif",   # 开心/跳跃（点击）
    "drag":  "bichon_drag.gif",    # 挣扎/惊讶（拖拽）
    "sleep": "bichon_sleep.gif",   # 睡觉（长时间待机后）
}

WALK_SPEED = 3                # 走路时每帧水平位移像素
CLICK_MOVE_THRESHOLD = 6      # 鼠标移动小于该像素视为"点击"而非"拖拽"
HIDE_SECONDS = 15            # 右键"隐藏"后自动回来的秒数
SLEEP_AFTER_IDLE = 18        # 连续待机超过该秒数后进入睡觉

BUBBLE_TEXTS = [
    "汪！", "摸摸我~", "陪我玩呀", "今天也要开心！",
    "嘿嘿~", "最喜欢你了", "要出去散步吗？", "(*^▽^*)",
]


# =============================================================
# 3. GIF 加载：转成 tkinter 可用的帧序列
# =============================================================
def load_frames(filename):
    """
    读取 GIF，返回 (frames, durations)。
    frames     : list[ImageTk.PhotoImage]
    durations  : list[int]  每帧毫秒数

    透明处理：用"硬边遮罩"把素材贴到 COLORKEY 背景上——
    alpha>=128 的像素保留原色，其余填成色键色（届时被窗口设为透明）。
    这样既不会出现彩色毛边，也不会在白色身体里抠出透明空洞。
    """
    path = resource_path(os.path.join(ASSET_DIR, filename))
    im = Image.open(path)
    key_rgb = tuple(int(COLORKEY[i:i + 2], 16) for i in (1, 3, 5))  # (255,0,255)

    frames, durations = [], []
    for frame in ImageSequence.Iterator(im):
        rgba = frame.convert("RGBA")
        alpha = rgba.split()[3]
        mask = alpha.point(lambda a: 255 if a >= 128 else 0)        # 硬边遮罩
        canvas = Image.new("RGB", rgba.size, key_rgb)              # 色键背景
        canvas.paste(rgba.convert("RGB"), (0, 0), mask)            # 仅贴不透明部分
        frames.append(ImageTk.PhotoImage(canvas))
        durations.append(frame.info.get("duration", 80))
    return frames, durations


def flip_frames(filename):
    """生成水平翻转的帧（让走路能朝左/朝右）。"""
    path = resource_path(os.path.join(ASSET_DIR, filename))
    im = Image.open(path)
    key_rgb = tuple(int(COLORKEY[i:i + 2], 16) for i in (1, 3, 5))
    frames = []
    for frame in ImageSequence.Iterator(im):
        rgba = frame.convert("RGBA").transpose(Image.FLIP_LEFT_RIGHT)
        alpha = rgba.split()[3]
        mask = alpha.point(lambda a: 255 if a >= 128 else 0)
        canvas = Image.new("RGB", rgba.size, key_rgb)
        canvas.paste(rgba.convert("RGB"), (0, 0), mask)
        frames.append(ImageTk.PhotoImage(canvas))
    return frames


# =============================================================
# 4. 气泡文字窗口
# =============================================================
class Bubble(tk.Toplevel):
    """点击宠物时，在头顶弹出的一句话气泡，自动消失。"""
    def __init__(self, master, text, x, y):
        super().__init__(master)
        self.overrideredirect(True)          # 无边框
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.95)
        except tk.TclError:
            pass
        lbl = tk.Label(
            self, text=text, font=("Microsoft YaHei", 11, "bold"),
            bg="#FFFDF5", fg="#5a4a42", padx=12, pady=6,
            relief="solid", bd=1,
        )
        lbl.pack()
        self.update_idletasks()
        # 居中显示在给定坐标上方
        bw = self.winfo_reqwidth()
        self.geometry(f"+{int(x - bw / 2)}+{int(y)}")
        self.after(1600, self.destroy)        # 1.6 秒后消失


# =============================================================
# 5. 桌宠主体
# =============================================================
class DesktopPet:
    def __init__(self, root: tk.Tk):
        self.root = root

        # ---- 窗口外观：无边框 / 置顶 / 透明 / 不占任务栏 ----
        root.overrideredirect(True)                       # 无边框（同时不在任务栏显示）
        root.attributes("-topmost", True)                 # 始终置顶
        root.attributes("-transparentcolor", COLORKEY)    # 色键透明（Windows 专有）
        root.config(bg=COLORKEY)

        # ---- 加载全部动画帧 ----
        self.anims = {}        # state -> (frames, durations)
        for state, fn in GIFS.items():
            self.anims[state] = load_frames(fn)
        self.walk_left = flip_frames(GIFS["walk"])         # 朝左走的翻转帧

        # 画布尺寸 = 单帧尺寸
        self.w = self.anims["idle"][0][0].width()
        self.h = self.anims["idle"][0][0].height()

        # ---- 承载图像的标签（背景=色键=透明）----
        self.label = tk.Label(root, bd=0, bg=COLORKEY)
        self.label.pack()

        # ---- 屏幕信息 & 初始位置（屏幕底部）----
        self.screen_w = root.winfo_screenwidth()
        self.screen_h = root.winfo_screenheight()
        self.ground_y = self.screen_h - self.h - 48        # 预留任务栏高度
        self.x = random.randint(0, max(0, self.screen_w - self.w))
        self.y = self.ground_y
        self._move_window()

        # ---- 状态机变量 ----
        self.state = "idle"
        self.frame_i = 0
        self.direction = random.choice([-1, 1])            # 走路方向
        self.behavior_ticks = 0                            # 当前自主行为剩余时间(帧)
        self.temp_state_ticks = 0                          # 临时状态(开心)剩余帧
        self.idle_elapsed = 0.0                            # 已待机秒数(用于自动睡觉)
        self.dragging = False
        self._press = None                                 # 记录按下时的信息

        # ---- 事件绑定 ----
        self.label.bind("<ButtonPress-1>", self.on_press)
        self.label.bind("<B1-Motion>", self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Button-3>", self.on_menu)        # 右键菜单

        # ---- 右键菜单 ----
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="隐藏", command=self.hide)
        self.menu.add_command(label="关于", command=self.about)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.quit)

        # ---- 启动动画循环 ----
        self._choose_new_behavior()
        self.tick()

    # ---------- 窗口移动 ----------
    def _move_window(self):
        self.x = max(0, min(self.x, self.screen_w - self.w))
        self.root.geometry(f"{self.w}x{self.h}+{int(self.x)}+{int(self.y)}")

    # ---------- 帧驱动主循环 ----------
    def tick(self):
        frames, durations = self.anims[self.state]
        # 显示当前帧（走路且朝左时使用翻转帧）
        if self.state == "walk" and self.direction < 0:
            img = self.walk_left[self.frame_i % len(self.walk_left)]
        else:
            img = frames[self.frame_i % len(frames)]
        self.label.config(image=img)

        dur = durations[self.frame_i % len(durations)]
        self.frame_i += 1

        # ---- 行为逻辑（拖拽时不自动行动）----
        if not self.dragging:
            self._update_behavior(dur / 1000.0)

        self.root.after(dur, self.tick)

    # ---------- 行为状态机 ----------
    def _update_behavior(self, dt):
        # 临时状态（开心）倒计时结束后回到自主行为
        if self.temp_state_ticks > 0:
            self.temp_state_ticks -= 1
            if self.temp_state_ticks == 0:
                self._set_state("idle")
                self._choose_new_behavior()
            return

        # 走路：移动窗口
        if self.state == "walk":
            self.x += WALK_SPEED * self.direction
            if self.x <= 0:
                self.x, self.direction = 0, 1
            elif self.x >= self.screen_w - self.w:
                self.x, self.direction = self.screen_w - self.w, -1
            self._move_window()
            self.idle_elapsed = 0.0
        else:  # idle / sleep
            self.idle_elapsed += dt
            # 长时间待机 → 睡觉
            if self.state == "idle" and self.idle_elapsed >= SLEEP_AFTER_IDLE:
                self._set_state("sleep")

        # 自主行为计时
        self.behavior_ticks -= 1
        if self.behavior_ticks <= 0 and self.state != "sleep":
            self._choose_new_behavior()

    def _choose_new_behavior(self):
        """随机决定接下来是走动还是停下。"""
        if random.random() < 0.6:                 # 60% 走动
            self.direction = random.choice([-1, 1])
            self._set_state("walk")
            self.behavior_ticks = random.randint(25, 60)
        else:                                      # 40% 停下摇尾/呼吸
            self._set_state("idle")
            self.behavior_ticks = random.randint(20, 45)

    def _set_state(self, state):
        if self.state != state:
            self.state = state
            self.frame_i = 0
            if state != "idle":
                self.idle_elapsed = 0.0

    # ---------- 鼠标交互 ----------
    def on_press(self, event):
        self._press = {
            "sx": event.x_root, "sy": event.y_root,   # 按下时屏幕坐标
            "ox": event.x, "oy": event.y,             # 在窗口内的偏移
            "moved": False, "t": time.time(),
        }

    def on_drag(self, event):
        if not self._press:
            return
        dist = abs(event.x_root - self._press["sx"]) + abs(event.y_root - self._press["sy"])
        if dist > CLICK_MOVE_THRESHOLD:
            if not self.dragging:
                self.dragging = True
                self._set_state("drag")            # 播放挣扎/惊讶
            self._press["moved"] = True
            # 让窗口跟随鼠标
            self.x = event.x_root - self._press["ox"]
            self.y = event.y_root - self._press["oy"]
            self._move_window()

    def on_release(self, event):
        if not self._press:
            return
        moved = self._press["moved"]
        self._press = None
        if self.dragging:                          # 拖拽结束 → 回落到地面待机
            self.dragging = False
            self.y = self.ground_y
            self._move_window()
            self._set_state("idle")
            self._choose_new_behavior()
        elif not moved:                            # 纯点击 → 开心 + 气泡
            self._play_happy()

    def _play_happy(self):
        self._set_state("happy")
        frames, durations = self.anims["happy"]
        # 让开心动画播放约 2 个循环
        self.temp_state_ticks = len(frames) * 2
        x = self.x + self.w / 2
        y = self.y - 10
        Bubble(self.root, random.choice(BUBBLE_TEXTS), x, y)

    # ---------- 右键菜单功能 ----------
    def on_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def hide(self):
        """隐藏一段时间后自动回来（标准库无托盘，故用定时返回）。"""
        self.root.withdraw()
        self.root.after(HIDE_SECONDS * 1000, self._show_again)

    def _show_again(self):
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def about(self):
        messagebox.showinfo(
            "关于",
            "比熊桌面宠物 🐶\n\n"
            "左键点我 → 开心跳跃\n"
            "拖动我 → 换个位置\n"
            "右键 → 菜单\n\n"
            "Made with Python + tkinter + Pillow",
        )

    def quit(self):
        self.root.destroy()
        sys.exit(0)


# =============================================================
# 6. 入口（含崩溃日志，便于排查打包后闪退）
# =============================================================
def main():
    # 提升 DPI 清晰度（高分屏不糊）
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    root.title("BichonPet")
    DesktopPet(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # --noconsole 模式下没有控制台，把异常写到日志文件方便排查
        log = os.path.join(os.path.dirname(sys.executable)
                           if getattr(sys, "frozen", False)
                           else os.path.dirname(os.path.abspath(__file__)),
                           "pet_error.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
