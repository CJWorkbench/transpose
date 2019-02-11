from typing import Optional


MAX_N_COLUMNS = 99


def render(table, params):
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
            f'We renamed some columns because the input column "{column}" had '
            'duplicate values.'
        )

    table = table.drop(column, axis=1)
    headers = series.astype(str).values
    headers[series.isna()] = ''
    table.index = headers

    # The actual transpose
    ret = table.T
 
    if 'firstcolname' in params and params['firstcolname'] != '':
        ret.index.name = params['firstcolname'] # let user rename first column, if desired
    else:
        ret.index.name = column    # otherwise name of first column is unchanged
   
    ret.reset_index(inplace=True)  # Makes the index (formerly the column names) into a normal column

    if warnings:
        return (ret, '\n'.join(warnings))
    else:
        return ret


