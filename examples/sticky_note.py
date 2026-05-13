import webview
import win32gui
import win32api
import win32con
import threading
import time


class NoteEngine:
    def __init__(self):
        self.target_hwnd = None
        self.main_hwnd = None

    def detach_logic(self, window_obj):
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
            return

        for i in range(100):
            chrome_hwnds = []

            def callback(hwnd, extra):
                if win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1":
                    chrome_hwnds.append(hwnd)
                    return False
                return True

            win32gui.EnumChildWindows(main_h, callback, None)
            chrome_h = chrome_hwnds[0] if chrome_hwnds else None

            if chrome_h and win32gui.IsWindowVisible(main_h):
                self.main_hwnd = main_h
                self.target_hwnd = chrome_h

                rect = win32gui.GetWindowRect(self.main_hwnd)
                x, y, w, h = rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]

                style = win32gui.GetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE)
                new_style = (style & ~win32con.WS_CHILD) | win32con.WS_POPUP
                win32gui.SetWindowLong(
                    self.target_hwnd, win32con.GWL_STYLE, new_style)

                win32gui.SetParent(self.target_hwnd, 0)

                win32gui.SetWindowPos(
                    self.target_hwnd, win32con.HWND_TOPMOST,
                    x, y, w, h,
                    win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW
                )

                win32gui.ShowWindow(self.main_hwnd, win32con.SW_HIDE)
                ex_style = win32gui.GetWindowLong(
                    self.main_hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(
                    self.main_hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TOOLWINDOW)
                break
            time.sleep(0.1)

    def start_drag(self):
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


html_content = """
<!DOCTYPE html>
<html>
<head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; user-select: none; }
        body { 
            width: 100vw; height: 100vh; 
            background: transparent; 
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif; 
            overflow: hidden; 
        }
        #container {
            width: 100%; height: 100%;
            background: rgba(45, 45, 45, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white; 
            display: flex; 
            flex-direction: column;
            border-radius: 12px;
            overflow: hidden;
        }
        #drag-bar {
            height: 30px; 
            background: rgba(255, 255, 255, 0.05);
            cursor: move; 
            display: flex; 
            align-items: center; 
            padding: 0 15px;
        }
        .title-text { font-size: 12px; opacity: 0.5; letter-spacing: 2px; width: 100%; text-align: center; }
        #note-area {
            flex: 1;
            width: 100%;
            background: transparent;
            border: none;
            outline: none;
            color: #e0e0e0;
            padding: 12px 15px;
            font-size: 14px;
            line-height: 1.5;
            resize: none;
            user-select: text;
        }
        #note-area::-webkit-scrollbar { width: 4px; }
        #note-area::-webkit-scrollbar-thumb { 
            background: rgba(255, 255, 255, 0.1); 
            border-radius: 10px; 
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="drag-bar" onmousedown="window.pywebview.api.start_drag()">
            <span class="title-text">Sticky Note</span>
        </div>
        <textarea id="note-area" placeholder="Write here..." spellcheck="false"></textarea>
    </div>
    <script>
        window.onload = function() { document.getElementById('note-area').focus(); };
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    engine = NoteEngine()
    window = webview.create_window(
        'StickyNote',
        html=html_content,
        transparent=True,
        js_api=engine,
        width=300,
        height=210
    )
    threading.Thread(target=engine.detach_logic,
                     args=(window,), daemon=True).start()
    webview.start()
