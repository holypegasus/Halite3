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
# b0="b0_init"
# b0="b1_eval"
# b0="b2_param"
# b0="b3_convolve"
# b0="b4_terminal"
b0="b5_efficient"
b1="MyBot"
n=2
# n=4
dim=8  # check compile
# dim=16  # check valid
# dim=24  # check Dropoff
dim=32  # check MIN
# dim=48  # check MED
# dim=64  # check MAX
# seed=1540185585

maybe_seed
./run_reorg.sh
./run_clear_replays.sh