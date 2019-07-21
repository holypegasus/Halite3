#!/usr/bin/env python3.6
import enum, math, random, time, traceback
from collections import Counter, OrderedDict
from functools import partial
from itertools import chain, product
from operator import (
  lt, le, eq, ne, ge, gt,
  contains
  )
from statistics import mean
from typing import Tuple, List

import numpy as np
import pandas as pd

import hlt
from hlt import commands as cmds, constants as const
from hlt.positionals import Direction as Dir, Position as Pos, Delta as Dlt, Zone
from hlt.transform import (
  obj2pos, # TRANSFORM
  dist, # GAME
  )
from hlt.util import (
  flatmap, mapl, maps_itr, maps_func, memo, # DATA
  asrt, lvl2lgr, log, logitr, logaz, timit, # DEBUG
  )

spawn_cap = lambda: True # normal
# spawn_cap = lambda: which_turn()<60 # FOCO turns
# spawn_cap = lambda : len(ships_mine())<2 # FOCO few
""" <<<Game Begin>>> """
game = hlt.Game()
## CONSTANTS
R_COST_MOVE = 1 / const.MOVE_COST_RATIO # 0.1
R_EXTRACT_NORMAL = 1 / const.EXTRACT_RATIO # 0.25
N_RADIUS_INSPIRE = const.INSPIRATION_RADIUS # 4
N_FOE_INSPIRE = const.INSPIRATION_SHIP_COUNT # 2
R_EXTRACT_INSPIRED = (1+const.INSPIRED_BONUS_MULTIPLIER) / const.EXTRACT_RATIO # 0.75
# log.warning((R_COST_MOVE,R_EXTRACT_NORMAL,N_RADIUS_INSPIRE,N_FOE_INSPIRE,R_EXTRACT_INSPIRED))
Task = enum.Enum('Task', 'roam drop raid term')
DIRS4 = Dir.get_all_cardinals()
DIR_O = Dir.Still
DIRS_ALL = [DIR_O] + DIRS4
LVL_TIMIT = 'warn'
# TIMEOUT_BREAKER = 1.600 # secs
## GLOBAL
me = game.me
gm = game.game_map
DIM_GAME = gm.width # == gm.height
DIM_MIN = 32 # [32, 64]
MAX_TURN = const.MAX_TURNS + 1 # [401, 501]
which_turn = lambda : game.turn_number
turns_left = lambda : MAX_TURN - which_turn()
age = lambda : which_turn() / MAX_TURN  # [0., 1.]
# NB decr curio -> start idling!
# r_curio = lambda : .8 + .2*age() # ++ curio
# r_curio = lambda : 1 - age() # -- curio
r_curio = lambda : .9 # == curio
# n_drop = lambda : const.MAX_HALITE * (.75 + .2*age()) # ++ 
# n_drop = lambda : const.MAX_HALITE * (.95 - .45*age()) # --
n_drop = lambda : const.MAX_HALITE * .95 # ==
# n_perim = lambda : round(2 + 2*age())
n_perim = lambda : 2
turn_last_spawn = lambda : .5 * MAX_TURN # TODO -> smarter eval sum(ship.val_future)
exp_depot = lambda : 1.5 # cost-exponent on r_curio for eval_depot

## PREPROC <= 30sec
def clj_preproc():  pass # TODO static game info
game.ready('b7_goal')
## EVAL, MOVE, DEPOT
def clj_globals(lvl='info'): # global CLJ -> NB objs get recreated every turn
  sid2task = dict()  # sid:int -> Task:Enum
  def set_ship2task(ship, task): sid2task[ship.id] = task
  get_ship2task = lambda ship: sid2task.get(ship.id)
  return set_ship2task, get_ship2task
set_ship2task, get_ship2task = clj_globals()
# move_random = lambda : random.choice(DIRS4)
pos2hlt = lambda pos: gm[pos].halite_amount
def p8d2pos(pos_src, _dir): return gm.normalize(pos_src + Dlt(*_dir))
@memo()
def gen_ngbr_dxys(dist) -> List[Dlt]: # [Dlt] dist-away
  dxs = dys = range(-dist, dist+1)
  return sorted(set(Dlt(dx, dy)
    for (dx, dy) in product(dxs, dys)
    if abs(dx)+abs(dy)==dist))
