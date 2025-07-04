from abc import ABC
from markdown_strings import table_row, table_delimiter_row


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