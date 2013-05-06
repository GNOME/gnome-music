// application/javascript;version=1.8
if (!('assertEquals' in this)) { /* allow running this test standalone */
    imports.lang.copyPublicProperties(imports.jsUnit, this);
    gjstestRun = function() { return imports.jsUnit.gjstestRun(window); };
}

imports.searchPath.unshift('..');
imports.searchPath.unshift('../src');
imports.searchPath.unshift('../libgd');
imports.searchPath.unshift('../data');
const AlbumArtCache = imports.src.albumArtCache.AlbumArtCache
const GLib = imports.gi.GLib;
const Lang = imports.lang;


function _hash(input) {
    return GLib.compute_checksum_for_string(GLib.ChecksumType.MD5, input, -1);
}

function testNormalizeAndHash_SmokeTest() {
    let albumArtCache = new AlbumArtCache();
    assertEquals(_hash("test"), albumArtCache.normalizeAndHash("test"))
}

function testNormalizeAndHash_NullInput() {
    let albumArtCache = new AlbumArtCache();
    assertEquals(_hash(" "), albumArtCache.normalizeAndHash(""))
    assertEquals(_hash(" "), albumArtCache.normalizeAndHash(null))
    assertEquals(_hash(" "), albumArtCache.normalizeAndHash(undefined))
}

function testNormalizeAndHash_Lowercased() {
    let albumArtCache = new AlbumArtCache();
    assertEquals(_hash("test"), albumArtCache.normalizeAndHash("TEST"))
}

function testNormalizeAndHash_UTF8() {
    let albumArtCache = new AlbumArtCache();
    assertEquals(_hash("Неизвестный артист"),
                 albumArtCache.normalizeAndHash("Неизвестный артист", true))
}

function testStripInvalidEntries_SmokeTest() {
    let albumArtCache = new AlbumArtCache();
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unknown Artist"))
}

function testStripInvalidEntries_Symbols() {
    let albumArtCache = new AlbumArtCache();
    //Percent and semicolon are not filtered, why?
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unknown_!@#$^&*+=| Artist"))
}

function testStripInvalidEntries_Slashes() {
    let albumArtCache = new AlbumArtCache();
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unknown\\ Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unknown\ Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unk//nown Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unk/nown Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unk\/nown Artist"))
}

function testStripInvalidEntries_Brackets() {
    let albumArtCache = new AlbumArtCache();
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Un(known) Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("[Un]known Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("<Un>known Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("{Un}known Artist"))
}

function testStripInvalidEntries_Spaces() {
    let albumArtCache = new AlbumArtCache();
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unknown  Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unknown   Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("<Unknown>  Artist"))
    assertEquals('Unknown Artist', albumArtCache.stripInvalidEntities("Unknown^^@(*  ) Artist"))
}

gjstestRun();
