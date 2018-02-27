Music is the new GNOME music playing application.

# Where can I find more?

Music has a wiki page at
https://wiki.gnome.org/Apps/Music (outdated).

You can join the developers on IRC: [#gnome-music](irc://irc.gnome.org/gnome-music) on [GIMPNet](https://wiki.gnome.org/Community/GettingInTouch/IRC).

# Join the development

Follow the guide at https://wiki.gnome.org/Newcomers/ and choose Music as your project. There are bugs labeled for newcomers, which should provide an easy entry point. Of course, feel free to pick something more challenging. Pick bugs if you can, the goal is to make the current Music experience sound & stable and only then extend it's functionality.

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

# Coding style

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

### PyGI specific

Use PyGI shorthands for manipulating `GtkTreeModel` & `GtkListStore`:
```python
model[iter][0] = "artist"
artist, title = model[iter][1, 4]
```
