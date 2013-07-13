def getDefault():
    if instance:
        return instance
    else:
        instance

class AlbumArtCache:
    instance = None

    @classmethod
    def getDefault(self):
        if self.instance:
            return self.instance
        else:
            self.instance = AlbumArtCache()
        return self.instance

    def makeDefaultIcon(self, width, height):
        pass
