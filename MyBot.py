#!/usr/bin/env python3.6
import enum, random, traceback
from collections import Counter, OrderedDict
from itertools import chain, product
from functools import partial
import math
from statistics import mean
from typing import Tuple, List
Crd = Tuple[int, int]

import pandas as pd

import hlt
from hlt import constants as const
from hlt.positionals import Direction as Dir, Position as Pos
Dirs4 = [Dir.North, Dir.East, Dir.West, Dir.South]
O = Dir.Still
from hlt.util import *
LVL_TIMIT = 'warn'
Task = enum.Enum('Task', 'roam drop depot term')
""" <<<Game Begin>>> """
game = hlt.Game()
# TODO global preproc
game.ready("6_Depot")
## GLOBAL
me = game.me
game_map = game.game_map
DIM_GAME = game_map.width
DIM_MIN = 32 # [32, 64]
MAX_TURN = 401 + 100 * max(0, (DIM_GAME / DIM_MIN - 1)) # [401, 501]
turns_left = lambda : MAX_TURN - game.turn_number
age = lambda : game.turn_number / MAX_TURN  # [0., 1.]
# NB decr curio -> start idling!
# r_curio = lambda : .8 + .2*age() # ++ curio
# r_curio = lambda : 1 - age() # -- curio
r_curio = lambda : .9 # == curio
# n_drop = lambda : const.MAX_HALITE * (.75 + .2*age()) # ++ 
# n_drop = lambda : const.MAX_HALITE * (.95 - .45*age()) # --
n_drop = lambda : const.MAX_HALITE * .95 # ==
# n_perim = lambda : round(2 + 2*age())
n_perim = lambda : 2
exp_depot = lambda : 1.5 # cost-exponent on r_curio for eval_depot
## EVAL
# move_random = lambda : random.choice(Dir.get_all_cardinals())
obj2pos = lambda o: o if isinstance(o, Pos) else o.position
pos2crd = lambda pos: (pos.x%DIM_GAME, pos.y%DIM_GAME)
pos2hlt = lambda p: game_map[p].halite_amount
def p8d2pos(pos_src, Dir): # Pos,Dir -> Pos
  # log.info((pos_src, Dir))
  pos_dst = pos_src.directional_offset(Dir)
  return game_map.normalize(pos_dst)
crds_all = tuple(product(list(range(DIM_GAME)), list(range(DIM_GAME))))

def pos8crd2pos(pos: Pos, crd: Crd) -> Pos: return game_map.normalize(pos + Pos(*crd))
@automemo()
def gen_ngbr_dxys(dist):
  dxs = range(-dist, dist+1)
  dys = range(-dist, dist+1)
  dxys = sorted(set((dx,dy) for dx in dxs for dy in dys if abs(dx)+abs(dy)==dist))
  return dxys
@automemo()
def gen_ring(origin, dist): # ring of Pos dist-away from origin [4*d]
  dxys = gen_ngbr_dxys(dist)
  return [(dist, pos8crd2pos(origin, dxy)) for dxy in dxys]
@automemo()
def pos2dist8ngbrs(pos, perim) -> [(int, Pos)]:
  part_gen_ring = partial(gen_ring, pos)
  return flatmap(part_gen_ring, range(1, perim+1))
