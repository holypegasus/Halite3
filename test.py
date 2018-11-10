## Test space
import math
from functools import partial
from itertools import product
from typing import Tuple, List

from hlt.constants import *
from hlt.positionals import Position as Pos, Delta as Dlt, Zone
from hlt.util import *
from hlt.transform import *
LVL = 'warn'

@memo(lvl=LVL)
def gen_ngbr_dxys(dist) -> List[Dlt]: # [Dlt] dist-away
  dxs = dys = range(-dist, dist+1)
  return sorted(Dlt(dx, dy) 
    for (dx, dy) in product(dxs, dys)
    if abs(dx)+abs(dy)==dist)
# tests(gen_ngbr_dxys, range(3))

def dist_mtn(pos0, pos1): # Manhattan
  dx = abs(pos0.x - pos1.x)
  dy = abs(pos0.y - pos1.y)
  dist = min(dx, DIM-dx) + min(dy, DIM-dy)
  return dist
def test_dist_mtn():
  DIM = 8
  p00 = Pos(2,1)
  p11 = Pos(5,7)
  asrt(eq, dist_mtn(p00,p11), 5)
  asrt(eq, dist_mtn(p11,p00), 5)
def test_zone():
  DIM = 8
  zone_normal = Zone(Pos(2,1), Pos(5,7), DIM)
  def not_contains(a, b): return not b in a
  asrt(contains, zone_normal, Pos(2,1))
  asrt(contains, zone_normal, Pos(5,7))
  asrt(contains, zone_normal, Pos(4,4))
  asrt(not_contains, zone_normal, Pos(1,1))
  asrt(not_contains, zone_normal, Pos(6,7))
  asrt(not_contains, zone_normal, Pos(1,1))
  zone_wrap = Zone(Pos(5,7), Pos(2,1), DIM)
  asrt(contains, zone_wrap, Pos(5,7))
  asrt(contains, zone_wrap, Pos(2,1))
  asrt(not_contains, zone_wrap, Pos(4,4))
  asrt(not_contains, zone_wrap, Pos(3,1))
  asrt(contains, zone_wrap, Pos(6,7))
  asrt(contains, zone_wrap, Pos(1,1))



# Test radar
# print(yx2ngbrs((3,0),4))
show = lambda mat: print(mat)
def make_map(dim=8, min_max=(0,1000), _show=False):
  _map = np.random.uniform(*min_max, size=(dim,dim)).astype(int)
  if _show: show(_map)
  return _map
DIM = 8
VMIN, VMAX = 0, 100
MAP_INIT = make_map(DIM,(VMIN,VMAX),_show=True)

src = DEPOT = (1,1)
_map = MAP_INIT.copy()
_map[DEPOT] = 0
init_cost2depot_map = init_cost2depot(_map, depot=DEPOT)
show(init_cost2depot_map)

















print('End of test.py !')
