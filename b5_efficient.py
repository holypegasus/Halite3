#!/usr/bin/env python3.6
import logging as log
import random, traceback
from collections import Counter, OrderedDict
from enum import Enum
from itertools import chain, product
from functools import partial
from math import ceil
from statistics import mean
from time import time

import pandas as pd

import hlt
from hlt import constants as const
from hlt.positionals import Direction, Position
N = Direction.North
E = Direction.East
W = Direction.West
S = Direction.South
O = Direction.Still
from hlt.util import timit
Task = Enum('Task', 'roam drop depot term')
## TODO -> utils
def logret(header='', log_itr=False, show=True):
  def wrap_func(f):
    def wrap_args(*args, **kwargs):
      res = f(*args, **kwargs)
      if log_itr:
        logitr(res, header, show)
      else:
        log.warning('%s: %s & %s => %s', f.__name__, args, kwargs, res)
      return res
    return wrap_args
  return wrap_func
def logitr(itr, header='', show=True):
  if isinstance(itr, dict):
    strs_itr = ['%s -> %s'%(k, v) for k, v in itr.items()]
  elif hasattr(itr, '__iter__'):
    strs_itr = map(str, itr)
  else:
    strs_itr = [str(itr)]
  str_itr = '\n'.join(strs_itr)
  log.debug('%s: [%s]%s', header, len(itr), '\n'+str_itr if show else '')
def automemo(func_key=lambda k:k, dict_type=dict):
  d = dict_type()
  def wrap_func(f):
    def wrap_arg(arg):
      k = func_key(arg)
      if k in d:
        log.info('%s -> %s', k, d[k])
        return d[k]
      else:
        d[k] = f(arg)
        log.info('%s +> %s', k, d[k])
        return d[k]
    return wrap_arg
  return wrap_func
def flatmap(func, itr): return chain(*map(func, itr))
def mapl(func, itr):  return list(map(func, itr)) # actualize iterator
def maps(funcs, itr): # map multiple functions over iterable
  for f in funcs: itr = map(f, itr)
  return itr

""" <<<Game Begin>>> """
game = hlt.Game()
# TODO global preproc
game.ready("5_Efficient")

## GLOBAL
me = game.me
game_map = game.game_map
DIM_GAME = game_map.width
DIM_MIN = 32 # [32, 64]
MAX_TURN = 401 + 100 * max(0, (DIM_GAME / DIM_MIN - 1)) # [401, 501]
turns_left = lambda : MAX_TURN - game.turn_number
age = lambda : game.turn_number / MAX_TURN  # [0., 1.]
# NB decr curio -> start idling!
# rate_time = lambda : .5 + age() # [.5, 0.]: incr curio
# rate_time = lambda : 1 - age() # [1, 0.]: decr curio
rate_time = lambda : .9 # constant curio
# n_drop = lambda : const.MAX_HALITE * (.75 - .25*age())
n_drop = lambda : const.MAX_HALITE * .95 # TODO

## EVAL
# move_random = lambda : random.choice(Direction.get_all_cardinals())
obj2pos = lambda o: o if isinstance(o, Position) else o.position
pos2crd = lambda pos: (pos.x%DIM_GAME, pos.y%DIM_GAME)
pos2hlt = lambda p: game_map[p].halite_amount
def p8d2pos(pos_src, Dir): # Pos,Dir -> Pos
  # log.info((pos_src, Dir))
  pos_dst = pos_src.directional_offset(Dir)
  return game_map.normalize(pos_dst)
crds_all = tuple(product(list(range(DIM_GAME)), list(range(DIM_GAME))))
def pos2ngbrs(pos, perim=1): # Pos -> [Pos]
  p8d2pos_part = partial(p8d2pos, pos)
  pos_ngbrs = pos.get_surrounding_cardinals()
  assert len(pos_ngbrs)==4, pos_ngbrs
  # logitr(pos_ngbrs, '%s.ngbrs'%pos)
  return pos_ngbrs
