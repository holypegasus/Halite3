#!/bin/sh

# b0="bot_0_init.py"
b0="bot_1_eval"
b1="MyBot"

# dim=8  # check valid
dim=16  # check realistic
# dim=32  # check scale
seed=1539928027

./halite --replay-directory replays/ -vvv --width $dim --height $dim "python3 $b0.py" "python3 $b1.py"
# ./halite --replay-directory replays/ -vvv --width $dim --height $dim "python3 $b0.py" "python3 $b1.py"  --seed $seed

./run_reorg.sh

# ./run_clear_replays.sh

