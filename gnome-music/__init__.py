from application import Application
import sys

if __name__ == 'gnome-music':
    app = Application()
    sys.exit(app.run(sys.argv))
