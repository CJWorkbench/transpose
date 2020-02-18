from dataclasses import dataclass
from typing import Iterator, List, Set

import numpy as np
import pandas as pd

from cjwmodule import i18n
from cjwmodule.util.colnames import gen_unique_clean_colnames_and_warn


# hard-code settings for now. TODO have Workbench pass render(..., settings=...)
@dataclass
class Settings:
    MAX_COLUMNS_PER_TABLE: int
    MAX_BYTES_PER_COLUMN_NAME: int


settings = Settings(99, 120)


@dataclass
class GenColnamesResult:
    names: List[str]
    """All column names for the output table (even the first column)."""

    warnings: List[str]
    """All the things we should tell the user about how we tweaked names."""


def _gen_colnames_and_warn(
    first_colname: str, first_column: pd.Series
) -> GenColnamesResult:
    """
    Generate transposed-table column names.

    If `first_colname` is empty, `column.name` is the first output column. If
    both are empty, auto-generate the column name (and warn).

    Warn if ASCII-cleaning names, renaming duplicates, truncating names or
    auto-generating names.

    Assume `first_column` is text without nulls.
    """
    input_names = [first_colname or first_column.name]
    input_names.extend(list(first_column.values))

    names, warnings = gen_unique_clean_colnames_and_warn(input_names, settings=settings)

    return GenColnamesResult(names, warnings)


def render(table, params, *, input_columns):
    warnings = []
    colnames_auto_converted_to_text = []

    if len(table) > settings.MAX_COLUMNS_PER_TABLE:
        table = table.truncate(after=settings.MAX_COLUMNS_PER_TABLE - 1)
        warnings.append(
            i18n.trans(
                "warnings.tooManyRows",
                "We truncated the input to {max_columns} rows so the "
                "transposed table would have a reasonable number of columns.",
                {"max_columns": settings.MAX_COLUMNS_PER_TABLE},
            )
        )

    if not len(table.columns):
        # happens if we're the first module in the module stack
        return pd.DataFrame()

    column = table.columns[0]
    first_column = table[column]
    table.drop(column, axis=1, inplace=True)

    if input_columns[column].type != "text":
        warnings.append(
            {
                "message": i18n.trans(
                    "warnings.headersConvertedToText.message",
                    'Headers in column "{column_name}" were auto-converted to text.',
                    {"column_name": column},
                ),
                "quickFixes": [
                    {
                        "text": i18n.trans(
                            "warnings.headersConvertedToText.quickFix.text",
                            "Convert {column_name} to text",
                            {"column_name": '"%s"' % column},
                        ),
                        "action": "prependModule",
                        "args": ["converttotext", {"colnames": [column]},],
                    }
                ],
            }
        )

    # Ensure headers are string. (They will become column names.)
    # * categorical => str
    # * nan => ""
    # * non-text => str
    na = first_column.isna()
    first_column = first_column.astype(str)
    first_column[na] = ""  # Empty values are all equivalent

    gen_headers_result = _gen_colnames_and_warn(params["firstcolname"], first_column)
    warnings.extend(gen_headers_result.warnings)

    input_types = set(c.type for c in input_columns.values() if c.name != column)
    if len(input_types) > 1:
        # Convert everything to text before converting. (All values must have
        # the same type.)
        to_convert = [c for c in table.columns if input_columns[c].type != "text"]
        if to_convert:
            warnings.append(
                {
                    "message": i18n.trans(
                        "warnings.differentColumnTypes.message",
                        '{n_columns, plural, other {# columns (see "{first_colname}") were} one {Column "{first_colname}" was}} '
                        "auto-converted to Text because all columns must have the same type.",
                        {"n_columns": len(to_convert), "first_colname": to_convert[0]},
                    ),
                    "quickFixes": [
                        {
                            "text": i18n.trans(
                                "warnings.differentColumnTypes.quickFix.text",
                                "Convert {n_columns, plural, other {# columns} one {# column}} to text",
                                {"n_columns": len(to_convert)},
                            ),
                            "action": "prependModule",
                            "args": ["converttotext", {"colnames": to_convert},],
                        }
                    ],
                }
            )

        for colname in to_convert:
            # TODO respect column formats ... and nix the quick-fix?
            na = table[colname].isnull()
            table[colname] = table[colname].astype(str)
            table[colname][na] = np.nan

    # The actual transpose
    table.index = gen_headers_result.names[1:]
    ret = table.T
    # Set the name of the index: it will become the name of the first column.
    ret.index.name = gen_headers_result.names[0]
    # Make the index (former colnames) a column
    ret.reset_index(inplace=True)

    if warnings:
        return (ret, warnings)
    else:
        return ret


def _migrate_params_v0_to_v1(params):
    return {"firstcolname": ""}


def migrate_params(params):
    if "firstcolname" not in params:
        params = _migrate_params_v0_to_v1(params)
    return params
