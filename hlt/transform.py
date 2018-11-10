## Utils: Halite3-specific
from functools import partial
from itertools import product
from math import ceil, floor, log as log10
from queue import PriorityQueue
from typing import Tuple, List

import numpy as np
import pandas as pd

from .positionals import Delta as Dlt, Position as Pos, Direction as Dir
from .util import (
  flatmap, memo, # DATA
  timit,lvl2lgr,log,logitr,logaz # DEBUG
  )

## DEBUG
# check if extreme-value
def extreme(v, threshold=1e6): return v<-threshold or v>threshold
def logmat(mat, header='', yx_ship=(), yx_depots=[], yx_ships=[], lvl='debug'):
  # TODO justify by 1+log(abs(max(val)))
  # max_magni = max(abs(mat.max()), abs(mat.min()))
  # n_jus = floor(log10(max_magni)) + 1 # neg sign
  n_jus = 5
  def fmt(y,x):
    # drop decimal
    str_v = '?' if extreme(mat[y,x]) else int(mat[y,x])
    # annotate
    if (y,x) in yx_depots: str_v = '#%s'%str_v
    if (y,x)==yx_ship: str_v = '*%s'%str_v
    elif (y,x) in yx_ships: str_v = '+%s'%str_v
    # justify
    str_jus = '%0'+str(n_jus)+'s'
    return str_jus%str_v
  dim = len(mat)
  mat_str = '\n'.join([' '.join(fmt(y,x) for x in range(dim)) 
    for y in range(dim)])
  str_mat = np.asarray(mat_str).astype(object)
  lvl2lgr(lvl)('%s\n%s', header, str_mat)

## TRANSFORM
obj2pos = lambda o: o if isinstance(o, Pos) else o.position

## GAME
DIRS4 = Dir.get_all_cardinals()
DIR_O = Dir.Still
DIRS_ALL = [DIR_O] + DIRS4
# USR: Mtn-dist between generic Objs
def dist(game_map, obj0, obj1):
  pos0 = obj2pos(obj0)
  pos1 = obj2pos(obj1)
  return game_map.calculate_distance(pos0, pos1)

# raw Mtn-dist for testing
@memo()
def dist_mtn(yx0, yx1, dim): # yx
  dx = abs(yx0[1] - yx1[1])
  dy = abs(yx0[0] - yx1[0])
  return min(dx, dim-dx) + min(dy, dim-dy)

def normalize(y,x,dim):
  return y%dim, x%dim
@memo()
def yx2ngbrs(y,x, dim):
  yxs_naive = [(y,x+1),(y+1,x),(y,x-1),(y-1,x)]
  return [normalize(yd,xd, dim) for yd,xd in yxs_naive]


"""BestFirstSearch
  scan for value
  seek path-cheapest: src -> tgt
  """
## NB all following expect coord-format (y, x)
# utils
@memo()
def c8c2c(yx0,dlt,dim): return (yx0[0]+dlt[0])%dim, (yx0[1]+dlt[1])%dim
def c8cs2c(yx0, dlts, dim): return c8c2c(yx0, tuple(map(sum,zip(*dlts))), dim)
@memo()
def yx2ngbrs(yx, dim):
  dirs = DIRS4#[E,N,W,S]
  return [c8c2c(yx,_dir,dim) for _dir in dirs]
# PriorityQueue -> put, get, empty
def pq(item_init=None, lvl='debug'):
  logf = lvl2lgr(lvl)
  def pq_put(item):
    _pq.put(item)
    # logf('+ %s [%d]', item, _pq.qsize())
  def pq_get():
    item = _pq.get()
    # logf('- %s [%d]', item, _pq.qsize())
    return item
  empty = lambda: _pq.empty()
  # stats = lambda: logf('# puts: %d; # gets: %d', n_puts, n_gets)
  _pq = PriorityQueue()
  if item_init: pq_put(item_init)
  return pq_put, pq_get, empty#, stats
