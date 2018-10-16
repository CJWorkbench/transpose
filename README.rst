transpose
---------

Workbench module that converts rows to columns and columns to rows.

Features
--------

* The user may choose a column-header column. (The default is to name output
  columns '0', '1', etc.)
* Throws an error on duplicate column names by default. The user may override
  the error.
* Limits the output table to 1,000 columns.

Missing Features
----------------

* Transposed values will have mixed types, if input columns aren't all of the
  same type. Assume Workbench will sanitize this by converting everything to
  text; there is no way to control the format of said text. Workaround: the
  user can convert everything to text before transposing.
* Output column headers will be text. If the user chose a column-header column
  of another type, it will be converted to text but there is no way to control
  the format of said text. Workaround: the user can convert the column-header
  column to text before transposing.

Developing
----------

First, get up and running:

#. ``python3 ./setup.py test`` # to test

To add a feature:

#. Write a test in ``test_transpose.py``
#. Run ``python3 ./setup.py test`` to prove it breaks
#. Edit ``transpose.py`` to make the test pass
#. Run ``python3 ./setup.py test`` to prove it works
#. Commit and submit a pull request

To develop continuously on Workbench:

#. Check this code out in a sibling directory to your checked-out Workbench code
#. Start Workbench with ``CACHE_MODULES=false bin/dev start``
#. In a separate tab in the Workbench directory, run ``bin/dev develop-module transpose``
#. Edit this code; the module will be reloaded in Workbench immediately
