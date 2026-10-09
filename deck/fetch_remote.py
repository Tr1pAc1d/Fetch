import os
import sys
import socket
import threading
import time
import webview

class DesktopBridge:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def vibrate(self, ms=25):
        pass

    def wakeOnLan(self, mac_str):
        try:
            cleaned = mac_str.replace(':', '').replace('-', '').replace('.', '')
            if len(cleaned) != 12:
                return
            mac_bytes = bytes.fromhex(cleaned)
            magic_packet = b'\xff' * 6 + mac_bytes * 16
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('255.255.255.255', 9))
            sock.close()
        except Exception as e:
            print(f"[WOL Error] {e}")

    def startDiscovery(self):
        t = threading.Thread(target=self._run_discovery)
        t.daemon = True
        t.start()

    def _run_discovery(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2.5)

            msg = b"DISCOVER_FETCH"
            # Broadcast to network and loopback
            for target in ('255.255.255.255', '127.0.0.1'):
                try:
                    sock.sendto(msg, (target, 8766))
                except Exception:
                    pass

            start_t = time.time()
            discovered = set()
            while time.time() - start_t < 2.5:
                try:
                    data, addr = sock.recvfrom(1024)
                    text = data.decode('utf-8', errors='ignore').strip()
                    if text.startswith("FETCH_OFFER"):
                        parts = text.split("|")
                        hostname = parts[1] if len(parts) > 1 else "PC"
                        ip = parts[2] if len(parts) > 2 else addr[0]
                        port = int(parts[3]) if len(parts) > 3 else 8765
                        os_name = parts[4] if len(parts) > 4 else "Windows"
                        mac = parts[5] if len(parts) > 5 else ""

                        key = f"{ip}:{port}"
                        if key not in discovered:
                            discovered.add(key)
                            if self.window:
                                js = f"window.onServerDiscovered('{ip}', {port}, '{hostname}', '{os_name}', '{mac}');"
                                self.window.evaluate_js(js)
                except socket.timeout:
                    break
                except Exception:
                    pass

            sock.close()
            if self.window:
                self.window.evaluate_js("window.onDiscoveryComplete();")
        except Exception as e:
            print(f"[Discovery Error] {e}")


def get_html_path():
    # If bundled in PyInstaller
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        os.path.join(base, 'index.html'),
        os.path.join(base, '..', 'android', 'app', 'src', 'main', 'assets', 'index.html'),
        os.path.join(base, '..', '..', 'android', 'app', 'src', 'main', 'assets', 'index.html'),
        os.path.join(base, '..', 'Fetch-Release', 'index.html')
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None

def main():
    bridge = DesktopBridge()
    html_file = get_html_path()
    if not html_file or not os.path.exists(html_file):
        print("Error: index.html not found.")
        sys.exit(1)

    url = f'file:///{html_file.replace(os.sep, "/")}'

    window = webview.create_window(
        title='Fetch Remote (Touchpad) - TAB inc.',
        url=url,
        js_api=bridge,
        width=420,
        height=820,
        resizable=True,
        min_size=(360, 600)
    )
    bridge.set_window(window)

    # Trigger discovery on start after webview loads
    def on_loaded():
        time.sleep(0.5)
        bridge.startDiscovery()

    threading.Thread(target=on_loaded, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