@memo()
def gen_ring(origin, dist): # ring of Pos dist-away [4*d] -> [(dist:int, Pos)]
  dxys = gen_ngbr_dxys(dist)
  return [(dist, gm.normalize(origin+dxy)) for dxy in dxys]
@memo()
def pos2dist8ngbrs(pos, perim) -> [(int, Pos)]:
  return flatmap(partial(gen_ring, pos), range(1, perim+1))
# @timit(LVL_TIMIT) # ! bulk of processing here
def clj_eval(lvl='debug'): # turnly CLJ: eval Pos
  # NB: hlt: curr tile worth; val: extended worth
  # time-decayed worth of nearby cell
  def calc_val_ngbr(dist:int, pos:Pos, exp=1):
    return round(pos2hlt(pos) * (r_curio()**exp)**dist)
  @memo()
  def pos2val(pos, perim=n_perim()): # TODO improv!
    hlt_here = pos2hlt(pos)
    vals_ngbrs = [calc_val_ngbr(d, pos_ngbr) for d, pos_ngbr in pos2dist8ngbrs(pos, perim)]
    return round(hlt_here + mean(vals_ngbrs))
  @memo()
  def eval_area(obj, perim):
    pos = obj if isinstance(obj, Pos) else obj.position
    hlt_here = pos2hlt(pos)
    vals_ngbrs = [calc_val_ngbr(d, pos_ngbr, exp_depot()) for d, pos_ngbr in pos2dist8ngbrs(pos, perim)]
    return round(hlt_here + sum(vals_ngbrs))
  def show_value_matrix(): 
    df_vals = pd.DataFrame(mat_vals) # NB [x][y]
    # annotate
    df_show = df_vals.copy()
    pos_shipyard = me.shipyard.position
    df_show[pos_shipyard.x][pos_shipyard.y] = '{%s}'%(df_show[pos_shipyard.x][pos_shipyard.y])
    for s in ships_mine():
      df_show[s.position.x][s.position.y] = '[%s]'%(df_show[s.position.x][s.position.y])
    lvl2lgr(lvl)('\n%s', df_show)
  # @timit(lvl=LVL_TIMIT)
  @memo(lvl=lvl)
  def eval_depot(ship, depot_nearest_ship): # TMP refine!
    dist = dist_mtn(ship, depot_nearest_ship)
    d_half = dist//2
    if d_half > 0:
      val_area_ship = eval_area(ship, d_half) * (1-r_curio()**dist)
      val_area_depot_nearest = eval_area(depot_nearest_ship, d_half)
      cost_depot = (const.DROPOFF_COST - ship.halite_amount)/(1-age()) + const.SHIP_COST # TMP measure of ship's future val
      return round(val_area_ship - val_area_depot_nearest - cost_depot)
    else:
      return -1 # sufficient since only consider building depot for positive val
  mat_vals = [[pos2val(Pos(x,y)) 
    for y in range(DIM_GAME)] 
    for x in range(DIM_GAME)] # NB get[x][y]
  return pos2val, show_value_matrix, eval_depot

def pos2crd(pos, dim=DIM_GAME):  return (pos.x%dim, pos.y%dim)
obj2crd = lambda o: pos2crd(obj2pos(o))
@memo(key=lambda objs: tuple(map(obj2crd, objs)))
def dist_mtn(obj0, obj1): return dist(gm, obj0, obj1)
# TODO expand this into cost2depot_nearest
cost4move = lambda pos_src: R_COST_MOVE * pos2hlt(pos_src)
wont_stall = lambda ship: cost4move(ship.position) <= ship.halite_amount
def clj_move(get_ship2task, lvl='info'): # turnly CLJ
  ship_2_task8mov8val = OrderedDict() # Ship -> (move:str, val:float)
  crds_taken = set() # [crd]:(int, int)
  moves = []
  def save_vimp(val, ship, move, pos):
    mov = move.split()[-1]
    ship_2_task8mov8val[ship] = get_ship2task(ship), mov, val
    crds_taken.add(pos2crd(pos))
    moves.append(move)
  ship_free = lambda ship:  ship not in ship_2_task8mov8val
  def pos_free(obj):
    pos = obj if isinstance(obj, Pos) else obj.position
    return pos2crd(pos) not in crds_taken
  def export_moves(show=False):  # copy to prevent mutation
    moves_copied = [m for m in moves]
    if show:  logitr(moves_copied)
    return moves_copied
  # Inspire status & utils
  def get_ships_near(ship, perim):  # foe | mine
    ships_all = [s for p in game.players.values() for s in p.get_ships()]
    in_range = lambda s: s!=ship and dist_mtn(ship, s) <= perim 
    return filter(in_range, ships_all)
  @memo()
  def if_inspired(ship):
    # is_ship_foe = lambda s: s.owner != me.id
    # ships_foe = list(filter(is_ship_foe, get_ships_near(ship, perim=4)))
    ships_foe = [s for s in get_ships_near(ship, N_RADIUS_INSPIRE) if s.owner!=me.id]
    return len(ships_foe) >= N_FOE_INSPIRE
  @memo() # Halite pick-rate (Normal|Inspired)
  def rate_pick(ship):  
    return R_EXTRACT_INSPIRED if if_inspired(ship) else R_EXTRACT_NORMAL
  return rate_pick, save_vimp, ship_free, pos_free, export_moves
