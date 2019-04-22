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
* Warns and converts all output to str if input has mixed types.
* Converts output column names to text, even if the first column is int.

Missing Features
----------------

* Type conversion does not respect column formats. (It just uses ``str()``.)
  A warning lets the user prepend a "Convert to Text" module to correct any
  errors.

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
#. Start Workbench with ``bin/dev start``
#. In a separate tab in the Workbench directory, run ``bin/dev develop-module transpose``
#. Edit this code; the module will be reloaded in Workbench immediately
