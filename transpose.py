from typing import Optional


MAX_N_COLUMNS = 999


class Form:
    """
    User input.

    The user may select no column at all, which will make column headers '0',
    '1', etc.
    """

    def __init__(self, header_colname: Optional[str], allow_duplicates: bool):
        self.header_colname = header_colname
        self.allow_duplicates = allow_duplicates

    @staticmethod
    def parse(*, header_colname=None, allow_duplicates=False, **kwargs):
        if header_colname == '':
            header_colname = None

        return Form(header_colname, allow_duplicates)


def transpose(table, form):
    truncate = (len(table) > MAX_N_COLUMNS)
    if truncate:
        table = table[0:MAX_N_COLUMNS]

    if form.header_colname:
        series = table[form.header_colname]

        if not form.allow_duplicates and series.duplicated().any():
            return (
                f'Column "{form.header_colname}" has duplicated values, so '
                'transposing by it would create duplicate column names. '
                'Please confirm you want this.'
            )

        table = table.drop(form.header_colname, axis=1)
        headers = series.astype(str).values
        table.index = headers
    else:
        table.index = table.index.astype(str)

    ret = table.T
    ret.index.name = 'Column'
    ret.reset_index(inplace=True)  # Makes 'Column' a column

    if truncate:
        return (ret, (
            f'We truncated the input to {MAX_N_COLUMNS} rows so the '
            'transposed table would have a reasonable number of columns.'
        ))
    else:
        return ret


def render(table, params):
    form = Form.parse(**params)

    return transpose(table, form)
