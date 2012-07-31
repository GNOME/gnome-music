/*
 * Copyright (C) 2012 Cesar Garcia Tapia <tapia@openshine.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

private enum Music.UIState {
    NONE,
    COLLECTION,
    CREDS,
    DISPLAY,
    SETTINGS,
    WIZARD,
    PROPERTIES
}

private abstract class Music.UI: GLib.Object {
    protected UIState previous_ui_state;
    private UIState _ui_state;
    [CCode (notify = false)]
        public UIState ui_state {
            get { return _ui_state; }
            set {
                if (_ui_state != value) {
                    previous_ui_state = _ui_state;
                    _ui_state = value;
                    ui_state_changed ();
                    notify_property ("ui-state");
                }
            }
        }

    public abstract void ui_state_changed ();
}

