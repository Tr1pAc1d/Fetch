import os
import sys
import time
import shutil
import subprocess
import threading
import winreg
import webview

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..', 'Fetch-Release'))
if not os.path.exists(RELEASE_DIR):
    RELEASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))

TERMS_PATH = os.path.join(CURRENT_DIR, 'TERMS.txt')
if not os.path.exists(TERMS_PATH):
    TERMS_PATH = os.path.join(RELEASE_DIR, 'TERMS.txt')

TERMS_TEXT = ""
if os.path.exists(TERMS_PATH):
    with open(TERMS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        TERMS_TEXT = f.read()

HTML_CONTENT = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fetch Setup - TAB inc.</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; user-select: none; }}
  body {{
    background: #070b14;
    color: #f8fafc;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid rgba(56, 189, 248, 0.25);
  }}

  /* Top Bar */
  .titlebar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: #0b1120;
    border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  }}
  .brand-badge {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.5px;
  }}
  .brand-badge span {{
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    padding: 2px 7px;
    border-radius: 6px;
    border: 1px solid rgba(56, 189, 248, 0.2);
  }}
  .close-x {{
    color: #64748b;
    font-size: 16px;
    cursor: pointer;
    line-height: 1;
    padding: 4px;
    transition: color 0.15s;
  }}
  .close-x:hover {{ color: #ef4444; }}

  /* Content */
  .main-content {{
    flex: 1;
    padding: 24px 28px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    overflow-y: auto;
  }}
  .mascot-logo {{
    width: 68px;
    height: 68px;
    border-radius: 18px;
    box-shadow: 0 0 25px rgba(56, 189, 248, 0.35);
    border: 2px solid rgba(56, 189, 248, 0.4);
    margin-bottom: 12px;
    object-fit: cover;
  }}
  h1 {{
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 4px;
    background: linear-gradient(135deg, #ffffff, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .subtitle {{
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 16px;
  }}

  /* Privacy Banner (Highlighted) */
  .privacy-card {{
    width: 100%;
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 12px;
    padding: 10px 14px;
    text-align: left;
    margin-bottom: 16px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }}
  .shield-icon {{ font-size: 20px; }}
  .privacy-text {{ font-size: 11px; color: #cbd5e1; line-height: 1.45; }}
  .privacy-text b {{ color: #34d399; font-weight: 700; }}

  /* Option Toggles */
  .options-group {{
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 18px;
    text-align: left;
  }}
  .option-label {{
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: 12px;
    color: #cbd5e1;
    cursor: pointer;
    background: #0f172a;
    border: 1px solid #1e293b;
    padding: 8px 12px;
    border-radius: 9px;
    transition: border-color 0.15s;
  }}
  .option-label:hover {{
    border-color: rgba(56, 189, 248, 0.4);
  }}
  .option-label input {{
    accent-color: #0284c7;
    width: 15px;
    height: 15px;
    cursor: pointer;
  }}

  /* Install Button */
  .btn-install {{
    width: 100%;
    background: linear-gradient(135deg, #0284c7, #2563eb);
    color: white;
    border: none;
    padding: 13px;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 4px 18px rgba(37, 99, 235, 0.45);
    transition: transform 0.1s, opacity 0.2s;
    letter-spacing: 0.3px;
  }}
  .btn-install:active {{ transform: scale(0.98); opacity: 0.9; }}

  .terms-link {{
    font-size: 11px;
    color: #64748b;
    margin-top: 10px;
    cursor: pointer;
  }}
  .terms-link a {{ color: #38bdf8; text-decoration: none; }}
  .terms-link a:hover {{ text-decoration: underline; }}

  /* Progress View */
  #progress-view {{
    display: none;
    width: 100%;
    margin-top: 10px;
  }}
  .progress-bar-bg {{
    width: 100%;
    height: 10px;
    background: #1e293b;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 10px;
    border: 1px solid #334155;
  }}
  .progress-fill {{
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #38bdf8, #2563eb);
    border-radius: 8px;
    transition: width 0.3s ease;
  }}
  .status-step {{
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 8px;
  }}

  /* Done View */
  #done-view {{
    display: none;
    width: 100%;
    text-align: center;
  }}
  .done-badge {{
    font-size: 40px;
    margin-bottom: 8px;
  }}

  /* Terms Modal */
  .modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.85);
    backdrop-filter: blur(8px);
    z-index: 99;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }}
  .modal-box {{
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    max-width: 480px;
    width: 100%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    padding: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.8);
  }}
  .modal-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }}
  .modal-header h3 {{ font-size: 14px; font-weight: 800; color: #f8fafc; }}
  .modal-text {{
    overflow-y: auto;
    font-size: 11px;
    color: #94a3b8;
    line-height: 1.5;
    white-space: pre-wrap;
    background: #070b14;
    padding: 12px;
    border-radius: 10px;
    border: 1px solid #1e293b;
    flex: 1;
    font-family: monospace;
  }}
  .btn-close-modal {{
    margin-top: 12px;
    background: #0284c7;
    color: white;
    border: none;
    padding: 9px;
    border-radius: 9px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }}
</style>
</head>
<body>

<div class="titlebar">
  <div class="brand-badge">
    <span>TAB INC.</span> Fetch Setup Wizard
  </div>
  <div class="close-x" onclick="closeApp()">✕</div>
</div>

<div class="main-content">
  <img src="icon.png" class="mascot-logo" alt="Fetch Mascot">
  <h1>Fetch Touchpad Remote</h1>
  <p class="subtitle">v1.0.0 &bull; Fast, lightweight PC controller by TAB inc.</p>

  <!-- Initial Setup Options -->
  <div id="setup-view" style="width: 100%;">
    <div class="privacy-card">
      <div class="shield-icon">🛡️</div>
      <div class="privacy-text">
        <b>Privacy Guarantee: Zero Data Collection</b><br>
        We do NOT track, collect, or sell any user data. Fetch operates 100% locally on your Wi-Fi, optimized for low memory usage on older and modern PCs.
      </div>
    </div>

    <div class="options-group">
      <label class="option-label">
        <input type="checkbox" id="opt-firewall" checked>
        <span>Add Windows Defender / Firewall exception (Recommended)</span>
      </label>
      <label class="option-label">
        <input type="checkbox" id="opt-startup" checked>
        <span>Start Fetch automatically when Windows boots (System Tray)</span>
      </label>
      <label class="option-label">
        <input type="checkbox" id="opt-shortcut" checked>
        <span>Create Desktop Shortcut</span>
      </label>
    </div>

    <button class="btn-install" id="btn-start" onclick="startInstall()">⚡ Install Fetch</button>

    <div class="terms-link">
      By clicking Install, you agree to our <a href="#" onclick="openTerms()">Terms of Service & Privacy Policy</a>.
    </div>
  </div>

  <!-- Progress Bar View -->
  <div id="progress-view">
    <div class="status-step" id="status-step">Preparing installation...</div>
    <div class="progress-bar-bg">
      <div class="progress-fill" id="progress-fill"></div>
    </div>
    <div style="font-size: 11px; color: #64748b;" id="percent-label">0%</div>
  </div>

  <!-- Done View -->
  <div id="done-view">
    <div class="done-badge">🎉</div>
    <h2 style="font-size: 18px; font-weight: 800; color: #10b981; margin-bottom: 6px;">Installation Complete!</h2>
    <p style="font-size: 12px; color: #94a3b8; margin-bottom: 18px; line-height: 1.4;">
      Fetch is now running in your <b>Windows System Tray</b>.<br>
      Open the Fetch app on your Android phone to start controlling your PC.
    </p>
    <button class="btn-install" onclick="openWebHub()" style="margin-bottom: 8px;">🌐 Open Web Hub (Download APK)</button>
    <button class="btn-install" onclick="closeApp()" style="background: #1e293b; color: #cbd5e1; box-shadow: none;">Done & Close</button>
  </div>
</div>

<!-- Terms Modal -->
<div class="modal-overlay" id="terms-modal">
  <div class="modal-box">
    <div class="modal-header">
      <h3>Terms of Service & Privacy Standards</h3>
      <div class="close-x" onclick="closeTerms()">✕</div>
    </div>
    <div class="modal-text">{TERMS_TEXT.replace('`', '\\`')}</div>
    <button class="btn-close-modal" onclick="closeTerms()">I Understand</button>
  </div>
</div>

<script>
  function openTerms() {{ document.getElementById('terms-modal').style.display = 'flex'; }}
  function closeTerms() {{ document.getElementById('terms-modal').style.display = 'none'; }}
  function closeApp() {{ window.pywebview.api.close(); }}
  function openWebHub() {{ window.pywebview.api.open_hub(); }}

  function startInstall() {{
    const firewall = document.getElementById('opt-firewall').checked;
    const startup = document.getElementById('opt-startup').checked;
    const shortcut = document.getElementById('opt-shortcut').checked;

    document.getElementById('setup-view').style.display = 'none';
    document.getElementById('progress-view').style.display = 'block';

    window.pywebview.api.install(firewall, startup, shortcut);
  }}

  window.updateProgress = function(percent, text) {{
    document.getElementById('progress-fill').style.width = percent + '%';
    document.getElementById('percent-label').innerText = percent + '%';
    document.getElementById('status-step').innerText = text;
  }};

  window.onInstallComplete = function() {{
    document.getElementById('progress-view').style.display = 'none';
    document.getElementById('done-view').style.display = 'block';
  }};
</script>
</body>
</html>
"""

class InstallerApi:
    def __init__(self, window_ref):
        self.window = window_ref

    def close(self):
        try:
            self.window.destroy()
        except Exception:
            os._exit(0)

    def open_hub(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8080")
        self.close()

    def install(self, firewall, startup, shortcut):
        threading.Thread(target=self._run_install, args=(firewall, startup, shortcut), daemon=True).start()

    def _run_install(self, firewall, startup, shortcut):
        def notify(pct, msg):
            self.window.evaluate_js(f"window.updateProgress({pct}, '{msg}');")
            time.sleep(0.35)

        try:
            notify(10, "Creating program directories...")
            # Use LocalAppData for clean non-admin compatibility, or ProgramFiles
            app_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'TAB inc', 'Fetch')
            os.makedirs(app_dir, exist_ok=True)

            notify(25, "Extracting Fetch server files...")
            source_server = os.path.join(RELEASE_DIR, 'Fetch-Server.exe')
            if os.path.exists(source_server):
                shutil.copy2(source_server, os.path.join(app_dir, 'Fetch-Server.exe'))

            notify(45, "Installing assets & Android package...")
            for f in ['icon.ico', 'icon.png', 'Fetch.apk', 'TERMS.txt', 'README.md']:
                src = os.path.join(RELEASE_DIR, f)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(app_dir, f))

            target_exe = os.path.join(app_dir, 'Fetch-Server.exe')
            target_ico = os.path.join(app_dir, 'icon.ico')

            # Create Shortcuts
            if shortcut:
                notify(65, "Creating desktop shortcut...")
                try:
                    desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
                    lnk_path = os.path.join(desktop, 'Fetch.lnk')
                    ps_cmd = f"$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('{lnk_path}'); $s.TargetPath = '{target_exe}'; $s.IconLocation = '{target_ico}'; $s.Save()"
                    subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)
                except Exception:
                    pass

            # Start Menu shortcut
            try:
                programs = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'TAB inc')
                os.makedirs(programs, exist_ok=True)
                lnk_menu = os.path.join(programs, 'Fetch.lnk')
                ps_cmd = f"$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('{lnk_menu}'); $s.TargetPath = '{target_exe}'; $s.IconLocation = '{target_ico}'; $s.Save()"
                subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)
            except Exception:
                pass

            # Windows Startup Registry
            if startup:
                notify(80, "Configuring Windows Startup...")
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "Fetch", 0, winreg.REG_SZ, f'"{target_exe}"')
                    winreg.CloseKey(key)
                except Exception:
                    pass

            # Firewall Rule
            if firewall:
                notify(90, "Registering Windows Firewall exceptions...")
                try:
                    subprocess.run(
                        ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                         'name=Fetch Host (TAB inc.)', 'dir=in', 'action=allow',
                         f'program={target_exe}', 'enable=yes'],
                        capture_output=True
                    )
                except Exception:
                    pass

            notify(95, "Launching Fetch in system tray...")
            try:
                subprocess.Popen([target_exe])
            except Exception:
                pass

            notify(100, "Setup complete!")
            time.sleep(0.4)
            self.window.evaluate_js("window.onInstallComplete();")

        except Exception as e:
            notify(100, f"Error: {e}")

def main():
    # Write temp html file for webview
    tmp_html = os.path.join(CURRENT_DIR, 'installer_ui.html')
    # Copy icon to current dir if needed
    icon_png = os.path.join(RELEASE_DIR, 'icon.png')
    if os.path.exists(icon_png):
        shutil.copy2(icon_png, os.path.join(CURRENT_DIR, 'icon.png'))

    with open(tmp_html, 'w', encoding='utf-8') as f:
        f.write(HTML_CONTENT)

    window = webview.create_window(
        title='Fetch Setup - TAB inc.',
        url=f'file:///{tmp_html.replace(os.sep, "/")}',
        width=520,
        height=620,
        resizable=False,
        frameless=False
    )
    api = InstallerApi(window)
    window.expose(api.close, api.open_hub, api.install)
    webview.start()

if __name__ == '__main__':
    main()
