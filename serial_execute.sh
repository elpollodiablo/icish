#!/bin/bash

test "$3" || { echo "$0 <regex> <command>"; exit 1; }

SSH_HOSTS=`python icish $1 "$2"`
DISPLAY=`echo $SSH_HOSTS |sed 's, ,\n,g'`
echo -e "Host to execute $3 on:\n$DISPLAY"
echo "Ok? (y/n)"
read ok

if [ "$ok" == "y" ]; then
	for SSH_HOST in $SSH_HOSTS; do
		echo "executing $3 on $SSH_HOST"
		ssh $SSH_HOST $3;
	done;
fi;
