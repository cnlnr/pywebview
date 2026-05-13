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

    def detach_logic(self, window_obj):
        """核心：通过 native 对象获取句柄并分离窗口"""
        print("正在等待原生对象初始化...")

        # 1. 轮询获取主窗口原生句柄
        main_h = None
        for _ in range(100):
            if window_obj.native is not None:
                try:
                    main_h = window_obj.native.Handle.ToInt32()
                    if main_h:
                        break
                except:
                    pass
            time.sleep(0.1)

        if not main_h:
            print("未能获取原生句柄")
            return

        # 2. 轮询查找内核子窗口
        for i in range(100):
            chrome_h = None
            chrome_hwnds = []

            def callback(hwnd, extra):
                if win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1":
                    chrome_hwnds.append(hwnd)
                    return False
                return True

            win32gui.EnumChildWindows(main_h, callback, None)
            chrome_h = chrome_hwnds[0] if chrome_hwnds else None

            # 确保子窗口已创建且可见
            if chrome_h and win32gui.IsWindowVisible(main_h):
                self.main_hwnd = main_h
                self.target_hwnd = chrome_h

                # --- 3. 捕获父窗口坐标 ---
                rect = win32gui.GetWindowRect(self.main_hwnd)
                x, y = rect[0], rect[1]
                w, h = rect[2] - rect[0], rect[3] - rect[1]

                # --- 4. 剥离并重设样式 ---
                style = win32gui.GetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE)
                new_style = (style & ~win32con.WS_CHILD) | win32con.WS_POPUP
                win32gui.SetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE, new_style)

                # --- 5. 改变父子关系 ---
                win32gui.SetParent(self.target_hwnd, 0)

                # --- 6. 同步几何属性 ---
                win32gui.SetWindowPos(
                    self.target_hwnd,
                    win32con.HWND_TOPMOST,
                    x, y, w, h,
                    win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW
                )

                # --- 7. 隐藏原壳体并从任务栏抹除 ---
                win32gui.ShowWindow(self.main_hwnd, win32con.SW_HIDE)
                ex_style = win32gui.GetWindowLong(
                    self.main_hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(
                    self.main_hwnd,
                    win32con.GWL_EXSTYLE,
                    ex_style | win32con.WS_EX_TOOLWINDOW
                )

                print(f"同步成功：坐标({x}, {y}) 尺寸({w}x{h})")
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


# --- UI HTML ---
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
            <span style="font-size: 12px; opacity: 0.8;">StickyNote Pro (Native Handle)</span>
            <span class="close" onclick="window.close()">×</span>
        </div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; flex-direction:column; padding:20px; text-align:center;">
            <p>已通过 .native.Handle 捕获</p>
            <p style="font-size:12px; opacity:0.5; margin-top:8px;">父窗口隐藏，位置已同步</p>
        </div>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    # 已去掉 DPI 感知代码
    engine = NoteEngine()

    window = webview.create_window(
        'StickyNote_Pro',
        html=html_content,
        transparent=True,
        js_api=engine,
        width=400,
        height=300
    )

    # 启动分离线程，传入 window 对象
    threading.Thread(target=engine.detach_logic,
                     args=(window,), daemon=True).start()

    webview.start()
