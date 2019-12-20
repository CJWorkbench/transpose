#!/usr/bin/env python3

from collections import namedtuple
import datetime
import unittest
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
from pandas.testing import assert_frame_equal
import transpose


Column = namedtuple("Column", ("name", "type"))  # transpose ignores 'format'


def render(table, firstcolname="", input_columns=None):
    def _infer_type(series):
        if is_numeric_dtype(series):
            return "number"
        elif is_datetime64_dtype(series):
            return "datetime"
        else:
            return "text"

    def _infer_column(colname):
        return Column(colname, _infer_type(table[colname]))

    if input_columns is None:
        input_columns = {c: _infer_column(c) for c in table.columns}

    return transpose.render(
        table, {"firstcolname": firstcolname}, input_columns=input_columns
    )


class MigrateParamsTest(unittest.TestCase):
    def test_v0(self):
        self.assertEqual(transpose.migrate_params({}), {"firstcolname": ""})

    def test_v1(self):
        # as of 2019-02-11
        self.assertEqual(
            transpose.migrate_params({"firstcolname": "A"}), {"firstcolname": "A"}
        )


class RenderTest(unittest.TestCase):
    def test_normal(self):
        #     A  B  C
        #  0  b  c  d
        #  1  c  d  e
        #
        # Transposed (with A as headers) becomes:
        #
        #          A  b  c
        #  0       B  c  d
        #  1       C  d  e
        table = pd.DataFrame({"A": ["b", "c"], "B": ["c", "d"], "C": ["d", "e"]})
        result = render(table)

        assert_frame_equal(
            result, pd.DataFrame({"A": ["B", "C"], "b": ["c", "d"], "c": ["d", "e"]})
        )

    def test_rename_first_column(self):
        # As above, but with a user supplied first column name

        table = pd.DataFrame({"A": ["b", "c"], "B": ["c", "d"], "C": ["d", "e"]})
        result = render(table, "Fish")

        assert_frame_equal(
            result, pd.DataFrame({"Fish": ["B", "C"], "b": ["c", "d"], "c": ["d", "e"]})
        )

    def test_empty_input(self):
        table = pd.DataFrame()
        result = render(table)
        assert_frame_equal(result, pd.DataFrame())

    def test_empty_input_with_columns(self):
        table = pd.DataFrame({"A": [], "B": []}, dtype=object)
        result = render(table)
        assert_frame_equal(result, pd.DataFrame({"A": ["B"]}))

    def test_colnames_to_str(self):
        #     A   B  C
        #  0  b   c  d
        #  1  1   d  e
        #  2  dt  e  f
        #  3  na  f  g
        #
        # Transposed (with A as headers) becomes:
        #
        #     Column  b  1  dt  unnamed
        #  0       B  c  d   e        f
        #  1       C  d  e   f        g

        dt = datetime.datetime(2018, 10, 16, 12, 7)
        table = pd.DataFrame(
            {
                "A": [1.1, 2.2, 3.3, None],
                "B": ["c", "d", "e", "f"],
                "C": ["d", "e", "f", "g"],
            }
        )
        result = render(table)

        assert_frame_equal(
            result["dataframe"],
            pd.DataFrame(
                {
                    "A": ["B", "C"],
                    "1.1": ["c", "d"],
                    "2.2": ["d", "e"],
                    "3.3": ["e", "f"],
                    "Column 5": ["f", "g"],
                }
            ),
        )

    def test_warn_and_rename_on_duplicates(self):
        #     A  B  C
        #  0  b  c  d
        #  1  b  d  e
        #
        # Transposed (with header A, allowing duplicates) becomes:
        #
        #     Column  b  b
        #  0       B  c  d
        #  1       C  d  e
        table = pd.DataFrame({"A": ["b", "b"], "B": ["c", "d"], "C": ["d", "e"]})
        result = render(table)

        self.assertEqual(result[1], "Renamed 1 duplicate column names (see “b 2”)")
        assert_frame_equal(
            result[0],
            pd.DataFrame({"A": ["B", "C"], "b": ["c", "d"], "b 2": ["d", "e"]}),
        )

    def test_warn_and_rename_on_empty_and_unnamed_colname(self):
        table = pd.DataFrame(
            {"A": ["x", "", "Column 3", np.nan], "B": ["b1", "b2", "b3", "b4"]}
        )
        result = render(table)
        self.assertEqual(
            result[1],
            "\n".join(
                [
                    "Renamed 2 column names (because values were empty; see “Column 4”)",
                    "Renamed 1 duplicate column names (see “Column 4”)",
                ]
            ),
        )
        assert_frame_equal(
            result[0],
            pd.DataFrame(
                {
                    "A": ["B"],
                    "x": ["b1"],
                    "Column 4": ["b2"],
                    "Column 3": ["b3"],
                    "Column 5": ["b4"],
                }
            ),
        )

    def test_warn_on_convert_to_str_including_column_header(self):
        table = pd.DataFrame({"A": [1, 2], "B": ["x", "y"], "C": [3, 4]})
        result = render(table)
        assert_frame_equal(
            result["dataframe"],
            pd.DataFrame({"A": ["B", "C"], "1": ["x", "3"], "2": ["y", "4"]}),
        )
        self.assertEqual(
            result["error"],
            (
                'Headers in column "A" were auto-converted to text.\n'
                'Column "C" was auto-converted to Text because all columns must '
                "have the same type."
            ),
        )
        self.assertEqual(
            result["quick_fixes"],
            [
                {
                    "text": 'Convert "A", "C" to text',
                    "action": "prependModule",
                    "args": ["converttotext", {"colnames": ["A", "C"]}],
                }
            ],
        )

    def test_allow_max_n_columns(self):
        table = pd.DataFrame(
            {
                "A": pd.Series(
                    [
                        chr(x + 100)
                        for x in range(transpose.settings.MAX_COLUMNS_PER_TABLE)
                    ]
                ),
                "B": pd.Series(
                    [
                        chr(x + 120)
                        for x in range(transpose.settings.MAX_COLUMNS_PER_TABLE)
                    ]
                ),
            }
        )
        result = render(table)

        # Build expected result as a dictionary first
        d = {"A": ["B"]}
        for i in range(0, transpose.settings.MAX_COLUMNS_PER_TABLE):
            d[chr(i + 100)] = chr(i + 120)

        assert_frame_equal(result, pd.DataFrame(d))

    def test_truncate_past_max_n_columns(self):
        table = pd.DataFrame(
            {
                "A": pd.Series(
                    [
                        str(x)
                        for x in range(transpose.settings.MAX_COLUMNS_PER_TABLE + 1)
                    ]
                ),
                "B": pd.Series(
                    [
                        str(x + 1000)
                        for x in range(transpose.settings.MAX_COLUMNS_PER_TABLE + 1)
                    ]
                ),
            }
        )
        result = render(table)

        self.assertEqual(
            result[1],
            (
                f"We truncated the input to {transpose.settings.MAX_COLUMNS_PER_TABLE} rows so the "
                "transposed table would have a reasonable number of columns."
            ),
        )
        # Build expected result as a dictionary first
        d = {"A": ["B"]}
        for i in range(transpose.settings.MAX_COLUMNS_PER_TABLE):
            d[str(i)] = str(i + 1000)

        assert_frame_equal(result[0], pd.DataFrame(d))

    def test_transpose_categorical_and_rename_index(self):
        # Avoid TypeError: cannot insert an item into a CategoricalIndex
        # that is not already an existing category
        #
        # Akin to https://github.com/pandas-dev/pandas/issues/19136
        #
        # Column names should strings, not a CategoricalIndex.
        table = pd.DataFrame(
            {
                "A": pd.Series(["a1", "a2"], dtype="category"),  # becomes ret.columns
                "B": pd.Series(["b1", "b2"]),
            }
        )
        result = render(table, firstcolname="X")
        assert_frame_equal(
            result, pd.DataFrame({"X": ["B"], "a1": ["b1"], "a2": ["b2"]})
        )

    def test_warn_and_rename_column_if_firstcolname_conflicts(self):
        table = pd.DataFrame({"X": ["B", "C"], "A": ["c", "d"]})
        result = render(table, firstcolname="B")
        self.assertEqual(result[1], "Renamed 1 duplicate column names (see “B 2”)")
        assert_frame_equal(
            result[0], pd.DataFrame({"B": ["A"], "B 2": ["c"], "C": ["d"]})
        )


if __name__ == "__main__":
    unittest.main()
