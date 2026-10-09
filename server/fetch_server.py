import asyncio
import json
import socket
import threading
import time
import os
import sys
import platform
import shutil
import http.server
import socketserver
import websockets

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

CURRENT_OS = platform.system()  # 'Windows', 'Linux', 'Darwin'

# -------------------------------------------------------------
# OS Input Abstraction Layer
# -------------------------------------------------------------

if CURRENT_OS == 'Windows':
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32

    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800

    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    VK_LWIN = 0x5B
    VK_ESCAPE = 0x1B
    VK_RETURN = 0x0D
    VK_BACK = 0x08
    VK_TAB = 0x09
    VK_SPACE = 0x20
    VK_MENU = 0x12
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_PLAY_PAUSE = 0xB3

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = (
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_ulonglong if sys.maxsize > 2**32 else ctypes.c_ulong)
        )

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = (
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_ulonglong if sys.maxsize > 2**32 else ctypes.c_ulong)
        )

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = (("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD))

    class INPUT(ctypes.Structure):
        class _INPUT_UNION(ctypes.Union):
            _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))
        _anonymous_ = ("_input",)
        _fields_ = (("type", wintypes.DWORD), ("_input", _INPUT_UNION))

    def send_mouse(flags, dx=0, dy=0, data=0):
        inp = INPUT(0)
        inp.mi = MOUSEINPUT(int(dx), int(dy), int(data), flags, 0, 0)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    def move_cursor(dx, dy):
        send_mouse(MOUSEEVENTF_MOVE, dx, dy)

    def mouse_click(btn='left'):
        if btn == 'left':
            send_mouse(MOUSEEVENTF_LEFTDOWN)
            time.sleep(0.01)
            send_mouse(MOUSEEVENTF_LEFTUP)
        elif btn == 'right':
            send_mouse(MOUSEEVENTF_RIGHTDOWN)
            time.sleep(0.01)
            send_mouse(MOUSEEVENTF_RIGHTUP)
        elif btn == 'middle':
            send_mouse(MOUSEEVENTF_MIDDLEDOWN)
            time.sleep(0.01)
            send_mouse(MOUSEEVENTF_MIDDLEUP)

    def mouse_down(btn='left'):
        if btn == 'left': send_mouse(MOUSEEVENTF_LEFTDOWN)
        elif btn == 'right': send_mouse(MOUSEEVENTF_RIGHTDOWN)
        elif btn == 'middle': send_mouse(MOUSEEVENTF_MIDDLEDOWN)

    def mouse_up(btn='left'):
        if btn == 'left': send_mouse(MOUSEEVENTF_LEFTUP)
        elif btn == 'right': send_mouse(MOUSEEVENTF_RIGHTUP)
        elif btn == 'middle': send_mouse(MOUSEEVENTF_MIDDLEUP)

    def mouse_scroll(delta_y):
        amount = int(delta_y * 120)
        send_mouse(MOUSEEVENTF_WHEEL, 0, 0, amount)

    def send_key_vk(vk, keyup=False):
        flags = KEYEVENTF_KEYUP if keyup else 0
        inp = INPUT(1)
        inp.ki = KEYBDINPUT(vk, 0, flags, 0, 0)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    def press_and_release(vk):
        send_key_vk(vk, False)
        time.sleep(0.01)
        send_key_vk(vk, True)

    def type_unicode(text):
        for ch in text:
            code = ord(ch)
            inp_d = INPUT(1)
            inp_d.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0)
            user32.SendInput(1, ctypes.byref(inp_d), ctypes.sizeof(inp_d))
            time.sleep(0.003)
            inp_u = INPUT(1)
            inp_u.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)
            user32.SendInput(1, ctypes.byref(inp_u), ctypes.sizeof(inp_u))

    VK_MAP = {
        'vol_up': VK_VOLUME_UP, 'vol_down': VK_VOLUME_DOWN, 'vol_mute': VK_VOLUME_MUTE,
        'play_pause': VK_MEDIA_PLAY_PAUSE, 'next_track': VK_MEDIA_NEXT_TRACK, 'prev_track': VK_MEDIA_PREV_TRACK,
        'win': VK_LWIN, 'esc': VK_ESCAPE, 'enter': VK_RETURN, 'backspace': VK_BACK, 'tab': VK_TAB, 'space': VK_SPACE
    }

    def handle_key_action(action):
        if action in VK_MAP:
            press_and_release(VK_MAP[action])
        elif action == 'alt_tab':
            send_key_vk(VK_MENU, False)
            press_and_release(VK_TAB)
            time.sleep(0.04)
            send_key_vk(VK_MENU, True)

