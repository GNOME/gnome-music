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

function getArtistView() {
    registerResources();

    const ArtistView = imports.view.Artists;
    const Toolbar = imports.toolbar;
    const Player = imports.player;
    let toolbar = new Toolbar.Toolbar();
    let player = new Player.Player();
    let stack = new Gtk.Stack();
    toolbar.set_stack(stack);
    let view = new ArtistView(toolbar, player);
    stack.add_titled(view, "Artists", "Artists");
    stack.set_visible_child_name('Artists');
    return view;
}

function testArtistsViewPlayback() {
    var Mainloop = imports.mainloop;
    const View = imports.view;
    const Widgets = imports.widgets;
    let artistView = getArtistView();

    artistView.connect("artist-added", Lang.bind(this, function(){
        //FIXME: Here we try to quit the mainloop for each album
        //this causes exceptions and should be handled correctly
        try {
            Mainloop.quit('artistAddedMainloop');
        } catch(Exception) {}
    }));
    Mainloop.run('artistAddedMainloop');
    // Loaded, ready to go

    // Check that no more than 50 and no less than 0 artists were loaded
    if (!(artistView._offset > 0 && artistView._offset < 51))
        fail('artistView._offset="'+artistView._offset +'"')

    // The album has title and artist displayed (not null values)
    let firstArtistIter = artistView._model.get_iter_first()[1];
    artistView._model.iter_next(firstArtistIter)
    let firstArtistPath = artistView._model.get_path(firstArtistIter);
    let artist = artistView._model.get_value(firstArtistIter, 0);
    log("  First artist is '"+artist+"'")
    assertNotNull(artist)

    // Select first artist, not 'All Artists'
    artistView.view.emit('item-activated', "0", firstArtistPath);
    let artistAlbumsWidget = artistView.artistAlbums;
    assertTrue(artistAlbumsWidget.widgets.length > 0);

    // Verify album title
    let artistAlbumWidget = artistAlbumsWidget.widgets[0];
    let albumTitle = artistAlbumWidget.album.get_title();
    assertNotNull(albumTitle);
    log("  First album is '" + albumTitle + "'")
    assertEquals(artistAlbumWidget.ui.get_object("title").get_label(), albumTitle);

    // Wait for all tracks to be added
    artistAlbumWidget.connect("tracks-loaded", Lang.bind(this, function(){
        Mainloop.quit('tracksLoadedMainloop');
    }));
    Mainloop.run('tracksLoadedMainloop');
    assertTrue(artistAlbumWidget.tracks.length > 0);
    let firstTrack = artistAlbumWidget.tracks[0];
    let trackTitle = firstTrack.get_title();
    log("  First track is '"+trackTitle+"'")

    let player = artistAlbumWidget.player;
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
    let model = artistAlbumWidget.model;
    let firstTrackIter = firstTrack.songWidget.iter;
    let firstTrackMarkup = model.get_value(firstTrackIter, 0);
    // Get songwidget and click on title
    firstTrack.songWidget.emit("button-release-event", null)

    // Wait for track to be played


    // Buttons become enabled
    //assertFalse(player.prevBtn.get_sensitive())
    //assertTrue(player.playBtn.get_sensitive())
    // TODO: Verify this only if artist has more than one song
    //assertTrue(player.nextBtn.get_sensitive())

    // Scale value is set to 0
    // This can't work everytime due to race conditions if the song starts playing before
    // reaching this assertion
    //assertEquals(player.progressScale.get_value(), 0)

    // Track markup is updated
    let newTrackMarkup = firstTrack.songWidget.title.get_label();
    assertEquals(newTrackMarkup, "<b>" + firstTrackMarkup + "</b>");

    // Nowplaying icon is displayed for this track
    assertTrue(firstTrack.songWidget.nowPlayingSign.get_visible())

    // Artist and track labels are updated
    assertEquals(player.artistLabel.get_label(), artist)
    assertEquals(player.titleLabel.get_label(), trackTitle)

    // Other tracks don't contain <b> or <span> and don't display now playing icon
    let tracksIter = firstTrackIter.copy();
    while(model.iter_next(tracksIter)) {
        let track = model.get_value(tracksIter, 5);
        let trackMarkup = track.songWidget.title.get_label();
        assertTrue(trackMarkup.indexOf("<b>") == -1)
        assertTrue(trackMarkup.indexOf("grey") == -1)
        assertFalse(track.songWidget.nowPlayingSign.get_visible())
    }
}

gjstestRun();
