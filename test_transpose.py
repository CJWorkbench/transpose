#!/usr/bin/env python3

import datetime
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from transpose import render, MAX_N_COLUMNS

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
        result = render(table, {'firstcolname':''}) 

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
        result = render(table, {'firstcolname':'Fish'}) 

        assert_frame_equal(result, pd.DataFrame({
            'Fish': ['B', 'C'],
            'b': ['c', 'd'],
            'c': ['d', 'e'],
        }))

    def test_no_first_column_param(self):
        # Check operation with previous data version where there was no first col name param
        # Should keep existing column name
        table = pd.DataFrame({
            'A': ['b', 'c'],
            'B': ['c', 'd'],
            'C': ['d', 'e'],
        })
        result = render(table, {}) 

        assert_frame_equal(result, pd.DataFrame({
            'A': ['B', 'C'],
            'b': ['c', 'd'],
            'c': ['d', 'e'],
        }))        

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
            'A': ['b', 1, dt, None],
            'B': ['c', 'd', 'e', 'f'],
            'C': ['d', 'e', 'f', 'g'],
        })
        result = render(table, {})

        assert_frame_equal(result, pd.DataFrame({
            'A': ['B', 'C'],
            'b': ['c', 'd'],
            '1': ['d', 'e'],
            '2018-10-16 12:07:00': ['e', 'f'],
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
        result = render(table, {})

        self.assertEqual(result[1], (
            'We renamed some columns because the input column "A" had '
            'duplicate values.'
        ))
        assert_frame_equal(result[0], pd.DataFrame(
            [[ 'B', 'c', 'd' ],
             [ 'C', 'd', 'e' ]],
            columns=('A', 'b', 'b')
        ))

    def test_allow_max_n_columns(self):
        table = pd.DataFrame({
            'A': pd.Series(range(0, MAX_N_COLUMNS)),
            'B': pd.Series(range(0, MAX_N_COLUMNS)),
        })
        result = render(table, {})

        # Build expected result as a dictionary first
        d = {'A': ['B']}
        for i in range(0, MAX_N_COLUMNS):
            d[str(i)] = i

        assert_frame_equal(result, pd.DataFrame(d))

    def test_truncate_past_max_n_columns(self):
        table = pd.DataFrame({
            'A': pd.Series(range(0, MAX_N_COLUMNS + 1)),
            'B': pd.Series(range(0, MAX_N_COLUMNS + 1)),
        })
        result = render(table, {})

        # Build expected result as a dictionary first
        d = {'A': ['B']}
        for i in range(0, MAX_N_COLUMNS):
            d[str(i)] = i

        self.assertEqual(result[1], (
            f'We truncated the input to {MAX_N_COLUMNS} rows so the transposed '
            'table would have a reasonable number of columns.'
        ))
        assert_frame_equal(result[0], pd.DataFrame(d))
