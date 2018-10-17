#!/bin/sh

./halite --replay-directory replays/ -vvv --width 16 --height 16 "python3 $1" "python3 $2"
