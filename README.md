Music is the new GNOME music playing application.


# Where can I find more?

We have a wiki page at
https://wiki.gnome.org/Apps/Music

You can join us on the IRC:
#gnome-music on GIMPNet

# Join the development

Follow the guide at https://wiki.gnome.org/Newcomers/ and choose Music as your project.

# Coding style

GNOME Music is written in Python and aspires to adhere to the coding style described in the python style guide [PEP-8](https://www.python.org/dev/peps/pep-0008/).

Use of docstrings is recommended following [PEP-257](https://www.python.org/dev/peps/pep-0257/).

The content of docstrings uses the [Sphinx markup style](http://www.sphinx-doc.org/).

Use PyGI shorthands for manipulating GtkTreeModel:

```python
model[iter][0] = "artist"
artist, title = model[iter][1, 4]```