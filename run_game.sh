#!/bin/sh

# ./halite --replay-directory replays/ -vvv --width 16 --height 16 "python3 $1" "python3 $2"

./halite --replay-directory replays/ -vvv --width 16 --height 16 "python3 bot_0_init.py" "python3 MyBot.py"

# ./halite --replay-directory replays/ -vvv --width 8 --height 8 "python3 bot_0_init.py" "python3 MyBot.py" --seed 1539843555

./run_reorg.sh

# ./run_clear_replays.sh

