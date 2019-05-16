import numpy as np
import pandas as pd
from typing import Iterator, Set


MAX_N_COLUMNS = 99


def _uniquize_colnames(colnames: Iterator[str],
                       never_rename_to: Set[str]) -> Iterator[str]:
    """
    Rename columns to prevent duplicates or empty column names.

    The algorithm: iterate over each `colname` and add to an internal "seen".
    When we encounter a colname we've seen, append " 1", " 2", " 3", etc. to it
    until we encounter a colname we've never seen that is not in
    `never_rename_to`.
    """
    seen = set()
    for colname in colnames:
        force_add_number = False
        if not colname:
            colname = 'unnamed'
            force_add_number = 'unnamed' in never_rename_to
        if colname in seen or force_add_number:
            for i in range(1, 999999):
                try_colname = f'{colname} {i}'
                if (
                    try_colname not in seen
                    and try_colname not in never_rename_to
                ):
                    colname = try_colname
                    break

        seen.add(colname)
        yield colname


def render(table, params, *, input_columns):
    warnings = []
    colnames_auto_converted_to_text = []

    if len(table) > MAX_N_COLUMNS:
        table = table.truncate(after=MAX_N_COLUMNS - 1)
        warnings.append(
            f'We truncated the input to {MAX_N_COLUMNS} rows so the '
            'transposed table would have a reasonable number of columns.'
        )

    if not len(table.columns):
        # happens if we're the first module in the module stack
        return pd.DataFrame()

    # If user does not supply a name (default), use the input table's first
    # column name as the output table's first column name.
    first_colname = params['firstcolname'].strip() or table.columns[0]

    column = table.columns[0]
    headers_series = table[column]
    table.drop(column, axis=1, inplace=True)

    # Ensure headers are string. (They will become column names.)
    if input_columns[column].type != 'text':
        warnings.append(f'Headers in column "A" were auto-converted to text.')
        colnames_auto_converted_to_text.append(column)

    # Regardless of column type, we want to convert to str. This catches lots
    # of issues:
    #
    # * Column names shouldn't be a CategoricalIndex; that would break other
    #   Pandas functions. See https://github.com/pandas-dev/pandas/issues/19136
    # * nulls should be converted to '' instead of 'nan'
    # * Non-str should be converted to str
    # * `first_colname` will be the first element (so we can enforce its
    #   uniqueness).
    #
    # After this step, `headers` will be a List[str]. "" is okay for now: we'll
    # catch that later.
    na = headers_series.isna()
    headers_series = headers_series.astype(str)
    headers_series[na] = ''  # Empty values are all equivalent
    headers_series[headers_series.isna()] = ''
    headers = headers_series.tolist()
    headers.insert(0, first_colname)
    non_empty_headers = [h for h in headers if h]

    # unique_headers: all the "valuable" header names -- the ones we won't
    # rename any duplicate/empty headers to.
    unique_headers = set(headers)

    if '' in unique_headers:
        warnings.append(
            f'We renamed some columns because the input column "{column}" had '
            'empty values.'
        )
    if len(non_empty_headers) != len(unique_headers - set([''])):
        warnings.append(
            f'We renamed some columns because the input column "{column}" had '
            'duplicate values.'
        )

    headers = list(_uniquize_colnames(headers, unique_headers))

    table.index = headers[1:]

    input_types = set(c.type
                      for c in input_columns.values()
                      if c.name != column)
    if len(input_types) > 1:
        # Convert everything to text before converting. (All values must have
        # the same type.)
        to_convert = [c for c in table.columns
                      if input_columns[c].type != 'text']
        colnames_auto_converted_to_text.extend(to_convert)
        if len(to_convert) == 1:
            start = f'Column "{to_convert[0]}" was'
        else:
            colnames = ', '.join(f'"{c}"' for c in to_convert)
            start = f'Columns {colnames} were'
        warnings.append(
            f'{start} auto-converted to Text because all columns must have '
            'the same type.'
        )

        for colname in to_convert:
            # TODO respect column formats ... and nix the quick-fix?
            na = table[colname].isnull()
            table[colname] = table[colname].astype(str)
            table[colname][na] = np.nan

    # The actual transpose
    ret = table.T
    # Set the name of the index: it will become the name of the first column.
    ret.index.name = first_colname
    # Make the index (former colnames) a column
    ret.reset_index(inplace=True)

    if warnings and colnames_auto_converted_to_text:
        colnames = ', '.join(f'"{c}"' for c in colnames_auto_converted_to_text)
        return {
            'dataframe': ret,
            'error': '\n'.join(warnings),
            'quick_fixes': [{
                'text': f'Convert {colnames} to text',
                'action': 'prependModule',
                'args': [
                    'converttotext',
                    {'colnames': colnames_auto_converted_to_text},
                ],
            }]
        }
    if warnings:
        return (ret, '\n'.join(warnings))
    else:
        return ret
