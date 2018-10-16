#!/usr/bin/env python3

import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from transpose import Form, render, transpose, MAX_N_COLUMNS

class TransposeTest(unittest.TestCase):
    def test_with_no_colname(self):
        #     A  B  C
        #  0  b  c  d
        #  1  c  d  e
        #
        # Transposed with no column as headers becomes:
        #
        #     Column  0  1
        #  0       A  b  c
        #  1       B  c  d
        #  2       C  d  e
        table = pd.DataFrame({
            'A': ['b', 'c'],
            'B': ['c', 'd'],
            'C': ['d', 'e'],
        })
        form = Form.parse(header_colname=None)
        result = transpose(table, form)

        assert_frame_equal(result, pd.DataFrame({
            'Column': ['A', 'B', 'C'],
            '0': ['b', 'c', 'd'],
            '1': ['c', 'd', 'e'],
        }))


    def test_with_header_colname(self):
        #     A  B  C
        #  0  b  c  d
        #  1  c  d  e
        #
        # Transposed with A as headers becomes:
        #
        #     Column  b  c
        #  0       B  c  d
        #  1       C  d  e

        table = pd.DataFrame({
            'A': ['b', 'c'],
            'B': ['c', 'd'],
            'C': ['d', 'e'],
        })
        form = Form.parse(header_colname='A')
        result = transpose(table, form)

        assert_frame_equal(result, pd.DataFrame({
            'Column': ['B', 'C'],
            'b': ['c', 'd'],
            'c': ['d', 'e'],
        }))

    def test_dup_not_allowed(self):
        #     A  B
        #  0  b  c
        #  1  b  d
        #
        # Transposed with A as headers becomes error because there would be two
        # columns with the same name.

        table = pd.DataFrame({
            'A': ['b', 'b'],
            'B': ['c', 'd'],
        })
        form = Form.parse(header_colname='A', allow_duplicates=False)
        result = transpose(table, form)

        self.assertEqual(result, (
            'Column "A" has duplicated values, so transposing by it would '
            'create duplicate column names. Please confirm you want this.'
        ))

    def test_dup_allowed_by_override(self):
        #     A  B  C
        #  0  b  c  d
        #  1  b  d  e
        #
        # Transposed with header A, allowing duplicates, becomes:
        #
        #     Column  b  b
        #  0       B  c  d
        #  1       C  d  e


        table = pd.DataFrame({
            'A': ['b', 'b'],
            'B': ['c', 'd'],
            'C': ['d', 'e'],
        })
        form = Form.parse(header_colname='A', allow_duplicates=True)
        result = transpose(table, form)

        assert_frame_equal(result, pd.DataFrame(
            [[ 'B', 'c', 'd' ],
             [ 'C', 'd', 'e' ]],
            columns=('Column', 'b', 'b')
        ))

    def test_allow_max_n_columns(self):
        table = pd.DataFrame({'A': pd.Series(range(0, MAX_N_COLUMNS))})
        form = Form.parse(header_colname=None)
        result = transpose(table, form)

        # Build expected result as a dictionary first
        d = {'Column': ['A']}
        for i in range(0, MAX_N_COLUMNS):
            d[str(i)] = i

        assert_frame_equal(result, pd.DataFrame(d))

    def test_disallow_past_max_n_columns(self):
        table = pd.DataFrame({'A': pd.Series(range(0, MAX_N_COLUMNS + 1))})
        form = Form.parse(header_colname=None)
        result = transpose(table, form)

        # Build expected result as a dictionary first
        d = {'Column': ['A']}
        for i in range(0, MAX_N_COLUMNS):
            d[str(i)] = i

        assert_frame_equal(result[0], pd.DataFrame(d))
        self.assertEqual(result[1], (
            'We truncated the input to 999 rows so the transposed table would '
            'have a reasonable number of columns.'
        ))