# @timit(LVL_TIMIT) # ! bulk of processing here
def clj_eval(lvl='debug'): # perturn CLJ: eval Pos
  # NB: hlt: curr tile worth; val: extended worth
  # @automemo(lvl=lvl)
  def calc_val_ngbr(dist:int, pos:Pos, exp=1):
    return round(pos2hlt(pos) * (r_curio()**exp)**dist)
  # @logret(lvl)
  def crd2val(crd, perim=n_perim()): # TODO improv!
    x, y = crd
    pos = Pos(x, y)
    hlt_self = pos2hlt(pos)
    vals_ngbrs = [calc_val_ngbr(d, pos_ngbr) for d, pos_ngbr in pos2dist8ngbrs(pos, perim)]
    # val_total = round(hlt_self + mean(vals_ngbrs), 2)
    val_total = round(hlt_self + mean(vals_ngbrs))
    return val_total
  @automemo()
  def eval_area(obj, perim):
    pos = obj if isinstance(obj, Pos) else obj.position
    hlt_self = pos2hlt(pos)
    vals_ngbrs = [calc_val_ngbr(d, pos_ngbr, exp_depot()) for d, pos_ngbr in pos2dist8ngbrs(pos, perim)]
    val_total = round(hlt_self + sum(vals_ngbrs))
    return val_total
  def pos2val(pos, perim=1):
    # TODO compare strength of Voronoi-zones -> if build Depot
    return mat_vals[pos.x][pos.y]
  def show_value_matrix(): 
    df_vals = pd.DataFrame(mat_vals) # NB [x][y]
    # annotate
    df_show = df_vals.copy()
    pos_shipyard = me.shipyard.position
    df_show[pos_shipyard.x][pos_shipyard.y] = '{%s}'%(df_show[pos_shipyard.x][pos_shipyard.y])
    for s in ships_mine():
      df_show[s.position.x][s.position.y] = '[%s]'%(df_show[s.position.x][s.position.y])
    LVL2LGR[lvl]('\n%s', df_show)
  @logret(lvl)
  def eval_depot(ship, depot_nearest_ship): # TMP refine!
    d = dist_mtn(ship, depot_nearest_ship)
    d_half = int(d/2)
    if d_half > 0:
      val_ship = eval_area(ship, d_half) + ship.halite_amount - const.SHIP_COST
      val_shipyard = eval_area(depot_nearest_ship, d_half)
      return round(val_ship - val_shipyard - const.DROPOFF_COST/(1-age()))
    else:
      return -1
  mat_vals = [[crd2val((x,y)) 
    for y in range(DIM_GAME)] 
    for x in range(DIM_GAME)] # NB get[x][y]
  return pos2val, show_value_matrix, eval_depot
ship2id = lambda ship: ship2id

@automemo()
def dist_mtn(obj0, obj1): # Manhattan
  pos0 = obj2pos(obj0)
  pos1 = obj2pos(obj1)
  dx = abs(pos0.x - pos1.x)
  dy = abs(pos0.y - pos1.y)
  return min(dx, DIM_GAME-dx) + min(dy, DIM_GAME-dy)
# @timit(LVL_TIMIT)
def clj_inspire(): # perturn CLJ -> Inspire status & utils
  # record_inspired = dict()
  def get_ships_near(ship, perim=4):  # foe | mine
    ships_all = [s for p in game.players.values() for s in p.get_ships()]
    # logitr(ships_all, 'ships_all', False)
    in_range = lambda s: s!=ship and dist_mtn(ship, s) <= perim 
    return filter(in_range, ships_all)
  @automemo(ship2id)
  # @logret()
  def if_inspired(ship):
    is_ship_foe = lambda s: s.owner != me.id
    ships_foe = list(filter(is_ship_foe, get_ships_near(ship)))
    # logitr(ships_foe, 'ships_foe near %s'%ship, False)
    return len(ships_foe) > 1
  return if_inspired

cost4move = lambda pos_src: .1 * pos2hlt(pos_src)
wont_stall = lambda ship: cost4move(ship.position) <= ship.halite_amount
# @timit(LVL_TIMIT)
def clj_param_pick(if_inspired): # perturn CLJ -> Halite pick-rate (Normal|Inspired)
  record_pick = dict()
  @automemo(ship2id)
  def rate_pick(ship):  return .75 if if_inspired(ship) else .25
  return rate_pick

## MOVE
def clj_globals(lvl='info'): # CLJ -> TMP tasks
  sid2task = dict()  # global; sid:int -> Task:Enum
  def set_sid2task(sid, task):
    # log.debug('%s -> %s', ship, task)
    sid2task[sid] = task
  get_sid2task = lambda sid: sid2task.get(sid)
  def show_EOT_stats():
    logitr(sid2task, 'sid2task', lvl=lvl)
    # logitr(Counter(sid2task.values()), 'task2count', lvl=lvl)
  return set_sid2task, get_sid2task, show_EOT_stats
