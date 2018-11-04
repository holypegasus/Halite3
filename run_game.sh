#!/bin/sh
function run_game {
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
    echo "Seeded play: $seed"
  fi
  }
# mv p0 -> p1 if p0
function mv_if { 
  if [ -f $1 ]; then
    mv $1 $2;
    cat $2
    echo "Errors! :O"
  else
    > $2;
    echo "error FREE :D"
  fi
  }
function reorg_files {
  mv bot*.log replays/;
  cd replays;
  mv_if errorlog*0.log bot_0_err.log;
  mv_if errorlog*1.log bot_1_err.log;
  }
function clear_replays {
  buffer=3;
  n_replays=$(ls replays/replay*hlt|wc -l);
  let n_replays-=$buffer;
  ls -F replays/replay*hlt | head -n$n_replays | xargs rm;
  rm replays/errorlog*.log;
  echo "cleared all before $buffer-newest replays!"
  }
# b0="b0_init"
# b0="b1_eval"
# b0="b2_param"
# b0="b3_convolve"
# b0="b4_terminal"
b0="b5_efficient"
b1="MyBot"
n=2
n=4
dim=8  # check compile
# dim=32  # check MIN
# dim=48  # check MED/DROPOFF
# dim=64  # check MAX
# seed=1541272138

clear_replays;
run_game; reorg_files;