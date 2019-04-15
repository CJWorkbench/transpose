#!/usr/bin/env python3

from collections import namedtuple
import datetime
import unittest
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
from pandas.testing import assert_frame_equal
import transpose


Column = namedtuple('Column', ('name', 'type'))  # transpose ignores 'format'


def render(table, firstcolname='', input_columns=None):
    def _infer_type(series):
        if is_numeric_dtype(series):
            return 'number'
        elif is_datetime64_dtype(series):
            return 'datetime'
        else:
            return 'text'

    def _infer_column(colname):
        return Column(colname, _infer_type(table[colname]))

    if input_columns is None:
        input_columns = {c: _infer_column(c) for c in table.columns}

    return transpose.render(
        table,
        {'firstcolname': firstcolname},
        input_columns=input_columns
    )


class TransposeTest(unittest.TestCase):
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
        table = pd.DataFrame({
            'A': ['b', 'c'],
            'B': ['c', 'd'],
            'C': ['d', 'e'],
        })
        result = render(table)

        assert_frame_equal(result, pd.DataFrame({
            'A': ['B', 'C'],
            'b': ['c', 'd'],
            'c': ['d', 'e'],
        }))

    def test_rename_first_column(self):
        # As above, but with a user supplied first column name

        table = pd.DataFrame({
            'A': ['b', 'c'],
            'B': ['c', 'd'],
            'C': ['d', 'e'],
        })
        result = render(table, 'Fish')

        assert_frame_equal(result, pd.DataFrame({
            'Fish': ['B', 'C'],
            'b': ['c', 'd'],
            'c': ['d', 'e'],
        }))

    def test_empty_input(self):
        table = pd.DataFrame()
        result = render(table)
        assert_frame_equal(result, pd.DataFrame())

    def test_empty_input_with_columns(self):
        table = pd.DataFrame({'A': [], 'B': []}, dtype=object)
        result = render(table)
        assert_frame_equal(result, pd.DataFrame({'A': ['B']}))

    def test_colnames_to_str(self):
        #     A   B  C
        #  0  b   c  d
        #  1  1   d  e
        #  2  dt  e  f
        #  3  na  f  g
        #
        # Transposed (with A as headers) becomes:
        #
        #     Column  b  1  dt  ''
        #  0       B  c  d   e   f
        #  1       C  d  e   f   g

        dt = datetime.datetime(2018, 10, 16, 12, 7)
        table = pd.DataFrame({
            'A': [1.1, 2.2, 3.3, None],
            'B': ['c', 'd', 'e', 'f'],
            'C': ['d', 'e', 'f', 'g'],
        })
        result = render(table)

        assert_frame_equal(result['dataframe'], pd.DataFrame({
            'A': ['B', 'C'],
            '1.1': ['c', 'd'],
            '2.2': ['d', 'e'],
            '3.3': ['e', 'f'],
            '': ['f', 'g'],
        }))

    def test_warn_on_duplicates(self):
        #     A  B  C
        #  0  b  c  d
        #  1  b  d  e
        #
        # Transposed (with header A, allowing duplicates) becomes:
        #
        #     Column  b  b
        #  0       B  c  d
        #  1       C  d  e
        table = pd.DataFrame({
            'A': ['b', 'b'],
            'B': ['c', 'd'],
            'C': ['d', 'e'],
        })
        result = render(table)

        self.assertEqual(result[1], (
            'We renamed some columns because the input column "A" had '
            'duplicate values.'
        ))
        assert_frame_equal(result[0], pd.DataFrame(
            [['B', 'c', 'd'],
             ['C', 'd', 'e']],
            columns=('A', 'b', 'b')
        ))

    def test_warn_on_convert_to_str_including_column_header(self):
        table = pd.DataFrame({'A': [1, 2], 'B': ['x', 'y'], 'C': [3, 4]})
        result = render(table)
        assert_frame_equal(
            result['dataframe'],
            pd.DataFrame({'A': ['B', 'C'], '1': ['x', '3'], '2': ['y', '4']})
        )
        self.assertEqual(result['error'], (
            'Headers in column "A" were auto-converted to text.\n'
            'Column "C" was auto-converted to Text because all columns must '
            'have the same type.'
        ))
        self.assertEqual(result['quick_fixes'], [{
            'text': 'Convert "A", "C" to text',
            'action': 'prependModule',
            'args': ['converttotext', {'colnames': 'A,C'}],
        }])

    def test_allow_max_n_columns(self):
        table = pd.DataFrame({
            'A': pd.Series([chr(x + 100)
                            for x in range(transpose.MAX_N_COLUMNS)]),
            'B': pd.Series([chr(x + 120)
                            for x in range(transpose.MAX_N_COLUMNS)]),
        })
        result = render(table)

        # Build expected result as a dictionary first
        d = {'A': ['B']}
        for i in range(0, transpose.MAX_N_COLUMNS):
            d[chr(i + 100)] = chr(i + 120)

        assert_frame_equal(result, pd.DataFrame(d))

    def test_truncate_past_max_n_columns(self):
        table = pd.DataFrame({
            'A': pd.Series([chr(x + 100)
                            for x in range(transpose.MAX_N_COLUMNS + 1)]),
            'B': pd.Series([chr(x + 123)
                            for x in range(transpose.MAX_N_COLUMNS + 1)]),
        })
        result = render(table)

        self.assertEqual(result[1], (
            f'We truncated the input to {transpose.MAX_N_COLUMNS} rows so the '
            'transposed table would have a reasonable number of columns.'
        ))
        # Build expected result as a dictionary first
        d = {'A': ['B']}
        for i in range(transpose.MAX_N_COLUMNS):
            d[chr(i + 100)] = chr(i + 123)

        assert_frame_equal(result[0], pd.DataFrame(d))


if __name__ == '__main__':
    unittest.main()
