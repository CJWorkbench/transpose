import pandas as pd


MAX_N_COLUMNS = 99


def render(table, params):
    warnings = []

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

    if series.duplicated().any():
        # Trust Workbench's sanitizer to rename columns
        warnings.append(
            f'We renamed some columns because the input column "{column}" had '
            'duplicate values.'
        )

    table = table.drop(column, axis=1)
    headers = series.astype(str).values
    headers[series.isna()] = ''
    table.index = headers

    # The actual transpose
    ret = table.T
    # Set the name of the index: it will become the name of the first column.
    # If user does not supply a name (default), use the input table's first
    # column.
    colname = params['firstcolname'].strip() or column
    ret.index.name = colname

    # Make the index (former colnames) a column
    ret.reset_index(inplace=True)

    if warnings:
        return (ret, '\n'.join(warnings))
    else:
        return ret
