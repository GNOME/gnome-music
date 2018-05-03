Music is the new GNOME music playing application.

# Where can I find more?

Music has a wiki page at
https://wiki.gnome.org/Apps/Music.

You can join the developers on IRC: [#gnome-music](irc://irc.gnome.org/gnome-music) on [GIMPNet](https://wiki.gnome.org/Community/GettingInTouch/IRC).

# Join the development

Follow the [GNOME Newcomers guide](https://wiki.gnome.org/Newcomers/) and choose Music as your project. There are bugs labeled for newcomers, which should provide an easy entry point. Of course, feel free to pick something more challenging. Pick bugs if you can, not feature requests. The goal is to make the current Music experience sound & stable and only then extend it's functionality.

### Build Music

Music uses the [meson](http://mesonbuild.com/) build system. Use the following commands to build Music from the source directory:

```sh
$ meson _build
$ cd _build
$ ninja
```

Then you can either run in the build dir by running:

```sh
$ ./local-music
```

You can also install Music system-wide by running:

```sh
$ ninja install
```

## Coding style

GNOME Music is written in Python and aspires to adhere to the coding style described in the python style guide [PEP-8](https://www.python.org/dev/peps/pep-0008/).

Since Music was written over many years and by many different contributors without a single style being enforced, it currently is in a mixed style state. The goal is to eventually consistently follow  [PEP-8](https://www.python.org/dev/peps/pep-0008/) for style and [PEP-257](https://www.python.org/dev/peps/pep-0257/) for docstrings. The content of docstrings uses the [Sphinx markup style](http://www.sphinx-doc.org/).

Docstrings should be added to all (new) public functions.

Since looking at the surrounding code might give mixed results, take note of the following rules as a basic style guide.

### Line length

>>>
Limit all lines to a maximum of 79 characters.

For flowing long blocks of text with fewer structural restrictions (docstrings or comments), the line length should be limited to 72 characters.
>>>

### Indentation

Music uses hanging indents when the lines get too long.

>>>
When using a hanging indent the following should be considered; there should be no arguments on the first line and further indentation should be used to clearly distinguish itself as a continuation line.
>>>

```python
# More indentation included to distinguish this from the rest.
def long_function_name(
        var_one, var_two, var_three,
        var_four):
    print(var_one)

# Hanging indents should add a level.
foo = long_function_name(
    var_one, var_two,
    var_three, var_four)
```

### Line break before a binary operator

```python
# Yes: easy to match operators with operands
income = (gross_wages
          + taxable_interest
          + (dividends - qualified_dividends)
          - ira_deduction
          - student_loan_interest)

# Add some extra indentation on the conditional continuation line.
if (this_is_one_thing
        and that_is_another_thing):
    do_something()
```

### Class internals

All non-public classwide variables or methods should be prepended with an underscore.
>>>
_single_leading_underscore: weak "internal use" indicator. E.g. from M import * does not import objects whose name starts with an underscore.
>>>

### PyGObject specifics

#### Treemodel

Use PyGObject shorthands for manipulating `GtkTreeModel` & `GtkListStore`:

```python
model[iter][0] = "artist"
artist, title = model[iter][1, 4]
```

#### Properties

Most objects in Music are derived from GObject and have properties. Use [PyGObject properties](https://pygobject.readthedocs.io/en/latest/guide/api/properties.html) through decorator usage if you add properties to your code.

Short form for simple properties:

```python
selected = GObject.Property(type=bool, default=False)
```

With method definition if more control is needed:

```python
@GObject.Property(type=bool, default=False)
def selection_mode(self):
    return self._selection_mode

@selection_mode.setter
def selection_mode(self, value):
    self._selection_mode = value
```

Manipulate and refer to GObject properties with the *props* attribute to set them apart from regular python attributes:

```python
is_selected = object.props.selected

object.props.selection_mode = True
```

##### Multi-word properties

Note that GObject multi-word properties are separated by `-` as in `'selection-mode'`, however Python does not allow `-` in variable or method names. So these are translated to `_` instead. You might find both `'selection-mode'` and `selection_mode` in the code (depending on how they are used), but they refer to the same property.

#### Templates

Recent PyGObject (3.29.1 and up) allows template usage and Music is [starting to convert](https://gitlab.gnome.org/GNOME/gnome-music/issues/183) to using this to build the user interface. More information can be found in the PyGObject source and [examples](https://gitlab.gnome.org/GNOME/gnome-music/blob/master/gnomemusic/widgets/songwidget.py) in the Music code.

The basic usage in Python is as follows, with the `widget.ui` file being a regular GTK template:

```python
@Gtk.Template(resource_path='/org/gnome/Music/widget.ui')
class Widget(Gtk.Widget):

    __gtype_name__ = 'Widget'

    _button = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def _on_button_clicked(self, klass):
        pass
```

## Commit messages

Music is fairly strict on the format and contents of commit messages. New contributors often struggle with this.

The GNOME wiki has a good [intro](https://wiki.gnome.org/Git/CommitMessages) on what a proper commit message is and this is a **must read** for first-time contributors.

It is always recommended to look at other Music commit messages as well to get an idea of what a good commit message is specific to Music.

It should look somewhat like:

>>>
tag: Short explanation

Problem in some detail.
Implemented fix.

Closes: #issuenr
>>>