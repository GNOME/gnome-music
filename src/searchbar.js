/*
 * Copyright (c) 2013 Eslam Mostafa<cseslam@gmail.com>.
 *
 * Gnome Music is free software; you can Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * Gnome Music is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with Gnome Music; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * Author: Eslam Mostafa <cseslam@gmail.com>
 *
 */

const Lang = imports.lang;
const Gtk = imports.gi.Gtk;
const Gdk = imports.gi.Gdk;
const Gd = imports.gi.Gd;

const Searchbar = new Lang.Class({
    Name: "Searchbar",
    
    actor: function() { return this._eventbox; },
    
    _eventbox: null,
    
    _search_entry: null,
    
    _init: function() {
        this._setup_ui();
    },

    _setup_ui: function() {
        this._eventbox = new Gtk.EventBox();
        //this._eventbox.margin_top = 5;
        //this._eventbox.margin_bottom = 5;

        let container = new Gd.MarginContainer();
        //container.min_margin = 64;
        //container.max_margin = 128;
        this._eventbox.add (container);

        let box = new Gtk.Box({orientation: Gtk.Orientation.HORIZONTAL, spacing : 0});
        container.add(box);

        this._search_entry = new Gd.TaggedEntry();
        this._search_entry.hexpand = true;
        this._search_entry.key_press_event.connect (on_search_entry_key_pressed);
        this._search_entry.changed.connect (on_search_entry_changed);
        this._search_entry.tag_clicked.connect (on_search_entry_tag_clicked);
        box.add (this._search_entry);

        this._eventbox.show_all();
    },

    _on_search_entry_key_pressed: function(e) {
        let keyval = e.keyval;
        
        if(keyval == Gdk.Key.Escape) {
            //App.app.search_mode = false;
            return true;
        }

        return false;
    },

    _on_search_entry_changed: function() {
        debug("2");
    },

    _on_search_entry_tag_clicked: function() {
        debug("3");
    },

    show: function() {
        this.actor.show();
    },

    hide: function() {
        this.actor.hide();
    },

    grab_focus: function() {
        this._search_entry.grab_focus();
    },

});

const Dropdown = new Lang.Class({
    Name: 'Dropdown',

    _init: function() {
        this._sourceView = new Manager.BaseView(Application.sourceManager);
        this._typeView = new Manager.BaseView(Application.searchTypeManager);
        this._matchView = new Manager.BaseView(Application.searchMatchManager);
        // TODO: this is out for now, but should we move it somewhere
        // else?
        // this._categoryView = new Manager.BaseView(Application.searchCategoryManager);

        this._sourceView.connect('item-activated',
                                 Lang.bind(this, this._onItemActivated));
        this._typeView.connect('item-activated',
                               Lang.bind(this, this._onItemActivated));
        this._matchView.connect('item-activated',
                                Lang.bind(this, this._onItemActivated));

        let frame = new Gtk.Frame({ shadow_type: Gtk.ShadowType.IN,
                                    opacity: 0.9 });
        frame.get_style_context().add_class('documents-dropdown');

        this.widget = new Gd.Revealer({ halign: Gtk.Align.CENTER,
                                        valign: Gtk.Align.START });
        this.widget.add(frame);

        this._grid = new Gtk.Grid({ orientation: Gtk.Orientation.HORIZONTAL });
        frame.add(this._grid);

        this._grid.add(this._sourceView.widget);
        this._grid.add(this._typeView.widget);
        this._grid.add(this._matchView.widget);
        //this._grid.add(this._categoryView.widget);

        this.hide();
        this.widget.show_all();
    },
});