@memo(key=lambda _ : which_turn())
def ships_mine():  return sorted(me.get_ships(), key=lambda s: s.id)

def clj_depot(lvl='info'): # turnly CLJ -> depot & terminal
  depots_mine = frozenset([me.shipyard] + me.get_dropoffs())
  crd_depots_mine = set(maps_itr([obj2pos, pos2crd], depots_mine))
  # @memo()
  # def depots_by_dist(ship): # by dist ASC
  #   return sorted(depots_mine, key=lambda depot: dist_mtn(depot, ship))
  @memo()
  def depot_nearest(ship):
    return min(depots_mine, key=lambda depot: dist_mtn(depot, ship))
  # very HACK...
  saving4depot = set()
  def if_depoting():  return len(saving4depot)>0
  @logaz('za', lvl=lvl)
  def toggle_depot(ship): # register ship as waiting2/building depot
    saving4depot.add(ship)
    return saving4depot
  # Task.term: return to depot_nearest & ignore hit @depot
  def task_terminal(ship):
    dist2return = dist_mtn(ship, depot_nearest(ship))
    ship_ahead_in_queue = lambda other: all([
      other!=ship,
      depot_nearest(other)==depot_nearest(ship),
      dist_mtn(other, depot_nearest(ship))<=dist_mtn(ship, depot_nearest(ship)), # NB ahead | equal
      ])
    # TMP really we want n_ships in quadrant that might compete for queue
    n_ships_ahead_in_queue = len(mapl(ship_ahead_in_queue, ships_mine()))//(4* len(depots_mine)) + 1
    turns2depot = dist2return + n_ships_ahead_in_queue
    terminal = (
      ship.halite_amount > 0 # TODO val(-> depot_nearest) > 0
      and turns2depot >= turns_left())
    return terminal
  def move_terminal(ship, pos_dst): # if ship to complete Task.term next
    return (get_ship2task(ship)==Task.term 
      and pos2crd(pos_dst) in crd_depots_mine)
  return task_terminal, move_terminal, if_depoting, toggle_depot, depots_mine, depot_nearest

def same_pos(o0, o1):
  return obj2pos(o0) == obj2pos(o1)
