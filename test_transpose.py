#!/usr/bin/env python3

import datetime
import unittest
from collections import namedtuple
from typing import NamedTuple

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_dtype, is_numeric_dtype
from pandas.testing import assert_frame_equal

import transpose
from cjwmodule.testing.i18n import cjwmodule_i18n_message, i18n_message

Column = namedtuple("Column", ("name", "type"))  # transpose ignores 'format'


class DefaultSettings(NamedTuple):
    MAX_COLUMNS_PER_TABLE: int = 1000
    MAX_BYTES_PER_COLUMN_NAME: int = 100


def render(table, firstcolname="", input_columns=None, settings=DefaultSettings()):
    def _infer_type(series):
        if is_numeric_dtype(series):
            return "number"
        elif is_datetime64_dtype(series):
            return "timestamp"
        else:
            return "text"

    def _infer_column(colname):
        return Column(colname, _infer_type(table[colname]))

    if input_columns is None:
        input_columns = {c: _infer_column(c) for c in table.columns}

    return transpose.render(
        table,
        {"firstcolname": firstcolname},
        input_columns=input_columns,
        settings=settings,
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
            result[0],
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

        self.assertEqual(
            result[1],
            [
                cjwmodule_i18n_message(
                    "util.colnames.warnings.numbered",
                    {"n_columns": 1, "first_colname": "b 2"},
                )
            ],
        )
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
            [
                cjwmodule_i18n_message(
                    "util.colnames.warnings.default",
                    {"n_columns": 2, "first_colname": "Column 4"},
                ),
                cjwmodule_i18n_message(
                    "util.colnames.warnings.numbered",
                    {"n_columns": 1, "first_colname": "Column 4"},
                ),
            ],
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
            result[0],
            pd.DataFrame({"A": ["B", "C"], "1": ["x", "3"], "2": ["y", "4"]}),
        )
        self.assertEqual(
            result[1],
            [
                {
                    "message": i18n_message(
                        "warnings.headersConvertedToText.message", {"column_name": "A"}
                    ),
                    "quickFixes": [
                        {
                            "text": i18n_message(
                                "warnings.headersConvertedToText.quickFix.text",
                                {"column_name": '"A"'},
                            ),
                            "action": "prependModule",
                            "args": ["converttotext", {"colnames": ["A"]}],
                        }
                    ],
                },
                {
                    "message": i18n_message(
                        "warnings.differentColumnTypes.message",
                        {"n_columns": 1, "first_colname": "C"},
                    ),
                    "quickFixes": [
                        {
                            "text": i18n_message(
                                "warnings.differentColumnTypes.quickFix.text",
                                {"n_columns": 1},
                            ),
                            "action": "prependModule",
                            "args": ["converttotext", {"colnames": ["C"]}],
                        }
                    ],
                },
            ],
        )

    def test_allow_max_n_columns(self):
        table = pd.DataFrame(
            {
                "A": ["a1", "a2", "a3"],
                "B": ["b1", "b2", "b3"],
            }
        )
        result = render(table, settings=DefaultSettings(MAX_COLUMNS_PER_TABLE=3))

        assert_frame_equal(
            result,
            pd.DataFrame(
                {
                    "A": ["B"],
                    "a1": ["b1"],
                    "a2": ["b2"],
                    "a3": ["b3"],
                }
            ),
        )

    def test_truncate_past_max_n_columns(self):
        table = pd.DataFrame(
            {
                "A": ["a1", "a2", "a3", "a4"],
                "B": ["b1", "b2", "b3", "b4"],
            }
        )
        result = render(table, settings=DefaultSettings(MAX_COLUMNS_PER_TABLE=3))

        assert_frame_equal(
            result[0],
            pd.DataFrame(
                {
                    "A": ["B"],
                    "a1": ["b1"],
                    "a2": ["b2"],
                    "a3": ["b3"],
                }
            ),
        )

        self.assertEqual(
            result[1],
            [i18n_message("warnings.tooManyRows", {"max_columns": 3})],
        )

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
        self.assertEqual(
            result[1],
            [
                cjwmodule_i18n_message(
                    "util.colnames.warnings.numbered",
                    {"n_columns": 1, "first_colname": "B 2"},
                )
            ],
        )
        assert_frame_equal(
            result[0], pd.DataFrame({"B": ["A"], "B 2": ["c"], "C": ["d"]})
        )


if __name__ == "__main__":
    unittest.main()
