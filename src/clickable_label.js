const Gtk = imports.gi.Gtk;
const Gdk = imports.gi.Gdk;
const Lang = imports.lang;

const ClickableLabel = new Lang.Class({
    Name: "ClickableLabel",
    Extends: Gtk.EventBox,
    
    _init: function (text) {
        let hbox = new Gtk.HBox ();
        let label = new Gtk.Label ({label : text});
        label.set_alignment(0, 0.5);
        
        this.parent ();
        hbox.add (label);
        this.add(hbox);
        /*
        this.connect ("enter_notify_event", function () {
			let cursor = new Gdk.Cursor ({Gdk.CursorType.HAND2});
			
			this.get_window ().set_cursor (cursor);
			return false;
        });
        
        this.connect("leave_notify_event", function () {
			let cursor = new Gdk.Cursor (Gdk.CursorType.Arrow);
			
			this.get_window ().set_cursor (cursor);
			return false;
		});
        */ 
    },
    
});
