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
from hlt.param import TURN_LAST_SPAWN
from hlt.positionals import Direction as Dir, Position as Pos, Delta as Dlt, Zone
from hlt.transform import (
  logmat,
  obj2pos, # TRANSFORM
  DIRS4, DIR_O, DIRS_ALL,
  dist, # GAME
  init_map_depot,
  scan, 
  )
from hlt.util import (
  flatmap, mapl, maps_itr, maps_func, memo, # DATA
  asrt, lvl2lgr, log, logitr, logaz, timit, # DEBUG
  )
timit = timit('warn')

spawn_cap = lambda: True # normal
# spawn_cap = lambda: which_turn()<TURN_LAST_SPAWN # FOCO turns
# spawn_cap = lambda : len(ships_mine())<2 # FOCO test
""" <<<Game Begin>>> """
game = hlt.Game()
## CONSTS
R_COST_MOVE = 1 / const.MOVE_COST_RATIO # 0.1
R_EXTRACT_NORMAL = 1 / const.EXTRACT_RATIO # 0.25
N_RADIUS_INSPIRE = const.INSPIRATION_RADIUS # 4
N_FOE_INSPIRE = const.INSPIRATION_SHIP_COUNT # 2
R_EXTRACT_INSPIRED = (1+const.INSPIRED_BONUS_MULTIPLIER) / const.EXTRACT_RATIO # 0.75
# log.warning((R_COST_MOVE,R_EXTRACT_NORMAL,N_RADIUS_INSPIRE,N_FOE_INSPIRE,R_EXTRACT_INSPIRED))
Task = enum.Enum('Task', 'roam drop raid term')
# TIMEOUT_BREAKER = 1.600 # secs
## VARS
me = game.me
gm = game.game_map
DIM_GAME = gm.width # == gm.height
DIM_MIN = 32 # [32, 64]
MAX_TURN = const.MAX_TURNS + 1 # [401, 501]
log.warning('max turn: %d; turn_last_spawn: %d', MAX_TURN, TURN_LAST_SPAWN)
which_turn = lambda : game.turn_number
turns_left = lambda : MAX_TURN - which_turn()
age = lambda : which_turn() / MAX_TURN  # [0., 1.]
r_decay = lambda : .9# + .1*age() # < .75 post-collection to avoid vasci
r_depot_decay = lambda : .8 # slower decay for depot-eval?
exp_depot_decay = lambda : 1 # cost-exponent on r_decay for eval_depot
n_perim = lambda : 2#DIM_GAME//8
n_drop = lambda : const.MAX_HALITE * .95 # ==
turn_last_spawn = lambda : TURN_LAST_SPAWN # TODO -> smarter eval sum(ship.val_future)
## PREPROC <= 30sec
# def clj_preproc():  pass # TODO static game info
game.ready('_'.join(map(str, ['b8_scan', n_perim(), r_decay()])))
## EVAL, MOVE, DEPOT
def clj_globals(lvl='info'): # global CLJ -> NB objs get recreated every turn
  sid2task = dict()  # sid:int -> Task:Enum
  def set_ship2task(ship, task): sid2task[ship.id] = task
  get_ship2task = lambda ship: sid2task.get(ship.id)
  val_depot_best = [-np.inf]
  get_vdb = lambda: val_depot_best[0]
  def set_vdb(vdb_better):
    val_depot_best[0] = vdb_better
  return set_ship2task, get_ship2task, get_vdb, set_vdb
set_ship2task, get_ship2task, get_vdb, set_vdb = clj_globals()
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
  pos_origin = obj2pos(origin)
  return [(dist, gm.normalize(pos_origin+dxy)) for dxy in dxys]
@memo()
def pos2dist8ngbrs(pos, perim) -> [(int, Pos)]:
  return flatmap(partial(gen_ring, pos), range(1, perim+1))
