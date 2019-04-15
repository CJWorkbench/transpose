import numpy as np
import pandas as pd


MAX_N_COLUMNS = 99


def render(table, params, *, input_columns):
    warnings = []
    colnames_auto_converted_to_text = []

    if len(table) > MAX_N_COLUMNS:
        table = table[0:MAX_N_COLUMNS]
        warnings.append(
            f'We truncated the input to {MAX_N_COLUMNS} rows so the '
            'transposed table would have a reasonable number of columns.'
        )

    if not len(table.columns):
        # happens if we're the first module in the module stack
        return pd.DataFrame()

    column = table.columns[0]
    series = table[column]

    if input_columns[column].type != 'text':
        warnings.append(f'Headers in column "A" were auto-converted to text.')
        colnames_auto_converted_to_text.append(column)
        headers = series.astype(str)
        headers[series.isna()] = ''
        headers[headers.isna()] = ''
    else:
        headers = series

    if headers.duplicated().any():
        # Trust Workbench's sanitizer to rename columns
        warnings.append(
            f'We renamed some columns because the input column "{column}" had '
            'duplicate values.'
        )

    table = table.drop(column, axis=1)
    table.index = headers.values

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
    # If user does not supply a name (default), use the input table's first
    # column.
    colname = params['firstcolname'].strip() or column
    ret.index.name = colname

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
                    {'colnames': ','.join(colnames_auto_converted_to_text)},
                ],
            }]
        }
    if warnings:
        return (ret, '\n'.join(warnings))
    else:
        return ret
