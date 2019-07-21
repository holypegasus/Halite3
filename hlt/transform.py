## Utils: Halite3-specific
from functools import partial
from itertools import product
from typing import Tuple, List

import numpy as np

from .positionals import Delta as Dlt, Position as Pos
from .util import (
  flatmap, memo, # DATA
  timit, # DEBUG
  )


## TRANSFORM
obj2pos = lambda o: o if isinstance(o, Pos) else o.position

## GAME
# USR: Mtn-dist between generic Objs
def dist(game_map, obj0, obj1):
  pos0 = obj2pos(obj0)
  pos1 = obj2pos(obj1)
  # dx = abs(pos0.x - pos1.x)
  # dy = abs(pos0.y - pos1.y)
  # return min(dx, dim-dx) + min(dy, dim-dy)
  return game_map.calculate_distance(pos0, pos1)

## TODO memo & arg-ize
## PairWise cost(path_cheapest): Floyd-Warshall
@memo()
def yx2ngbrs(y,x, dim):
  yxs_naive = [(y,x+1),(y+1,x),(y,x-1),(y-1,x)]
  return [(yd%dim, xd%dim) for yd,xd in yxs_naive]
@timit(lvl='warn') # ~550ms
def floyd_warshall(_map):
  dim = len(_map)
  YXS = list(product( *[range(dim)]*2 ))
  COSTS = np.full(shape=[dim]*4, fill_value=float('inf')) # (i, j) -> cost$i->j
  def cost(yx_i, yx_j, yx_k=None): # cheapest known cost $ i->j (opt via k)
    if not yx_k: return COSTS[(*yx_i, *yx_j)] # cost$i->j
    else: return cost(yx_i,yx_k) + cost(yx_k,yx_j) # cost$i->k->j
  def set_cost(yx_i,yx_j, _cost): COSTS[(*yx_i, *yx_j)] = _cost # cost#i->j <- _cost
  def weight(yx_i, yx_ngbr): return _map[(*yx_i,)] # Halite3: ngbr$i,j => cost$i->j <- val$i
  NEXTS = np.full([dim]*4, None) # (i, j) -> k: st cost$i->k->j == min$cost$i->j
  def next_(yx_i, yx_j): return NEXTS[(*yx_i, *yx_j)]
  def set_next(yx_i,yx_j, _next): NEXTS[(*yx_i, *yx_j)] = _next
  # @memo() # maybe useful when queried in game
  def path(yx_i, yx_j):
    if not next_(yx_i, yx_j): return [] # base: next$i==j -> None
    else: nexts = [(yx_i, weight(yx_i,yx_j))] + path(next_(yx_i,yx_j), yx_j) # ndct: recursive
    # else: # ndct: iterative
    #   nexts = [yx_i] # vertex_start
    #   while yx_i!=yx_j:
    #     yx_i = next_(yx_i, yx_j)
    #     nexts += [yx_i] # vertex_next
    return nexts
  ## init: base & ndct cases
  for yx in YXS:
    set_cost(yx, yx, 0) # v->v: 0
    for yx_ngbr in yx2ngbrs(*yx, dim): # v->ngbr: val(v) <- Halite3
      set_cost(yx, yx_ngbr, weight(yx, yx_ngbr))
      set_next(yx, yx_ngbr, yx_ngbr)
  ## update: cost(all vertex-pairs i & j) via v_k
  for yx_k,yx_i,yx_j in product(*[YXS]*3):
    if cost(yx_i,yx_j) > cost(yx_i,yx_j,yx_k):
      set_cost(yx_i,yx_j, cost(yx_i,yx_j,yx_k))
      set_next(yx_i,yx_j, next_(yx_i,yx_k))
  return cost, path # pairwise cheapest-path's 1) cost 2) actual