def clj_eval(lvl='debug'): # turnly CLJ: eval Pos
  # NB: hlt: curr tile worth; val: extended worth
  # time-decayed worth of nearby cell
  def calc_val_ngbr(dist:int, pos:Pos, exp=1):
    return round( pos2hlt(pos) * r_depot_decay()**(exp*dist) )
  @memo()
  def eval_area(obj, perim):
    pos = obj if isinstance(obj, Pos) else obj.position
    hlt_here = pos2hlt(pos)
    vals_ngbrs = [calc_val_ngbr(d, pos_ngbr, exp_depot_decay()) for d, pos_ngbr in pos2dist8ngbrs(pos, perim)]
    return round(hlt_here + sum(vals_ngbrs))
  @memo()
  # TODO just analyze map_decay(perim=d_half) + map_depot_propose
  def eval_depot(ship, depot_nearest_ship):
    dist = dist_mtn(ship, depot_nearest_ship)
    d_half = dist//2
    if d_half > 1:
      val_area_ship = eval_area(ship, d_half) * r_depot_decay()**exp_depot_decay()
      val_area_depot_nearest = eval_area(depot_nearest_ship, d_half)
      cost_depot = (const.DROPOFF_COST - ship.halite_amount)/(1-age()) + const.SHIP_COST # TMP measure of ship's future val
      return round(val_area_ship - val_area_depot_nearest - cost_depot)
    else:
      return -np.inf
  return eval_depot

def pos2xy(pos, dim=DIM_GAME): return (pos.x%dim, pos.y%dim)
def obj2xy(obj, dim=DIM_GAME): return pos2xy(obj2pos(obj), dim)
@memo(f_key=lambda objs: tuple(map(obj2xy, objs)))
def dist_mtn(obj0, obj1): return dist(gm, obj0, obj1)
# TODO expand this into cost2depot_nearest
cost4move = lambda pos_src: R_COST_MOVE * pos2hlt(pos_src)
will_stall = lambda ship: ship.halite_amount < cost4move(ship.position)
def clj_move(get_ship2task, lvl='info'): # turnly CLJ
  ship_2_task8mov8val = OrderedDict() # Ship -> (Task, move:str, val:float)
  ship_free = lambda ship:  ship not in ship_2_task8mov8val
  xy_taken = set() # xy
  take_pos = lambda obj:  xy_taken.add( pos2xy(obj2pos(obj)) )
  pos_free = lambda obj:  pos2xy(obj2pos(obj)) not in xy_taken
  moves = []
  def save_vimp(val, ship, move, pos):
    mov = move.split()[-1]
    ship_2_task8mov8val[ship] = get_ship2task(ship), mov, val
    take_pos(pos)
    moves.append(move)
  def export_moves(show=False):  # copy to prevent mutation
    moves_copied = [m for m in moves]
    if show:  logitr(moves_copied, lvl=lvl)
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
  return rate_pick, save_vimp, ship_free, take_pos, pos_free, export_moves
#TODO refresh turnly otherwise mem-leak!
@memo(f_key=lambda _: which_turn())
def ships_mine():  return sorted(me.get_ships(), key=lambda s: s.id)
@memo(f_key=lambda _: which_turn())
def pos2ship_mine():  return {s.position: s for s in ships_mine()}
def clj_depot(lvl='info'): # turnly CLJ -> depot & terminal
  depots_mine = frozenset([me.shipyard] + me.get_dropoffs())
  crd_depots_mine = set(maps_itr([obj2pos, pos2xy], depots_mine))
  @memo()
  def depot_nearest(ship):
    return min(depots_mine, key=lambda depot: dist_mtn(depot, ship))
  # very HACK...
  saving4depot = set()
  def sv4depot():  return len(saving4depot)>0
  @logaz('za', lvl=lvl)
  def toggle_depot(ship): # register ship as waiting2/building depot
    saving4depot.add(ship)
    return saving4depot
  # Task.term -> return to depot_nearest & ignore hit @depot
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
  def move_terminal(ship, pos_dst): # to complete Task.term
    return (get_ship2task(ship)==Task.term 
      and pos2xy(pos_dst) in crd_depots_mine)
  return task_terminal, move_terminal, sv4depot, toggle_depot, depots_mine, depot_nearest

def same_pos(o0, o1):
  return obj2pos(o0) == obj2pos(o1)
def obj2yx(obj, dim):
  x, y = obj2xy(obj, dim)
  return y, x
