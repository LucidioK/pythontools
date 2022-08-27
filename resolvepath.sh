#!/bin/bash
explainThenExit() (
    echo
    echo resolvepath.sh somepath
    echo Will return the full path
    echo
)
if [ "$#" -ne 1 ]
then
    explainThenExit ; exit 1
fi

if [ "$1" == "-h" ] || [ "$1" == "--help" ] || [ "$1" == "--?" ] ||  [ "$1" == "--version" ] || [ "$1" == "-?" ] || [ "$1" == "-help"  ]
then
    explainThenExit ; exit 1
fi

# filepath=$(python3 -c 'import os, sys; print(os.path.abspath(sys.argv[1]))' "$1")
# if [ ! -e "$filepath" ]; then
#     filepath=$(python3 findstr.py "$1")
# fi

if [ -e "$1" ]; then
    readlink -f "$1"
    exit 0
fi

IFS=:
dirs=( $PATH )
for dir in "${dirs[@]}"; do
    if [ -e "$dir/$1" ]; then
        echo "$dir/$1"
        exit 0
    fi
done

exit 1
