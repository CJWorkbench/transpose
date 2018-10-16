from typing import Optional


MAX_N_COLUMNS = 99


def transpose(table):
    warnings = []

    if len(table) > MAX_N_COLUMNS:
        table = table[0:MAX_N_COLUMNS]
        warnings.append(
            f'We truncated the input to {MAX_N_COLUMNS} rows so the '
            'transposed table would have a reasonable number of columns.'
        )

    column = table.columns[0]
    series = table[column]

    if series.duplicated().any():
        # Trust Workbench's sanitizer to rename columns
        warnings.append(
            f'We renamed some columns because the input column "A" had '
            'duplicate values.'
        )

    table = table.drop(column, axis=1)
    headers = series.astype(str).values
    headers[series.isna()] = ''
    table.index = headers

    ret = table.T
    ret.index.name = 'Column'
    ret.reset_index(inplace=True)  # Makes 'Column' a column

    if warnings:
        return (ret, '\n'.join(warnings))
    else:
        return ret


def render(table, params):
    return transpose(table)
