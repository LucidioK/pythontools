if [ "$#" -ne 1 ]
then
    echo
    echo makeexecutable.sh filepath
    echo
    exit 1
fi

chmod 755 $1