#!/bin/sh
function maybe_seed {
  if [ -z $seed ]; then # no seed
    if [ $n = 2 ]; then
      ./halite --replay-directory replays/ -vvv --no-logs --width $dim --height $dim "python3 $b0.py" "python3 $b1.py"
    else
      ./halite --replay-directory replays/ -vvv --no-logs --width $dim --height $dim "python3 $b0.py" "python3 $b1.py" "python3 $b0.py" "python3 $b0.py"
    fi
    echo "Random play"
  else # yes seed
    if [ $n = 2 ]; then
      ./halite --replay-directory replays/ -vvv --no-logs --width $dim --height $dim "python3 $b0.py" "python3 $b1.py"  --seed $seed
    else
      ./halite --replay-directory replays/ -vvv --no-logs --width $dim --height $dim --seed $seed "python3 $b0.py" "python3 $b1.py" "python3 $b0.py" "python3 $b0.py"
    fi
    echo "Seeded play"
  fi
  }
# b0="bot_0_init"
# b0="bot_1_eval"
# b0="bot_2_param"
# b0="bot_3_convolve"
b0="bot_4_terminal"
b1="MyBot"
n=2
# n=4
dim=8  # check compile
dim=16  # check valid
# dim=32  # check real MIN
# dim=64  # check real MAX
# seed=1540178627

maybe_seed
./run_reorg.sh
# ./run_clear_replays.sh