@logaz('z', lvl='info')
def get_comms(t0, lvl='info'):
  """# TIMEOUT_BREAKER
    td = time.time() - t0
    if td > TIMEOUT_BREAKER:
      log.critical('Break timeout after %.2fs: %s/%s !', td, i, len(vimps))
      break"""
  pos2val, show_value_matrix, eval_depot = clj_eval(lvl=lvl)
  rate_pick, save_vimp, ship_free, pos_free, export_moves = clj_move(get_ship2task)
  task_terminal, move_terminal, if_depoting, toggle_depot, depots_mine, depot_nearest = clj_depot()
  def s8d2val(ship, _dir, dirs_drop={}): # Ship, Dir -> val
    pos_src = ship.position
    pos_dst = p8d2pos(pos_src, _dir)
    r_fresh = 1. if _dir==DIR_O else r_curio() 
    cost_move = 0. if _dir==DIR_O else cost4move(pos_src) # TODO does this even make sense?
    if dirs_drop:
      if _dir in dirs_drop: val = ship.halite_amount
      elif _dir==DIR_O: val = ship.halite_amount * r_curio()
      else: val = ship.halite_amount * r_curio()**2
      val = val - cost_move - cost4move(pos_dst)*r_curio()
    else:
      val_pos_dst = math.ceil(rate_pick(ship) * pos2val(pos_dst)) * r_fresh
      cargo_space = const.MAX_HALITE - ship.halite_amount
      val_pos2ship = min(val_pos_dst, cargo_space)
      val = val_pos2ship - cost_move
    return round(val)
  def s8d2vimp(ship, _dir, dirs_drop={}): # Ship,Dir -> val,ship,Move,Pos
    val = s8d2val(ship, _dir, dirs_drop)
    move = ship.move(_dir)
    pos_dst = p8d2pos(ship.position, _dir)
    return (val, ship, move, pos_dst)
  def get_vimps(ship): # Ship -> [(val, ship, Move, Pos)]
    task = get_ship2task(ship)
    # set task
    if task == Task.term: # sink state
      pass # TODO?
    elif not task or ship.halite_amount==0:
      task = Task.roam
    elif task == Task.roam and ship.halite_amount >= n_drop():
      task = Task.drop
    elif task_terminal(ship):
      task = Task.term
    set_ship2task(ship, task)
    # gen vimps: seed w/ Stay unless on Depots -> don't Stay & block
    vimps = [] if same_pos(ship, depot_nearest(ship)) else [s8d2vimp(ship, DIR_O)]
    # Move-oriented depot TODO Goal-orient
    if eval_depot(ship, depot_nearest(ship)) > 0:
      if me.halite_amount>=const.DROPOFF_COST:
        vimps.append( (eval_depot(ship, depot_nearest(ship)), ship, ship.make_dropoff(), ship.position) )
      else: toggle_depot(ship)
    # TODO Move-orient -> Goal-orient
    if wont_stall(ship): # enough fuel to move
      if task in (Task.drop, Task.term):
        # _dir_drop = gm.naive_navigate(ship, me.shipyard.position)
        dirs_drop = gm.get_unsafe_moves(ship.position, depot_nearest(ship).position)
      else:
        dirs_drop = []
      for _dir in DIRS_ALL:  # add O 
        vimps.append( s8d2vimp(ship, _dir, dirs_drop=dirs_drop) )
    # HACK: only-Move must happen -> bump-up
    if len(vimps) == 1:
      v,i,m,p = vimps[0]
      vimps[0] = (v+const.SHIP_COST, i, m, p)
    return vimps
  @logaz('z', lvl=lvl)
  def get_vimps_all():  return sorted(flatmap(get_vimps, ships_mine()), reverse=True)
  def get_spawn(moves): # TODO smart eval
    if all([
      spawn_cap(),
      me.halite_amount >= const.SHIP_COST,
      pos_free(me.shipyard),
      # TMP
      which_turn() <= turn_last_spawn(),
      not if_depoting(),
      # TODO comp(sum.val_future$ship, cost_ship) > 0
      ]):
      moves.append( me.shipyard.spawn() )
    return moves

  vimps = get_vimps_all()
  # logitr([(v,i,get_ship2task(i),m,p) for (v,i,m,p) in vimps], 'vitmp.s', lvl=lvl)
  for i, (val, ship, move, pos_dst) in enumerate(vimps): # TODO improve curr GreedyAlgo
    if (ship_free(ship)
      and (pos_free(pos_dst) or move_terminal(ship, pos_dst))):
      # HACK
      if move.split()[0]==cmds.CONSTRUCT:
        if if_depoting() or gm[pos_dst].has_structure:  continue
        else: toggle_depot(ship)
      save_vimp(val, ship, move, pos_dst)
  return get_spawn(export_moves())

""" <<<Game Loop>>> """
@timit(LVL_TIMIT)
def game_loop(lvl='info'):
  t0 = time.time() # conservative?
  game.update_frame()
  log.info('Age: %.3f; r_fresh: %.3f; n_drop: %d', age(), r_curio(), n_drop())
  # Move & Spawn
  comms = get_comms(t0, lvl=lvl)
  # Submit & next
  game.end_turn(comms)
while True: game_loop()