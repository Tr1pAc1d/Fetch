import webview
import os
import sys

def main():
    assets_dir = os.path.join(os.path.dirname(__file__), 'android', 'app', 'src', 'main', 'assets')
    if not os.path.exists(assets_dir):
        assets_dir = os.path.dirname(__file__)

    html_file = os.path.join(assets_dir, 'index.html')
    if not os.path.exists(html_file):
        html_file = os.path.join(os.path.dirname(__file__), 'assets', 'index.html')

    url = f'file:///{os.path.abspath(html_file).replace(os.sep, "/")}'

    print("=" * 60)
    print("      FETCH - PC MOBILE APP SIMULATOR & PREVIEW")
    print("=" * 60)
    print(f" Loading UI: {url}")
    print(" You can test touch gestures, Summon Keyboard, and Quick Links")
    print(" directly in this phone simulator window on your PC!")
    print("=" * 60)

    window = webview.create_window(
        title='Fetch - Mobile App Preview',
        url=url,
        width=410,
        height=850,
        resizable=True,
        min_size=(360, 640)
    )
    webview.start()

if __name__ == '__main__':
    main()