else:
    # Cross-Platform Linux / macOS Fallback using pynput or pyautogui
    try:
        from pynput.mouse import Controller as MouseController, Button
        from pynput.keyboard import Controller as KeyController, Key
        mouse_ctrl = MouseController()
        kb_ctrl = KeyController()

        def move_cursor(dx, dy): mouse_ctrl.move(dx, dy)
        def mouse_click(btn='left'):
            b = Button.left if btn == 'left' else (Button.right if btn == 'right' else Button.middle)
            mouse_ctrl.click(b)
        def mouse_down(btn='left'):
            b = Button.left if btn == 'left' else Button.right
            mouse_ctrl.press(b)
        def mouse_up(btn='left'):
            b = Button.left if btn == 'left' else Button.right
            mouse_ctrl.release(b)
        def mouse_scroll(delta_y): mouse_ctrl.scroll(0, delta_y)
        def type_unicode(text): kb_ctrl.type(text)
        def handle_key_action(action):
            if action == 'enter': kb_ctrl.tap(Key.enter)
            elif action == 'backspace': kb_ctrl.tap(Key.backspace)
            elif action == 'esc': kb_ctrl.tap(Key.esc)
            elif action == 'tab': kb_ctrl.tap(Key.tab)
            elif action == 'space': kb_ctrl.tap(Key.space)
            elif action == 'win': kb_ctrl.tap(Key.cmd)
    except ImportError:
        print("[Warning] pynput not installed. Running in mock input mode on non-Windows OS.")
        def move_cursor(dx, dy): pass
        def mouse_click(btn='left'): pass
        def mouse_down(btn='left'): pass
        def mouse_up(btn='left'): pass
        def mouse_scroll(delta_y): pass
        def type_unicode(text): pass
        def handle_key_action(action): pass

# -------------------------------------------------------------
# Cross-Platform Browser Launcher
# -------------------------------------------------------------
import subprocess
import webbrowser

def launch_browser_url(url):
    if not url: return
    url = url.strip()
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url

    # Try Firefox first
    firefox_cmd = None
    if CURRENT_OS == 'Windows':
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%LocalAppData%\Mozilla Firefox\firefox.exe"),
            shutil.which('firefox')
        ]
        for c in candidates:
            if c and os.path.exists(c):
                firefox_cmd = [c, url]
                break
    elif CURRENT_OS == 'Linux':
        if shutil.which('firefox'):
            firefox_cmd = ['firefox', url]
    elif CURRENT_OS == 'Darwin':
        if os.path.exists('/Applications/Firefox.app'):
            firefox_cmd = ['open', '-a', 'Firefox', url]

    if firefox_cmd:
        try:
            print(f"[Fetch] Opening in Firefox: {url}")
            subprocess.Popen(firefox_cmd)
            return
        except Exception as e:
            print(f"[Fetch] Firefox error: {e}")

    # Fallback to system default browser
    print(f"[Fetch] Opening in default browser: {url}")
    webbrowser.open(url)

# -------------------------------------------------------------
# Power & Sleep Timers
# -------------------------------------------------------------
sleep_timer_obj = None
sleep_timer_lock = threading.Lock()