set_sid2task, get_sid2task, show_EOT_stats = clj_globals()
ships_mine = lambda : sorted(me.get_ships(), key=lambda s: s.id)
# @timit(LVL_TIMIT)
def clj_track_turn(get_sid2task, lvl='info'): # perturn CLJ -> prevent self hits
  sid_2_task8mov8val = OrderedDict() # sid:int -> (move:str, val:float)
  crds_taken = set() # [crd]:(int, int)
  moves = []
  def save(val, sid, move, pos):
    mov = move.split()[-1]
    sid_2_task8mov8val[sid] = get_sid2task(sid), mov, val
    crds_taken.add(pos2crd(pos))
    moves.append(move)
  sid_free = lambda sid:  sid not in sid_2_task8mov8val
  def pos_free(obj):
    pos = obj if isinstance(obj, Pos) else obj.position
    return pos2crd(pos) not in crds_taken
  def export_moves(show=False):  # copy to prevent mutation
    moves_copied = [m for m in moves]
    if show:  logitr(moves_copied)
    return moves_copied
  def show_ship_asmts():
    logitr(sid_2_task8mov8val, 'sid_2_task8mov8val', lvl=lvl)
  return save, sid_free, pos_free, export_moves, show_ship_asmts
# @timit(LVL_TIMIT)
def clj_depot(lvl='info'): # CLJ -> terminal utils
  depots_mine = [me.shipyard] + me.get_dropoffs()
  crd_depots_mine = set(maps([obj2pos, pos2crd], depots_mine))
  @automemo()
  def depots_by_dist(ship): # by dist ASC
    return sorted(depots_mine, key=lambda depot: dist_mtn(depot, ship))
  saving4depot = set()
  def if_depoting():  return len(saving4depot)>0
  @logret(lvl=lvl)
  def toggle_depot(sid):
    saving4depot.add(sid)
    return saving4depot
  # Task.term: return to depot_nearest & ignore hit @depot
  # @logret()
  def task_terminal(ship, depot_nearest_ship):
    buffer_terminal = 3
    turns2depot = dist_mtn(ship, depot_nearest_ship) + buffer_terminal
    terminal = (
      ship.halite_amount > 0 # TODO val(depot_nearest) > 0
      and turns2depot >= turns_left())
    return terminal
  def move_terminal(sid, pos_dst): # if ship to complete Task.term next
    return (get_sid2task(sid)==Task.term 
      and pos2crd(pos_dst) in crd_depots_mine)
  return task_terminal, move_terminal, if_depoting, toggle_depot, depots_by_dist
task_terminal, move_terminal, if_depoting, toggle_depot, depots_by_dist = clj_depot()

