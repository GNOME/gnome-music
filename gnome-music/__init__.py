from gnomemusic import application
import sys

if __name__ == 'gnome-music':
    app = Application.application()
    sys.exit(app.run(sys.argv))
