from abc import ABC


def _esc_format(text):
    """Escape markdown formatting characters (underscore, asterisk) in a cell value."""
    return str(text).replace("_", r"\_").replace("*", r"\*")


def table_row(text_list):
    """Return a single unpadded markdown table row, e.g. '| a | b | c |'.

    Vendored from `markdown_strings` (MIT, awesmubarak/markdown_strings) —
    inlined here because the PyPI package was removed upstream and this
    service only ever needs the unpadded row/delimiter behavior.
    """
    return "| " + " | ".join(_esc_format(cell) for cell in text_list) + " |"


def table_delimiter_row(number_of_columns):
    """Return an unpadded markdown table delimiter row, e.g. '| --- | --- |'."""
    return table_row(["---"] * number_of_columns)


class MarkdownTableService(ABC):
    def table(self, table_list):
        number_of_columns = len(table_list)
        number_of_rows_in_column = [len(column) for column in table_list]
        string_list = [[str(cell) for cell in column]
                    for column in table_list]  # so cell can be int
        column_lengths = [len(max(column, key=len)) for column in string_list]
        table = []

        # title row
        row_list = [column[0] for column in string_list]
        table.append(table_row(row_list))

        # delimiter row
        table.append(table_delimiter_row(len(column_lengths)))

        # body rows
        for row in range(1, max(number_of_rows_in_column)):
            row_list = []
            for column_number in range(number_of_columns):
                if number_of_rows_in_column[column_number] > row:
                    row_list.append(string_list[column_number][row])
                else:
                    row_list.append("")
            table.append(table_row(row_list))
        return "\n".join(table)