import webview
import win32gui
import win32api
import win32con
import ctypes
import threading
import time


class NoteEngine:
    def __init__(self):
        self.target_hwnd = None
        self.main_hwnd = None

    def _get_hwnds(self):
        """查找主窗口和内核窗口"""
        main_h = win32gui.FindWindow(None, 'StickyNote_Pro')
        if not main_h:
            return None, None

        chrome_hwnds = []

        def callback(hwnd, extra):
            if win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1":
                chrome_hwnds.append(hwnd)
                return False
            return True

        win32gui.EnumChildWindows(main_h, callback, None)
        target_h = chrome_hwnds[0] if chrome_hwnds else None
        return main_h, target_h

    def detach_logic(self):
        """核心：捕获位置 -> 剥离关系 -> 继承位置 -> 隐藏父级"""
        print("正在同步窗口几何数据...")
        for i in range(100):
            main_h, chrome_h = self._get_hwnds()

            # 确保主窗口已经渲染并可见
            if chrome_h and win32gui.IsWindowVisible(main_h):
                self.main_hwnd = main_h
                self.target_hwnd = chrome_h

                # --- 1. 获取父窗口当前的位置和大小 ---
                # rect 返回 (left, top, right, bottom)
                rect = win32gui.GetWindowRect(self.main_hwnd)
                x = rect[0]
                y = rect[1]
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]

                # --- 2. 预设样式 ---
                style = win32gui.GetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE)
                new_style = (style & ~win32con.WS_CHILD) | win32con.WS_POPUP
                win32gui.SetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE, new_style)

                # --- 3. 物理剥离 ---
                win32gui.SetParent(self.target_hwnd, 0)

                # --- 4. 瞬间同步几何属性 ---
                # 将子窗口移动到刚才记录的父窗口坐标，并保持大小一致
                win32gui.SetWindowPos(
                    self.target_hwnd,
                    win32con.HWND_TOPMOST,
                    x, y, w, h,
                    win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW
                )

                # --- 5. 隐藏原壳体 ---
                # 此时子窗口已经挡在了原位置，隐藏父窗口视觉上是无感的
                win32gui.ShowWindow(self.main_hwnd, win32con.SW_HIDE)

                # 移除任务栏残留
                ex_style = win32gui.GetWindowLong(
                    self.main_hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(
                    self.main_hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TOOLWINDOW)

                print(f"同步成功：子窗口已继承父窗口坐标 ({x}, {y}) 尺寸 {w}x{h}")
                break

            time.sleep(0.1)

    def start_drag(self):
        """处理自定义拖拽"""
        if not self.target_hwnd:
            return
        rect = win32gui.GetWindowRect(self.target_hwnd)
        ox, oy = win32api.GetCursorPos()
        offset_x, offset_y = ox - rect[0], oy - rect[1]

        def drag_loop():
            while win32api.GetAsyncKeyState(0x01) < 0:
                mx, my = win32api.GetCursorPos()
                win32gui.SetWindowPos(self.target_hwnd, 0, int(mx - offset_x), int(my - offset_y),
                                      0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
                time.sleep(0.005)
        threading.Thread(target=drag_loop, daemon=True).start()


# --- HTML/CSS 保持美观 ---
html_content = """
<!DOCTYPE html>
<html>
<head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; user-select: none; }
        body { width: 100vw; height: 100vh; background: transparent; font-family: "Microsoft YaHei", sans-serif; overflow: hidden; }
        #container {
            width: 100%; height: 100%;
            background: rgba(30, 30, 30, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white; display: flex; flex-direction: column;
        }
        #drag-bar {
            height: 35px; background: rgba(255, 255, 255, 0.05);
            cursor: move; display: flex; align-items: center; padding: 0 12px; justify-content: space-between;
        }
        .close { color: #ff5f56; cursor: pointer; font-size: 20px; }
    </style>
</head>
<body>
    <div id="container">
        <div id="drag-bar" onmousedown="window.pywebview.api.start_drag()">
            <span style="font-size: 12px; opacity: 0.8;">StickyNote Pro (Isolated)</span>
            <span class="close" onclick="window.close()">×</span>
        </div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; flex-direction:column;">
            <p>继承位置同步成功</p>
            <p style="font-size:12px; opacity:0.5; margin-top:8px;">父窗口已消失，子窗口接管坐标</p>
        </div>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    # 强制启用 DPI 感知，否则坐标计算会偏移
    ctypes.windll.user32.SetProcessDPIAware()

    engine = NoteEngine()

    # 初始创建窗口（这个窗口会被隐藏）
    window = webview.create_window(
        'StickyNote_Pro',
        html=html_content,
        transparent=True,
        js_api=engine,
        width=400,
        height=300
    )

    threading.Thread(target=engine.detach_logic, daemon=True).start()
    webview.start()