def clj_eval(): # perturn CLJ: eval Pos
  # NB: hlt: curr tile worth; val: extended worth
  calc_val_ngbr = lambda pos: rate_time() * pos2hlt(pos)
  def crd2val(crd): # 
    x, y = crd
    pos = Position(x, y)
    hlt_self = pos2hlt(pos)
    # hlts_ngbrs = map(pos2hlt, pos2ngbrs(pos))
    vals_ngbrs = map(calc_val_ngbr, pos2ngbrs(pos))
    # val_total = round(hlt_self + mean(vals_ngbrs), 2)
    val_total = round(hlt_self + max(vals_ngbrs), 2)
    # log.info('%s -> %s', (pos, hlt_self, hlt_ngbrs), val_total)
    return val_total
  mat_vals = [[crd2val((x,y)) for x in range(DIM_GAME)] 
    for y in range(DIM_GAME)] # NB [y][x]
  df_vals = pd.DataFrame(mat_vals) # NB [x][y]
  def pos2val(pos, perim=1):
    # TODO compare strength of Voronoi-zones -> if build Depot



    return df_vals[pos.x][pos.y]
  def show_value_matrix(): log.debug('Values:\n%s', df_vals)
  # def show(pos, perim=3): log.info('vals %s-near %s:\n', perim, pos, )
  return pos2val, show_value_matrix

ship2id = lambda ship: ship2id
def dist_mtn(obj0, obj1, show=False): # Manhattan
  pos0 = obj2pos(obj0)
  pos1 = obj2pos(obj1)
  dx = abs(pos0.x - pos1.x)
  dy = abs(pos0.y - pos1.y)
  if show:  log.info((pos0, pos1, dx, dy))
  return dx+dy
def clj_inspire(): # perturn CLJ -> Inspire status & utils
  # record_inspired = dict()
  def get_ships_near(ship, perim=4):  # foe | mine
    ships_all = [s for p in game.players.values() for s in p.get_ships()]
    # logitr(ships_all, 'ships_all', False)
    in_range = lambda s: s!=ship and dist_mtn(ship, s) <= perim 
    return filter(in_range, ships_all)
  @automemo(ship2id)
  # @logret('inspired?')
  def if_inspired(ship):
    is_ship_foe = lambda s: s.owner != me.id
    ships_foe = list(filter(is_ship_foe, get_ships_near(ship)))
    # logitr(ships_foe, 'ships_foe near %s'%ship, False)
    return len(ships_foe) > 1
  return if_inspired

cost4move = lambda pos_src: .1 * pos2hlt(pos_src)
wont_stall = lambda ship: cost4move(ship.position) <= ship.halite_amount
def clj_param_pick(if_inspired): # perturn CLJ -> Halite pick-rate (Normal | Inspired)
  record_pick = dict()
  @automemo(ship2id)
  def rate_pick(ship):  return .75 if if_inspired(ship) else .25
  return rate_pick

## MOVE
PREC = 3
def clj_globals(): # CLJ -> TMP tasks
  sid2task = dict()  # global; sid:int -> Task:Enum
  def set_sid2task(sid, task):  sid2task[sid] = task
  get_sid2task = lambda sid: sid2task.get(sid)
  def update_globals():
    # SID2TASK = {ship.id: SID2TASK[ship.id] for ship in me.get_ships()}
    # log.warning(sid2task)
    pass
  def show_EOT_stats():
    task2count = Counter(sid2task.values())
    log.info(task2count)
  return set_sid2task, get_sid2task, update_globals, show_EOT_stats
set_sid2task, get_sid2task, update_globals, show_EOT_stats = clj_globals()
ships_mine = lambda : sorted(me.get_ships(), key=lambda s: s.id)
def clj_track_turn(): # perturn CLJ -> prevent self hits
  sid2pos8val = OrderedDict() # sid:int -> (crd:(int, int), val:float)
  crds_taken = set() # [crd]:(int, int)
  moves = []
  def save(val, sid, move, pos):
    sid2pos8val[sid] = (pos, val)
    crds_taken.add(pos2crd(pos))
    moves.append(move)
  def sid_free(sid):  return sid not in sid2pos8val
  def pos_free(obj):
    pos = obj if isinstance(obj, Position) else obj.position
    return pos2crd(pos) not in crds_taken
  def export_moves(show=False):  # copy to prevent mutation
    moves_copied = [m for m in moves]
    if show:  logitr(moves_copied)
    return moves_copied
  return save, sid_free, pos_free, export_moves