# BFS env -> map,cost,depot,val,backtrack
# map_depot_only: calc map_depot w/o backtrack
# @timit(lvl='warn')
def scan(_map, map_depot, src, map_depot_only=False, perim=2, r_decay=1., r_cost_move=.1, lvl='debug'):
  logf = lvl2lgr(lvl)
  # logf('%s scanning w/ perim: %s; r_decay: %s', src, perim, r_decay)
  dim = len(_map)
  cost_init = np.inf
  map_cost = np.full((dim,dim),fill_value=cost_init)
  seen = lambda yx: map_cost[yx]!=cost_init
  map_val = np.full((dim,dim),fill_value=-cost_init)
  def clj_backtrack(): # backtrack outer vals -> immediate Moves
    map_back = np.full((dim,dim),fill_value=-cost_init)
    map_back[src] = map_val[src]
    curr2prev = {src: src} # link cells: outer -> inner
    def back_ptr(yx_curr, yx_prev): # stores curr->prev then returns prev
      curr2prev[yx_curr] = yx_prev
      return yx_prev
    def backtrack(yx_curr, yx_prev):
      # update yx_curr
      dist = dist_mtn(yx_curr, src, dim)
      new_back_curr = max(
        floor(map_val[yx_curr]*(r_decay**dist)), 
        map_back[yx_curr])
      if new_back_curr != map_back[yx_curr]:
        # logf('%so>%s: %s->%s', yx_curr, yx_curr, map_back[yx_curr], new_back_curr)
        map_back[yx_curr] = new_back_curr
      # update prev
      if yx_prev!=src:
        dist = dist_mtn(yx_prev, src, dim)
        new_back_prev = max(
          floor(map_back[yx_curr]*r_decay),
          floor(map_val[yx_prev]*(r_decay**dist)),
          map_back[yx_prev])
        if new_back_prev != map_back[yx_prev]:
          # logf('%s->%s: %s->max"(%s, %s, %s)=>%s', 
          #   yx_curr, yx_prev, map_back[yx_prev], 
          #   map_back[yx_curr], map_val[yx_prev], map_back[yx_prev],
          #   new_back_prev)
          map_back[yx_prev] = new_back_prev
        backtrack(yx_prev, curr2prev[yx_prev]) # pass new info outside inward
    return back_ptr, backtrack, map_back
  back_ptr, backtrack, map_back = clj_backtrack()
  put, get, empty = pq(item_init=(0,0,src,src), lvl=lvl) # (cost,dist,yx_curr,yx_prev)
  while not empty():
    cost,dist,yx_curr,yx_prev = get()
    if cost < map_cost[yx_curr]: # 1st visit also cheapest -> update maps & backtrack
      map_cost[yx_curr] = cost
      if extreme(map_depot[yx_curr]):  log.warning('%s: extreme val @ map_depot[%s]: %s', src, yx_curr, map_depot[yx_curr])
      # cost: src -> tgt -> depot_nearest 
      map_val[yx_curr] = _map[yx_curr] - cost - map_depot[yx_curr]
      # logf('val: %s <- %s - %s - %s', yx_curr, _map[yx_curr], cost, map_depot[yx_curr])
      if not map_depot_only: backtrack(yx_curr, yx_prev)
      if dist_mtn(src, yx_curr, dim) < perim: # expand in-perim ngbrs
        for yx_ngbr in [yx for yx in yx2ngbrs(yx_curr, dim) if not seen(yx)]:
          src4cost = yx_curr if not map_depot_only else yx_ngbr # reverse approach direction <- map_depot
          cost_ngbr = floor(cost + _map[src4cost]*r_cost_move) # decay val but not cost
          put( (cost_ngbr, dist+1, yx_ngbr, back_ptr(yx_ngbr, yx_curr)) )
  """ how maps relate
    _map, map_depot, map_cost -> map_val
    map_val -> map_back"""
  return _map, map_depot, map_cost, map_val, map_back
# initial map -> initial cost-to-depot-map
# @timit(lvl='warn')
def init_map_depot(_map, depot, perim, lvl='debug'):
  dim = len(_map)
  _,_,map_depot,_,_ = scan(_map, map_depot=np.full((dim,dim),0), src=depot, map_depot_only=True, perim=perim, r_decay=1., lvl=lvl)
  return map_depot.astype(int)

