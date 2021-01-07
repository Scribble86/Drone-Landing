import csv
from typing import Sequence


class Logger:
    def __init__(self, filename: str, params: Sequence[str]):
        """
        :param filename: The name of the log file to save
        :param params: A list of first row titles"""
        self.file = open(filename, 'w')
        self.writer = csv.writer(self.file, dialect='excel')
        self.params = params
        self.writer.writerow(params)

    def __del__(self):
        self.file.close()

    def writeline(self, arguments: Sequence):
        """Enter a new line of elements to the log.

        Must have the same number of elements
        as this element was initialized with.
        """
        if len(arguments) == len(self.params):
            self.writer.writerow(arguments)
        else:
            print("Exception: improper number of arguments!")
