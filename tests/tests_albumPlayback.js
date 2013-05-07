// application/javascript;version=1.8
if (!('assertEquals' in this)) { /* allow running this test standalone */
    imports.lang.copyPublicProperties(imports.jsUnit, this);
    gjstestRun = function() { return imports.jsUnit.gjstestRun(window); };
}

imports.searchPath.unshift('..');
imports.searchPath.unshift('../src');
imports.searchPath.unshift('../libgd');
imports.searchPath.unshift('../data');
const Gio = imports.gi.Gio;
const Gtk = imports.gi.Gtk;
const Gdk = imports.gi.Gdk;
const Lang = imports.lang;


function registerResources() {
    let resource = Gio.Resource.load('../data/gnome-music.gresource');
    resource._register();

    let cssFile = Gio.File.new_for_uri('resource:///org/gnome/music/application.css');
    let provider = new Gtk.CssProvider();
    provider.load_from_file(cssFile);
    Gtk.init(null, 0);
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),
                                             provider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION);
}

function getAlbumView() {
    registerResources();

    const AlbumView = imports.view.Albums;
    const Toolbar = imports.toolbar;
    const Player = imports.player;
    let toolbar = new Toolbar.Toolbar();
    let player = new Player.Player();
    return new AlbumView(toolbar, player);
}

function testAlbumViewPlayback() {
    var Mainloop = imports.mainloop;
    const View = imports.view;
    const Widgets = imports.widgets;
    let albumView = getAlbumView();
    // Wait for albums to load, run mainloop
    albumView.connect("album-art-updated", Lang.bind(this, function(){
        //FIXME: Here we try to quit the mainloop for each album
        //this causes exceptions and should be handled correctly
        try {
            Mainloop.quit('testMainloop');
        } catch(Exception) {}
    }));
    Mainloop.run('testMainloop');
    // Loaded, ready to go

    // Check that no more than 50 and no less than 0 albums were loaded
    if (!(albumView._offset > 0 && albumView._offset < 51))
        fail('albumView._offset="'+albumView._offset +'"')

    // The album has title and artist displayed (not null values)
    let firstAlbumIter = albumView._model.get_iter_first()[1];
    let firstAlbumPath = albumView._model.get_path(firstAlbumIter);
    let album = albumView._model.get_value(firstAlbumIter, 2);
    let artist = albumView._model.get_value(firstAlbumIter, 3);
    log("  First album is '"+album+"' by '"+artist+"'")
    assertNotNull(album)
    assertNotNull(artist)

    // Select first album
    let albumWidget = albumView._albumWidget;
    albumWidget.connect("loaded", Lang.bind(this, function(){
        Mainloop.quit('testMainloop');
    }));
    Mainloop.idle_add(function() {
        albumView.view.emit('item-activated', "0", firstAlbumPath);
    })
    Mainloop.run('testMainloop');
    // Album view loaded

    // Make sure that the same artist and album are displayed
    let artist2 = albumWidget.ui.get_object("artist_label").label;
    assertEquals(artist, artist2)
    let album2 = albumWidget.ui.get_object("title_label").label;
    assertEquals(album, album2)

    // Make sure that year is either ---- or more that 1000 (at least)
    let year = albumWidget.ui.get_object("released_label_info").label;
    if (year != '----')
        assertTrue(year > 1000)

    // Wait for tracks to be added
    albumWidget.connect('track-added', Lang.bind(this, function(){
        Mainloop.quit('testMainloop');
    }))
    Mainloop.run('testMainloop');

    // FIXME: wait for all tracks to be added, for now operate on the first one
    let model = albumWidget.model;
    let iter = model.get_iter_first()[1];
    let title = model.get_value(iter, 0);
    assertNotNull(title);
    assertEquals(title, model.get_value(iter, 5).get_title())
    log("  First track is '"+title+"'")

    // Buttons are disabled
    let player = albumWidget.player;
    assertFalse(player.prevBtn.get_sensitive())
    assertFalse(player.playBtn.get_sensitive())
    assertFalse(player.nextBtn.get_sensitive())

    // Artist and track labels are empty
    assertEquals(player.artistLabel.get_label(), "")
    assertEquals(player.titleLabel.get_label(), "")

    // Progress scale is not initialized (undefined range)
    assertEquals(player.progressScale.range, undefined)

    // Duration labels are set to "00:00"
    assertEquals(player.songTotalTimeLabel.get_label(), "00:00")
    assertEquals(player.songPlaybackTimeLabel.get_label(), "00:00")

    // Select the first song and remember its markup
    let firstTrackIter = albumWidget.model.get_iter_first()[1];
    let firstTrackMarkup = albumWidget.model.get_value(firstTrackIter, 0);
    let firstTrackPath = albumWidget.model.get_path(firstTrackIter);
    albumWidget.view.emit("item-activated", "0", firstTrackPath);

    // Buttons become enabled
    assertFalse(player.prevBtn.get_sensitive())
    assertTrue(player.playBtn.get_sensitive())
    assertTrue(player.nextBtn.get_sensitive())

    // Scale value is set to 0
    assertEquals(player.progressScale.get_value(), 0)

    // Track markup is updated
    let newTrackMarkup = albumWidget.model.get_value(firstTrackIter, 0);
    assertEquals(newTrackMarkup, "<b>" + firstTrackMarkup + "</b>");

    // Nowplaying icon is displayed for this track
    assertTrue(albumWidget.model.get_value(firstTrackIter, 3))

    // Artist and track labels are updated
    assertEquals(player.artistLabel.get_label(), artist)
    assertEquals(player.titleLabel.get_label(), title)

    // Other tracks don't contain <b> or <span> and don't display now playing icon
    let tracksIter = firstTrackIter.copy();
    while(albumWidget.model.iter_next(tracksIter)) {
        let trackMarkup = albumWidget.model.get_value(tracksIter, 0);
        assertTrue(trackMarkup.indexOf("<b>") == -1)
        assertTrue(trackMarkup.indexOf("<span>") == -1)
        assertFalse(albumWidget.model.get_value(tracksIter, 3))
    }
}

gjstestRun();