def clj_depot(): # CLJ -> terminal utils
  depots_mine = [me.shipyard] + me.get_dropoffs()
  crd_depots_mine = set(maps([obj2pos, pos2crd], depots_mine))
  @automemo(func_key=ship2id)
  # @logret()
  def depot_nearest(ship): # TODO
    return min(depots_mine, key=lambda d: dist_mtn(d, ship))
  saving4depot = lambda : False
  # Task.term: return to depot_nearest & ignore hit @depot
  buffer_terminal = 3
  # @logret()
  def task_terminal(ship):
    turns2depot = dist_mtn(ship, depot_nearest(ship)) + buffer_terminal
    terminal = (
      ship.halite_amount > 0 # TODO val(depot_nearest) > 0
      and turns2depot >= turns_left())
    return terminal
  def move_terminal(sid, pos_dst): # if ship to complete Task.term next
    return (get_sid2task(sid)==Task.term 
      and pos2crd(pos_dst) in crd_depots_mine)
  return task_terminal, move_terminal, saving4depot
task_terminal, move_terminal, saving4depot = clj_depot()
def get_moves(pos2val, rate_pick, if_inspired):
  save, sid_free, pos_free, export_moves = clj_track_turn()
  task_terminal, move_terminal, saving4depot = clj_depot()

  def s8d2val(ship, Dir): # Pos,Dir -> val
    pos_src = ship.position
    pos_dst = p8d2pos(pos_src, Dir)
    r_fresh = 1. if Dir==O else rate_time() 
    cost_move = 0. if Dir==O else -(
      2*cost4move(pos_src)) # TODO does this even make sense?
    assert cost_move <= 0, (cost_move, 0)
    # log.debug('%s val: %s', pos_dst, pos2val(pos_dst))
    val_pos_dst = ceil(rate_pick(ship) * pos2val(pos_dst)) * r_fresh
    # log.debug('%s -> %s: val_pos_dst: %.1f; cost_move: %.1f', pos_src, Dir, val_pos_dst, cost_move)
    return val_pos_dst + cost_move
  def s8d2vimp(ship, Dir, drop=False): # Ship,Dir -> val,sid,Move,Pos
    # log.debug('drop? %s', drop)
    val = s8d2val(ship, Dir)
    if drop:
      val = val + ship.halite_amount
    val = round(val, PREC)
    # log.debug(val)
    move = ship.move(Dir)
    pos_dst = p8d2pos(ship.position, Dir)
    return (val, ship.id, move, pos_dst)
  def get_vimps(ship): # Ship -> [(val, sid, Move, Pos)]
    sid = ship.id
    task = get_sid2task(ship.id)
    # set task
    if task == Task.term: # sink state
      pass
    elif not task or ship.halite_amount == 0:
      task = Task.roam
    elif task == Task.roam and ship.halite_amount >= n_drop():
      task = Task.drop
    elif task_terminal(ship):
      task = Task.term
    set_sid2task(sid, task)
    log.debug('%s -> %s', ship, task)
    # gen vimps: seed w/ Stay unless on Shipyard -> don't Stay & block
    vimps = [] if ship.position==me.shipyard.position else [s8d2vimp(ship, O)]
    if wont_stall(ship): # enough fuel to move
      if task in (Task.drop, Task.term):
        # _dir_drop = game_map.naive_navigate(ship, me.shipyard.position)
        Dirs_drop = game_map.get_unsafe_moves(ship.position, me.shipyard.position)
      else:
        Dirs_drop = []
      for Dir in [E, N, W, S]:  # O already seeded
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
  for val, sid, move, pos_dst in vimps: # TODO improve curr GreedyAlgo
    if (sid_free(sid)
      and (pos_free(pos_dst) or move_terminal(sid, pos_dst))):
      save(val, sid, move, pos_dst)
  return export_moves(), pos_free

def get_spawn(moves, pos_free):
  if all([
    game.turn_number <= .5 * MAX_TURN,
    me.halite_amount >= const.SHIP_COST,
    pos_free(me.shipyard),
    not saving4depot(),
    ]):
    moves.append( me.shipyard.spawn() )
  return moves


""" <<<Game Loop>>> """
@timit()
def game_loop():
  game.update_frame()
  log.info('Age: %.3f; r_fresh: %.3f; n_drop: %d', age(), rate_time(), n_drop())
  log.debug(game_map)
  # Memo refresh
  # update_globals()
  pos2val, show_value_matrix = clj_eval()
  show_value_matrix()
  if_inspired = clj_inspire()
  rate_pick = clj_param_pick(if_inspired)
  # Move & Spawn
  moves, pos_free = get_moves(pos2val, rate_pick, if_inspired)
  moves_and_spawn = get_spawn(moves, pos_free)
  # Submit & next
  # show_EOT_stats()
  game.end_turn(moves_and_spawn)
while True: game_loop()

