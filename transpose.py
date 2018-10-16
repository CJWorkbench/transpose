from typing import Optional


MAX_N_COLUMNS = 999


class Form:
    """
    User input.

    The user may select no column at all, which will make column headers '0',
    '1', etc.
    """

    def __init__(self, header_column: Optional[str], allow_duplicates: bool):
        self.header_column = header_column
        self.allow_duplicates = allow_duplicates

    @staticmethod
    def parse(*, header_column=None, allow_duplicates=False, **kwargs):
        if header_column == '':
            header_column = None

        return Form(header_column, allow_duplicates)


def transpose(table, form):
    truncate = (len(table) > MAX_N_COLUMNS)
    if truncate:
        table = table[0:MAX_N_COLUMNS]

    if form.header_column:
        series = table[form.header_column]

        if not form.allow_duplicates and series.duplicated().any():
            return (
                f'Column "{form.header_column}" has duplicated values, so '
                'transposing by it would create duplicate column names. '
                'Please confirm you want this.'
            )

        table = table.drop(form.header_column, axis=1)
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
