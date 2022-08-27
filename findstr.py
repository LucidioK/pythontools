import fnmatch
import getopt
import os
import sys
import re

argumentList = sys.argv[1:]

def find_in_file(file_path, text):
    try:
        with open(file_path, 'r') as fp:
            for line_number,line in enumerate(fp):
                if line.find(text) != -1:
                    print(f'{file_path}@{line_number}:{line}', end='')
    except UnicodeDecodeError:
        return # do nothing, this is a file we cannot read.

def find_in_files(base_directory, name_filter, text):
    base_directory = base_directory.replace('~', os.environ['HOME'])
    with os.scandir(base_directory) as item:
        for entry in item:
            if entry.is_file():
                if (fnmatch.fnmatch(entry.name, name_filter)):
                    find_in_file(entry.path, text)
            else:
                find_in_files(entry.path, name_filter, text)

find_in_files(argumentList[0], argumentList[1], argumentList[2])
