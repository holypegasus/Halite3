#!/bin/sh

# mv p0 p1 if p0
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

cd replays;
mv_if errorlog*0.log bot_0_err.log;
mv_if errorlog*1.log bot_1_err.log;