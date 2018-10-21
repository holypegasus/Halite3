#!/bin/sh
# b0="bot_0_init.py"
# b0="bot_1_eval"
b0="bot_2_param"
b1="MyBot"
dim=8  # check compile
dim=16  # check valid
# dim=32  # check real MIN
# dim=64  # check real MAX
./halite --replay-directory replays/ -vvv --width $dim --height $dim "python3 $b0.py" "python3 $b1.py"
# ./halite --replay-directory replays/ -vvv --width $dim --height $dim '"python3 $b0.py" "python3 $b1.py" "python3 $b0.py" "python3 $b0.py"'

# seed=1540108840
# ./halite --replay-directory replays/ -vvv --width $dim --height $dim "python3 $b0.py" "python3 $b1.py"  --seed $seed
# ./halite --replay-directory replays/ -vvv --width $dim --height $dim "python3 $b0.py" "python3 $b1.py" "python3 $b0.py" "python3 $b0.py" --seed $seed

./run_reorg.sh

# ./run_clear_replays.sh