def put_pc_to_sleep():
    if CURRENT_OS == 'Windows':
        subprocess.Popen(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'])
    elif CURRENT_OS == 'Linux':
        subprocess.Popen(['systemctl', 'suspend'])
    elif CURRENT_OS == 'Darwin':
        subprocess.Popen(['pmset', 'sleepnow'])

def handle_power_action(action, minutes=0):
    global sleep_timer_obj
    if action == 'lock':
        if CURRENT_OS == 'Windows':
            try:
                ctypes.windll.user32.LockWorkStation()
            except Exception:
                pass
        elif CURRENT_OS == 'Linux':
            subprocess.Popen(['xdg-screensaver', 'lock'])
        elif CURRENT_OS == 'Darwin':
            subprocess.Popen(['pmset', 'displaysleepnow'])
    elif action == 'sleep':
        put_pc_to_sleep()
    elif action == 'shutdown':
        if CURRENT_OS == 'Windows':
            subprocess.Popen(['shutdown', '/s', '/t', '0'])
        else:
            subprocess.Popen(['shutdown', '-h', 'now'])
    elif action == 'restart':
        if CURRENT_OS == 'Windows':
            subprocess.Popen(['shutdown', '/r', '/t', '0'])
        else:
            subprocess.Popen(['shutdown', '-r', 'now'])
    elif action == 'start_sleep_timer':
        with sleep_timer_lock:
            if sleep_timer_obj:
                sleep_timer_obj.cancel()
            sec = max(1, int(minutes)) * 60
            sleep_timer_obj = threading.Timer(sec, put_pc_to_sleep)
            sleep_timer_obj.daemon = True
            sleep_timer_obj.start()
    elif action == 'cancel_sleep_timer':
        with sleep_timer_lock:
            if sleep_timer_obj:
                sleep_timer_obj.cancel()
                sleep_timer_obj = None

# -------------------------------------------------------------
# Network & UDP Beacon Auto-Discovery (Port 8766)
# -------------------------------------------------------------

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def get_mac_address():
    try:
        import uuid
        node = uuid.getnode()
        return ':'.join(f'{(node >> i) & 0xff:02x}' for i in range(40, -1, -8))
    except Exception:
        return '00:00:00:00:00:00'

def udp_beacon():
    ip = get_local_ip()
    hostname = socket.gethostname()
    mac = get_mac_address()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('0.0.0.0', 8766))
    except Exception as e:
        print(f"[Beacon] Bind error: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8', errors='ignore').strip()
            if msg in ('DISCOVER_FETCH', 'DISCOVER_PC_TOUCH'):
                response = f"FETCH_OFFER|{hostname}|{ip}|8765|{CURRENT_OS}|{mac}"
                sock.sendto(response.encode('utf-8'), addr)
                print(f"[Beacon] Discovered by {addr[0]} ({hostname} @ {ip})")
        except Exception:
            time.sleep(0.5)

# -------------------------------------------------------------
# WebSocket Server (Port 8765)
# -------------------------------------------------------------

async def handle_ws(websocket):
    client_ip = websocket.remote_address[0]
    print(f"[Fetch] Connected: {client_ip}")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                mtype = data.get('type')

                if mtype == 'move':
                    move_cursor(data.get('dx', 0), data.get('dy', 0))
                elif mtype == 'click':
                    mouse_click(data.get('btn', 'left'))
                elif mtype == 'down':
                    mouse_down(data.get('btn', 'left'))
                elif mtype == 'up':
                    mouse_up(data.get('btn', 'left'))
                elif mtype == 'scroll':
                    mouse_scroll(data.get('dy', 0))
                elif mtype == 'key':
                    handle_key_action(data.get('key'))
                elif mtype == 'text':
                    type_unicode(data.get('text', ''))
                elif mtype == 'launch_url':
                    launch_browser_url(data.get('url', ''))
                elif mtype == 'power':
                    handle_power_action(data.get('action'), data.get('minutes', 0))
                elif mtype == 'zoom':
                    delta = data.get('delta', 1)
                    if CURRENT_OS == 'Windows':
                        send_key_vk(0x11, False) # VK_CONTROL down
                        mouse_scroll(delta)
                        time.sleep(0.01)
                        send_key_vk(0x11, True)  # VK_CONTROL up
                    else:
                        mouse_scroll(delta)
            except Exception:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"[Fetch] Disconnected: {client_ip}")

# -------------------------------------------------------------
# Web Landing & Download Portal (Port 8080)
# -------------------------------------------------------------

PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fetch - Touchpad Remote</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
  body { background: #070b14; color: #f1f5f9; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 24px; text-align: center; }
  .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 24px; padding: 36px 28px; max-width: 440px; width: 100%; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
  .badge { background: rgba(56, 189, 248, 0.1); color: #38bdf8; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; margin-bottom: 16px; border: 1px solid rgba(56, 189, 248, 0.3); }
  h1 { font-size: 32px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.5px; }
  p { color: #94a3b8; font-size: 15px; line-height: 1.5; margin-bottom: 24px; }
  .btn-download { display: block; background: linear-gradient(135deg, #0284c7, #2563eb); color: white; text-decoration: none; padding: 14px 20px; border-radius: 14px; font-weight: 700; font-size: 16px; margin-bottom: 12px; transition: transform 0.2s; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4); }
  .btn-download:active { transform: scale(0.98); }
  .status-box { background: #1e293b; border-radius: 12px; padding: 12px; font-size: 13px; color: #cbd5e1; }
  .green-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981; margin-right: 6px; box-shadow: 0 0 8px #10b981; }
</style>
</head>
<body>
<div class="card">
  <div class="badge">🐕 FETCH CONTROLLER</div>
  <h1>Fetch Touchpad</h1>
  <p>Control your PC with smooth touchscreen gestures, summon keyboard, and Firefox quick links.</p>
  <a href="/Fetch.apk" class="btn-download">📱 Download Android App (.apk)</a>
  <div class="status-box">
    <span class="green-dot"></span> Host Server is active on this machine
  </div>
</div>
</body>
</html>
"""

class PortalHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(PORTAL_HTML.encode('utf-8'))
        elif self.path in ('/Fetch.apk', '/app-debug.apk'):
            apk_path = os.path.join(os.path.dirname(__file__), '..', 'Fetch.apk')
            if not os.path.exists(apk_path):
                apk_path = os.path.join(os.path.dirname(__file__), 'Fetch.apk')
            if os.path.exists(apk_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/vnd.android.package-archive')
                self.send_header('Content-Disposition', 'attachment; filename="Fetch.apk"')
                self.send_header('Content-Length', str(os.path.getsize(apk_path)))
                self.end_headers()
                with open(apk_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"APK is compiling. Please check back shortly.")
        else:
            super().do_GET()

    def log_message(self, format, *args):
        return

def run_portal():
    try:
        httpd = socketserver.TCPServer(('0.0.0.0', 8080), PortalHandler)
        httpd.serve_forever()
    except Exception:
        pass

# -------------------------------------------------------------
# System Tray Integration
# -------------------------------------------------------------

def get_tray_icon_image():
    candidates = [
        os.path.join(getattr(sys, '_MEIPASS', ''), 'icon.ico'),
        os.path.join(getattr(sys, '_MEIPASS', ''), 'icon.png'),
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'icon.ico'),
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'icon.png'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'icon.ico'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'icon.png'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.png'),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            try:
                from PIL import Image
                return Image.open(c)
            except Exception:
                pass
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (64, 64), color=(2, 132, 199, 255))
        d = ImageDraw.Draw(img)
        d.ellipse((16, 16, 48, 48), fill=(255, 255, 255, 255))
        return img
    except Exception:
        return None

def create_tray_icon(ip, host):
    try:
        import pystray
        from PIL import Image
    except ImportError:
        return None

    img = get_tray_icon_image()
    if not img:
        return None

    def on_open_hub(icon, item):
        webbrowser.open(f"http://{ip}:8080")

    def on_show_info(icon, item):
        if CURRENT_OS == 'Windows':
            msg = (
                f"Fetch Host Server (TAB inc.)\n\n"
                f"Status: Active in System Tray\n"
                f"Hostname: {host}\n"
                f"Local IP: {ip}\n"
                f"Touchpad Port: 8765\n"
                f"Web Hub: http://{ip}:8080\n\n"
                f"Your PC will be discovered automatically by the Fetch Android app.\n"
                f"Fetch stays running quietly in the tray without any popup windows."
            )
            ctypes.windll.user32.MessageBoxW(0, msg, "Fetch - Host Status", 0x40 | 0x0)
        else:
            print(f"[Fetch] Status: Active on {ip}:8765")

    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem(f"Fetch Host v1.0.0", None, enabled=False),
        pystray.MenuItem(f"● Online: {ip}", on_show_info),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌐 Open Web Hub (Download APK)", on_open_hub),
        pystray.MenuItem("ℹ️ Connection Details", on_show_info),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Exit Fetch", on_exit)
    )

    icon = pystray.Icon(
        "FetchServer",
        img,
        title=f"Fetch Host - {host} ({ip}:8765)",
        menu=menu
    )
    return icon

# -------------------------------------------------------------
# Main Runner
# -------------------------------------------------------------

def main():
    if CURRENT_OS == 'Windows':
        # Single-instance enforcement
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\FetchServerHostMutex_TABinc")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(
                0,
                "Fetch Server is already running in your system tray.\nLook for the Husky icon in your notification area.",
                "Fetch Server",
                0x40
            )
            sys.exit(0)

    ip = get_local_ip()
    host = socket.gethostname()

    # Start UDP discovery beacon
    threading.Thread(target=udp_beacon, daemon=True).start()

    # Start Web landing & download portal
    threading.Thread(target=run_portal, daemon=True).start()

    # Start WebSocket server in background thread
    def run_ws():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def ws_loop():
            async with websockets.serve(handle_ws, '0.0.0.0', 8765):
                await asyncio.Future()
        try:
            loop.run_until_complete(ws_loop())
        except Exception:
            pass

    ws_thread = threading.Thread(target=run_ws, daemon=True)
    ws_thread.start()

    # Run System Tray
    tray = create_tray_icon(ip, host)
    if tray:
        try:
            tray.run()
        except Exception:
            pass
    else:
        # Fallback for headless environments without GUI/tray
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Fetch] Server stopped.")

if __name__ == '__main__':
    main()
