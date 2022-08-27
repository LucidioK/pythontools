#!/bin/bash
if [ "$#" -ne 2 ] && [ "$#" -ne 3 ]
then
    echo
    echo dirsb.sh directory fileFilter [RegularExpressionToFilterOutEntries]
    echo
    exit 1
fi

directory=$1
fileFilter=$2
if [ "$#" -eq 3 ]
then
    filterOutRegex=$3
else
    filterOutRegex="###"
fi

scriptpath="$( ./resolvepath.sh dirsb.py )"
python3 "$scriptpath" $directory  "$fileFilter" "$filterOutRegex"
