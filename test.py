## Sandbox for testing functi
import math
from functools import partial
from typing import Tuple, List
Crd = Tuple[int, int]

from hlt.positionals import Position as Pos
from hlt.util import *


DIM_GAME = 32
pos0 = Pos(35, 0)
pos1 = Pos(34, 30)
def dist_mtn(pos0, pos1): # Manhattan
  dx = abs(pos0.x - pos1.x)
  dy = abs(pos0.y - pos1.y)
  dist = min(dx, DIM_GAME-dx) + min(dy, DIM_GAME-dy)
  return dist
print(dist_mtn(pos0, pos1))