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

    def _get_main_and_chrome_hwnds(self):
        """同时获取父窗口和子窗口句柄"""
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
        """核心逻辑：分离子窗口并隐藏父窗口"""
        print("正在等待窗口初始化...")
        for _ in range(50):
            main_h, chrome_h = self._get_main_and_chrome_hwnds()

            if chrome_h:
                self.target_hwnd = chrome_h

                # 1. 改变样式：脱离从属关系，变为独立弹出窗口
                style = win32gui.GetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE)
                new_style = (style & ~win32con.WS_CHILD) | win32con.WS_POPUP
                win32gui.SetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE, new_style)

                # 2. 修改父子关系：将其父窗口设为桌面
                win32gui.SetParent(self.target_hwnd, 0)

                # 3. 隐藏原来的父窗口（那个空壳）
                # 注意：隐藏父窗口不会关闭程序，因为 webview 的消息循环还在运行
                win32gui.ShowWindow(main_h, win32con.SW_HIDE)

                # 4. 显示并刷新分离后的新窗口
                win32gui.ShowWindow(self.target_hwnd, win32con.SW_SHOW)
                win32gui.SetWindowPos(self.target_hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED)

                print(f"分离成功！父窗口 {hex(main_h)} 已隐藏，子窗口 {hex(chrome_h)} 已独立。")
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
                win32gui.SetWindowPos(self.target_hwnd, 0,
                                      int(mx - offset_x), int(my - offset_y),
                                      0, 0, 0x0001 | 0x0004 | 0x0010)
                time.sleep(0.005)

        threading.Thread(target=drag_loop, daemon=True).start()


# --- 全屏无边距 HTML ---
html_content = """
<!DOCTYPE html>
<html>
<head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; user-select: none; }
        html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
        
        #container {
            width: 100%; height: 100%;
            background: rgba(30, 30, 30, 0.85); /* 深色半透明风格 */
            color: white;
            display: flex;
            flex-direction: column;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        }
        
        #drag-bar {
            height: 35px;
            background: rgba(255, 255, 255, 0.1);
            cursor: move;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 15px;
            font-size: 12px;
        }

        #content {
            flex: 1;
            padding: 20px;
            text-align: center;
        }
        
        .close-btn { cursor: pointer; padding: 5px; }
        .close-btn:hover { color: #ff5f56; }
    </style>
</head>
<body>
    <div id="container">
        <div id="drag-bar" onmousedown="window.pywebview.api.start_drag()">
            <span>便签控制台</span>
            <span class="close-btn" onclick="window.close()">✕</span>
        </div>
        <div id="content">
            <h3>已成功分离并隐藏父窗口</h3>
            <p style="margin-top: 10px; font-size: 14px; opacity: 0.7;">
                现在这个窗口是完全独立的。
            </p>
        </div>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    # 启用 DPI 感知
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        ctypes.windll.user32.SetProcessDPIAware()

    api = NoteEngine()

    # 创建窗口
    # 注意：虽然我们在后台会隐藏它，但建议初始化时还是给个尺寸
    window = webview.create_window(
        'StickyNote_Pro',
        html=html_content,
        transparent=True,
        js_api=api,
        width=350,
        height=250
    )

    # 启动异步分离逻辑
    threading.Thread(target=api.detach_logic, daemon=True).start()

    webview.start()
