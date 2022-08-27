#!/bin/bash
if [ "$#" -ne 3 ]
then
    echo
    echo findstr.sh directory fileFilter termtofind
    echo example:
    echo ./findstr.sh dsv '*.py' 'PermissionError'
    echo
    exit 1
fi

startdir=$(readlink -f "$1")

scriptpath="$( ./resolvepath.sh findstr.py )"

python3 "$scriptpath" $startdir  "$2" "$3"
