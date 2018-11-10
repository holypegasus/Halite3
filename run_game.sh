#!/bin/sh
run_game () {
  bot0="$(echo \"python3 $1.py\")"
  bot1="$(echo \"python3 ARK/$2/MyBot.py\")"
  bot2="$(echo \"python3 ARK/${3:-$2}/MyBot.py\")" # ${X:-$Y} <- sub if not
  bot3="$(echo \"python3 ARK/${4:-$3}/MyBot.py\")"
  bots2="$bot0 $bot1"
  bots4="$bot0 $bot1 $bot2 $bot3"
  cmd_base="./halite --replay-directory replays/ --no-logs -vvv --width $dim --height $dim"
  # set bots
  if [ $n = 2 ]; then
    cmd_bots=$bots2
  else
    cmd_bots=$bots4
  fi
  # set seed
  if [ -z $seed ]; then # no seed
    cmd_seed=""
  else
    cmd_seed="--seed $seed"
  fi
  echo "$cmd_base $cmd_bots $cmd_seed"
  eval "$cmd_base $cmd_bots $cmd_seed"
  }
mv_if () {
  if [ -f $1 ]; then
    mv $1 $2;
    cat $2
    echo "Errors! :O"
  else
    > $2; # clear out prev error-log
    # echo "error FREE :D"
  fi
  }
rm_if () {
  if [ -f $1 ]; then
    rm $1
  fi
  }
mv_outputs () {
  # mv bot*.log replays/; # leave in top folder since remote doesn't allow replays
  cd replays;
  mv_if errorlog*0.log bot_0_err.log;
  mv_if errorlog*1.log bot_1_err.log;
  rm_if errorlog*.log; # if bot2 & bot3]
  cd ..;
  }
trim_replays () {
  buffer=4;
  n_replays=$(ls replays/replay*hlt|wc -l);
  let n_replays-=$buffer;
  ls -F replays/replay*hlt | head -n$n_replays | xargs rm;
  rm_if replays/errorlog*.log;
  }
# b3="b6_depot"
# b2="b6_depot"
b1="b7_goal"
b0="MyBot"
n=2
# n=4
# dim=8  # check compile
# dim=12  # check scan
# dim=16  # check TERMINAL
# dim=32   # check MIN - 401 turns
# seed=1542597964 # depot 32
# seed=1542784283 # depot 32
# seed=1542784390 # depot 32
# dim=56
dim=64  # check MAX - 501 turns
seed=1542778654 # depot 64

run_game $b0 $b1 $b2 $b3;
mv_outputs;
trim_replays;