from dataclasses import dataclass
import numpy as np
import pandas as pd
from cjwmodule.util.colnames import gen_unique_clean_colnames
from typing import Iterator, List, Set


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
    n_ascii_cleaned = 0
    first_ascii_cleaned = None
    n_default = 0
    first_default = None
    n_truncated = 0
    first_truncated = None
    n_numbered = 0
    first_numbered = None

    input_names = [first_colname or first_column.name]
    input_names.extend(list(first_column.values))

    names = []

    for uccolname in gen_unique_clean_colnames(input_names, settings=settings):
        name = uccolname.name
        names.append(name)
        if uccolname.is_ascii_cleaned:
            if n_ascii_cleaned == 0:
                first_ascii_cleaned = name
            n_ascii_cleaned += 1
        if uccolname.is_default:
            if n_default == 0:
                first_default = name
            n_default += 1
        if uccolname.is_truncated:
            if n_truncated == 0:
                first_truncated = name
            n_truncated += 1
        if uccolname.is_numbered:
            if n_numbered == 0:
                first_numbered = name
            n_numbered += 1

    warnings = []
    if n_ascii_cleaned > 0:
        warnings.append(
            "Removed special characters from %d column names (see “%s”)"
            % (n_ascii_cleaned, first_ascii_cleaned)
        )
    if n_default > 0:
        warnings.append(
            "Renamed %d column names (because values were empty; see “%s”)"
            % (n_default, first_default)
        )
    if n_truncated > 0:
        warnings.append(
            "Truncated %d column names (to %d bytes each; see “%s”)"
            % (n_truncated, settings.MAX_BYTES_PER_COLUMN_NAME, first_truncated)
        )
    if n_numbered > 0:
        warnings.append(
            "Renamed %d duplicate column names (see “%s”)"
            % (n_numbered, first_numbered)
        )

    return GenColnamesResult(names, warnings)


def render(table, params, *, input_columns):
    warnings = []
    colnames_auto_converted_to_text = []

    if len(table) > settings.MAX_COLUMNS_PER_TABLE:
        table = table.truncate(after=settings.MAX_COLUMNS_PER_TABLE - 1)
        warnings.append(
            f"We truncated the input to {settings.MAX_COLUMNS_PER_TABLE} rows so the "
            "transposed table would have a reasonable number of columns."
        )

    if not len(table.columns):
        # happens if we're the first module in the module stack
        return pd.DataFrame()

    column = table.columns[0]
    first_column = table[column]
    table.drop(column, axis=1, inplace=True)

    if input_columns[column].type != "text":
        warnings.append(f'Headers in column "A" were auto-converted to text.')
        colnames_auto_converted_to_text.append(column)

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
        colnames_auto_converted_to_text.extend(to_convert)
        if len(to_convert) == 1:
            start = f'Column "{to_convert[0]}" was'
        else:
            colnames = ", ".join(f'"{c}"' for c in to_convert)
            start = f"Columns {colnames} were"
        warnings.append(
            f"{start} auto-converted to Text because all columns must have "
            "the same type."
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

    if warnings and colnames_auto_converted_to_text:
        colnames = ", ".join(f'"{c}"' for c in colnames_auto_converted_to_text)
        return {
            "dataframe": ret,
            "error": "\n".join(warnings),
            "quick_fixes": [
                {
                    "text": f"Convert {colnames} to text",
                    "action": "prependModule",
                    "args": [
                        "converttotext",
                        {"colnames": colnames_auto_converted_to_text},
                    ],
                }
            ],
        }
    if warnings:
        return (ret, "\n".join(warnings))
    else:
        return ret


def _migrate_params_v0_to_v1(params):
    return {"firstcolname": ""}


def migrate_params(params):
    if "firstcolname" not in params:
        params = _migrate_params_v0_to_v1(params)
    return params
