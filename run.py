import os
import sys
import streamlit.web.cli as stcli

def main():
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(bundle_dir, 'app.py')

    sys.argv = [
        "streamlit", 
        "run", 
        app_path, 
        "--global.developmentMode=false",
        "--server.headless=false",
        "--client.toolbarMode=viewer"  # <--- This natively hides the Deploy button glitch-free
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()

