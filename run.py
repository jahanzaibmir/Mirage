import os
import threading


def run_storefront():
    try:
        from storefront import create_app

        app = create_app()
        app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)
        return True
    except Exception as e:
        import traceback

        print("Storefront startup failed:", e)
        traceback.print_exc()
        return False


def run_admin_console():
    try:
        from storefront import create_admin_app

        app = create_admin_app()
        app.run(host=os.environ.get("ADMIN_HOST", "127.0.0.1"), port=int(os.environ.get("ADMIN_PORT", 5001)), debug=False, use_reloader=False)
        return True
    except Exception as e:
        import traceback

        print("Admin console startup failed:", e)
        traceback.print_exc()
        return False


if __name__ == "__main__":
    admin_thread = threading.Thread(target=run_admin_console, daemon=True)
    admin_thread.start()
    if not run_storefront():
        from mirage.server import main

        main()
