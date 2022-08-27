import fnmatch
import getopt
import os
import sys
import re

argumentList = sys.argv[1:]

def find_files(base_directory, name_filter, filter_out_regex):
    base_directory = base_directory.replace('~', os.environ['HOME'])
    try:
        with os.scandir(base_directory) as item:
            for entry in item:
                if (filter_out_regex.match(entry.path)):
                    continue
                if (fnmatch.fnmatch(entry.name, name_filter)):
                    print(f'{entry.path}')
                if entry.is_dir() and not entry.is_symlink():
                    find_files(entry.path, name_filter, filter_out_regex)
    except PermissionError:
        return # do nothing, this is a directory we cannot read.
    except FileNotFoundError:
        return # do nothing, this is a directory we cannot read.
                
bdi=argumentList[0]
flt=argumentList[1]
if len(argumentList) == 3:
    exc=argumentList[2]
else:
    exc='###'

rgx = re.compile(exc)
find_files(bdi, flt, rgx)
