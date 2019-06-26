from gi.repository import GObject


class CoreSelection(GObject.GObject):

    selected_items_count = GObject.Property(type=int, default=0)

    def __init__(self):
        super().__init__()

        self._selected_items = []

    def update_selection(self, coresong, value):
        if coresong.props.selected:
            self.props.selected_items.append(coresong)
        else:
            try:
                self.props.selected_items.remove(coresong)
            except ValueError:
                pass

        self.props.selected_items_count = len(self.props.selected_items)

    @GObject.property
    def selected_items(self):
        return self._selected_items
