import fnmatch
import getopt
import os
import sys
import re

if len(sys.argv) != 2:
    print("findinpath.py filename")
    os._exit(1)

filename = sys.argv[1]
foundpath = ''
for p in os.getenv('PATH').split(':'):
    filepath = os.path.join(p, filename)
    if os.path.exists(filepath):
        foundpath = filepath
        break
    
if not foundpath:
    print(f'Could not find {filename} in PATH')
    os._exit(2)
    
print(foundpath)
os._exit(0)