# @timit(LVL_TIMIT)
def get_moves(pos2val, rate_pick, if_inspired, eval_depot):
  save, sid_free, pos_free, export_moves, show_ship_asmts = clj_track_turn(get_sid2task)
  task_terminal, move_terminal, if_depoting, toggle_depot, depots_by_dist = clj_depot()

  def s8d2val(ship, Dir): # Pos,Dir -> val
    pos_src = ship.position
    pos_dst = p8d2pos(pos_src, Dir)
    r_fresh = 1. if Dir==O else r_curio() 
    cost_move = 0. if Dir==O else -(
      2*cost4move(pos_src)) # TODO does this even make sense?
    assert cost_move <= 0, (cost_move, 0)
    # log.debug('%s val: %s', pos_dst, pos2val(pos_dst))
    val_pos_dst = math.ceil(rate_pick(ship) * pos2val(pos_dst)) * r_fresh
    # log.debug('%s -> %s: val_pos_dst: %.1f; cost_move: %.1f', pos_src, Dir, val_pos_dst, cost_move)
    return val_pos_dst + cost_move
  def s8d2vimp(ship, Dir, drop=False): # Ship,Dir -> val,sid,Move,Pos
    # log.debug('drop? %s', drop)
    val = s8d2val(ship, Dir)
    if drop:
      val = val + ship.halite_amount
    val = round(val)
    # log.debug(val)
    move = ship.move(Dir)
    pos_dst = p8d2pos(ship.position, Dir)
    return (val, ship.id, move, pos_dst)
  def get_vimps(ship): # Ship -> [(val, sid, Move, Pos)]
    sid = ship.id
    task = get_sid2task(ship.id)
    depot_nearest_ship = depots_by_dist(ship)[0]
    # set task
    if task == Task.term: # sink state
      pass
    elif not task or ship.halite_amount == 0:
      task = Task.roam
    elif task == Task.roam and ship.halite_amount >= n_drop():
      task = Task.drop
    elif task_terminal(ship, depot_nearest_ship):
      task = Task.term
    set_sid2task(sid, task)
    # gen vimps: seed w/ Stay unless on Shipyard -> don't Stay & block
    pos_depots = map(obj2pos, depots_by_dist(ship))
    vimps = [] if ship.position in pos_depots else [s8d2vimp(ship, O)]
    # TMP depot
    # if eval_depot(ship) > 0 and me.halite_amount>=const.DROPOFF_COST:
    if eval_depot(ship, depot_nearest_ship) > 0:
      if me.halite_amount>=const.DROPOFF_COST:
        vimps.append( (eval_depot(ship, depot_nearest_ship), ship.id, ship.make_dropoff(), ship.position) )
      else:
        toggle_depot(ship.id) # NOT updating saving4depot!!!
    if wont_stall(ship): # enough fuel to move
      if task in (Task.drop, Task.term):
        # _dir_drop = game_map.naive_navigate(ship, me.shipyard.position)
        Dirs_drop = game_map.get_unsafe_moves(ship.position, depot_nearest_ship.position)
      else:
        Dirs_drop = []
      for Dir in Dirs4:  # O already seeded
        # log.debug('%s vs %s: %s', Dir, Dirs_drop, Dir==Dirs_drop)
        vimps.append(s8d2vimp(ship, Dir, drop=Dir in Dirs_drop))
    # HACK: only-Move must happen -> bump-up
    if len(vimps) == 1:
      v,i,m,p = vimps[0]
      vimps[0] = (v+const.SHIP_COST, i, m, p)
    logitr(sorted(vimps, reverse=True), 'vimps <- ship')
    return vimps

  vimps = sorted(flatmap(get_vimps, ships_mine()), reverse=True)
  logitr(vimps, 'vimps <- turn')
  already_building_depot = False # TMP prevents multiple depot same turn
  logitr(vimps)
  for val, sid, move, pos_dst in vimps: # TODO improve curr GreedyAlgo
    if (sid_free(sid)
      and (pos_free(pos_dst) or move_terminal(sid, pos_dst))):
      # HACK
      if move.split()[0]=='c':
        if already_building_depot:  continue
        else:
          already_building_depot = True
          toggle_depot(sid)
      save(val, sid, move, pos_dst)
  show_ship_asmts()
  return export_moves(), pos_free, if_depoting

def get_spawn(moves, pos_free, if_depoting):
  if all([
    game.turn_number <= .5 * MAX_TURN,
    me.halite_amount >= const.SHIP_COST,
    pos_free(me.shipyard),
    not if_depoting(),
    # TODO comp(sum.val_future$ship, cost_ship) > 0
    ]):
    moves.append( me.shipyard.spawn() )
  return moves
""" <<<Game Loop>>> """
@timit('warn')
def game_loop(lvl='info'):
  game.update_frame()
  log.info('Age: %.3f; r_fresh: %.3f; n_drop: %d', age(), r_curio(), n_drop())
  log.debug(game_map)
  # Memo refresh
  pos2val, show_value_matrix, eval_depot = clj_eval(lvl=lvl)
  # show_value_matrix()
  if_inspired = clj_inspire()
  rate_pick = clj_param_pick(if_inspired)
  # Move & Spawn
  moves, pos_free, if_depoting = get_moves(pos2val, rate_pick, if_inspired, eval_depot)
  moves_and_spawn = get_spawn(moves, pos_free, if_depoting)
  # logitr(moves_and_spawn, lvl=lvl)
  # Submit & next
  # show_EOT_stats()
  game.end_turn(moves_and_spawn)
while True: game_loop()