# @timit
def get_comms(t0, map_hlt, lvl='info'):
  logf=lvl2lgr(lvl)
  """# TIMEOUT_BREAKER
    td = time.time() - t0
    if td > TIMEOUT_BREAKER:
      log.critical('Break timeout after %.2fs: %s/%s !', td, i, len(vimps))
      break"""
  eval_depot = clj_eval(lvl=lvl)
  rate_pick, save_vimp, ship_free, take_pos, pos_free, export_moves = clj_move(get_ship2task)
  task_terminal, move_terminal, sv4depot, toggle_depot, depots_mine, depot_nearest = clj_depot()
  ## SCAN stuff
  # map_hlt = gm.map_hlt()
  _yx_ships = set(obj2yx(s,len(map_hlt)) for s in ships_mine())
  _yx_depots_mine = set(obj2yx(d,len(map_hlt)) for d in depots_mine)
  # OPTI? each depot only calcs enough to partial overlap another
  depot2map = {} # each depot -> map_depot 
  for depot in depots_mine:
    dist_ship_furthest2depot = max(dist_mtn(depot, s) for s in ships_mine()+[depot])
    radius_depot_scan = dist_ship_furthest2depot + n_perim() + 1
    depot2map[depot] = init_map_depot(_map=gm.map_hlt(), depot=obj2yx(depot, DIM_GAME), perim=radius_depot_scan, lvl=lvl)
  ## Goal-major Moves
  # TODO scan perim -> backtrack eval$moves -> knapsack pick
  # @timit
  def scan_maps(map_hlt, ship):
    # logf('%s scanning maps...', ship)
    yx_ship = obj2yx(ship, DIM_GAME)
    map_depot = depot2map[depot_nearest(ship)]
    map_hlt,map_depot,map_cost,map_val,map_back = scan(
      map_hlt, map_depot, yx_ship, perim=n_perim(), r_decay=r_decay(), r_cost_move=R_COST_MOVE, lvl=lvl)
    # logmat(map_hlt, 'map_hlt', lvl=lvl)
    # logmat(map_depot, 'map_depot', yx_ship, _yx_depots_mine, _yx_ships, lvl=lvl)
    # logmat(map_cost, 'map_cost', _yx_depots_mine, _yx_ships, lvl=lvl)
    logmat(map_val, 'map_val', yx_ship, _yx_depots_mine, _yx_ships, lvl=lvl)
    logmat(map_back, 'map_back: %s'%ship, yx_ship, _yx_depots_mine, _yx_ships, lvl=lvl)
    # @logaz('za', lvl=lvl)
    def eval_dir(_dir):
      pos_dst = p8d2pos(ship.position, _dir)
      yx_dst = obj2yx(pos_dst, DIM_GAME)
      cargo_space = const.MAX_HALITE-ship.halite_amount
      val_roam = min(cargo_space, int(map_back[yx_dst]))
      val_pick = min(cargo_space, math.ceil(map_hlt[yx_dst]*rate_pick(ship))) if _dir == DIR_O else 0
      # _rate_decay = r_depot_decay()**dist_mtn(pos_dst, depot_nearest(ship))
      # val_drop = math.floor(ship.halite_amount * _rate_decay)
      val_drop = ship.halite_amount 
      val_all = val_roam + val_pick + val_drop
      # logf('%s->%s: %03s, %03s, %03s => %s', ship, _dir, val_roam, val_pick, val_drop, val_all)
      return val_all
    def eval_vimp(vimp): # cargocap tiebreak 1) dist2depot 2) cost2depot
      val,ship,move,pos_dst = vimp
      yx = obj2yx(pos_dst, DIM_GAME)
      dist2depot = dist_mtn(pos_dst, depot_nearest(ship))
      # logf((ship, depot_nearest(ship), dist2depot))
      cost2depot = map_depot[yx]
      return val, -dist2depot, -cost2depot, ship, move, pos_dst
    return eval_dir, eval_vimp
  def s8d2vimp(eval_dir, ship, _dir, dirs_drop={}): # Ship,Dir -> val,ship,Move,Pos
    val = eval_dir(_dir)
    if _dir in dirs_drop: val+=ship.halite_amount
    move = ship.move(_dir)
    pos_dst = p8d2pos(ship.position, _dir)
    return (val, ship, move, pos_dst)
  # @timit
  def get_vimps(ship): # Ship -> [(val, ship, Move, Pos)]
    ## TASK
    task = get_ship2task(ship)
    if task == Task.term: # sink state
      pass # TODO?
    elif not task or ship.halite_amount==0: # newborn or after Drop
      task = Task.roam
    elif task == Task.roam and ship.halite_amount >= n_drop(): # TODO?
      task = Task.drop
    elif task_terminal(ship):
      task = Task.term
    set_ship2task(ship, task)
    ## MOVE: seed w/ Stay unless on Depots -> don't Stay & block!
    eval_dir, eval_vimp = scan_maps(map_hlt, ship)
    vimps = [] if same_pos(ship, depot_nearest(ship)) else [s8d2vimp(eval_dir, ship, DIR_O)]
    # Move-oriented depot TODO Goal-orient
    val_depot = eval_depot(ship, depot_nearest(ship))
    # debug
    if val_depot > get_vdb():
      set_vdb(val_depot)
      log.warning('better val_depot_best! %s => %s', ship, val_depot)
    if val_depot > 0:
      if me.halite_amount>=const.DROPOFF_COST:
        vimps.append( (val_depot, ship, ship.make_dropoff(), ship.position) )
      else: toggle_depot(ship)
    if not will_stall(ship): # enough fuel to move
      if task in (Task.drop, Task.term):
        # dirs_drop = gm.naive_navigate(ship, depot_nearest(ship).position)
        dirs_drop = gm.get_unsafe_moves(ship.position, depot_nearest(ship).position)
      else:
        dirs_drop = []
      for _dir in DIRS4:
        vimps.append( s8d2vimp(eval_dir, ship, _dir, dirs_drop=dirs_drop) )
    # HACK: bump-up only-Move otherwise Ship might be forced to Stay & get hit!
    if len(vimps) == 1:
      [(v,i,m,p)] = vimps
      vimps = [(v+const.SHIP_COST, i, m, p)]
    # HACK break val-tie w/ 1) min dist2depot 2) min cost2depot
    vdcimps = mapl(eval_vimp, vimps) 
    return vdcimps
  # @timit
  def get_vimps_all():  return sorted(flatmap(get_vimps, ships_mine()), reverse=True)
  def get_spawn(moves): # TODO smart eval
    if all([
      spawn_cap(),
      # HACK save4depot up to cost for 1
      ((not sv4depot() and me.halite_amount >= const.SHIP_COST)
        or (me.halite_amount >=const.DROPOFF_COST+const.SHIP_COST)),
      pos_free(me.shipyard),
      # TODO comp(sum.val_future$ship, cost_ship) > 0
      which_turn() <= turn_last_spawn(),
      ]):
      moves.append( me.shipyard.spawn() )
    return moves
  vdcimps = get_vimps_all()
  # @logaz('za', lvl=lvl)
  def can_vacate(pos): # if ship_mine @pos can move out - don't take spot otherwise
    ship_mine = pos2ship_mine().get(pos)
    if not ship_mine:  return True
    elif will_stall(ship_mine):  return False
    else: return any(map(pos_free, [p for (d,p) in gen_ring(pos, 1)]))
  # TODO greedy -> knapsack w/ dynamic re-eval
  # TODO pos_free -> 1) intertemporal 2) val-based
  # TODO use priority-queue + auto-promote last-move
  def alloc_moves(vdcimps, show=True):
    ship2n_moves = Counter(ship for v,d,c,ship,m,p in vdcimps)
    # logitr(ship2n_moves, 'ship2n_moves', lvl=lvl)
    for i, (val, dist2depot, cost2depot, ship, move, pos_dst) in enumerate(vdcimps): # TODO improve curr GreedyAlgo
      # dont take pos_dst ship_mine's final-move
      ship_on_pos_dst = pos2ship_mine().get(pos_dst)
      if ship_on_pos_dst and ship!=ship_on_pos_dst and ship2n_moves[ship_on_pos_dst]==1:
        log.warning('skip: [%s] %s > %s << %s', val, ship, pos_dst, ship_on_pos_dst)
        continue
      str_move = str((val, dist2depot, cost2depot, ship, get_ship2task(ship), move, pos_dst))
      if (ship_free(ship)
        and (pos_free(pos_dst) or move_terminal(ship, pos_dst))):
        # HACK: build <= 1 Depot/turn
        if move.split()[0]==cmds.CONSTRUCT:
          if sv4depot() or gm[pos_dst].has_structure:  continue # next
          else:
            log.warning('Making depot @%s', pos_dst)
            toggle_depot(ship)
        # move approved
        save_vimp(val, ship, move, pos_dst) # -> clj_move
        ship2n_moves[ship] -= 1
        # logitr(ship2n_moves, 'ship2n_moves', lvl=lvl)
        str_move = '> %s'%str_move
      if show:  logf(str_move)
  alloc_moves(vdcimps)
  mvs8spwn = get_spawn(export_moves())
  logitr(mvs8spwn, lvl=lvl)
  return mvs8spwn

""" <<<Game Loop>>> """
@timit
def game_loop(lvl='info'):
  t0 = time.time() # conservative?
  map_hlt = game.update_frame()
  log.info('Age: %.3f; r_fresh: %.3f; n_drop: %d', age(), r_decay(), n_drop())
  # Move & Spawn
  comms = get_comms(t0, map_hlt, lvl=lvl)
  # Submit & next
  game.end_turn(comms)
while True: game_loop()