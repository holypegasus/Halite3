#!/usr/bin/env python3.6
import logging as log
# log.getLogger().setLevel(log.WARNING) # silence -> upload
import random
from collections import OrderedDict
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
Task = Enum('Task', 'roam drop')
## Utils
# TODO recursive indent logitr
def logitr(itr, header='', show=True, lvl=0):
  str_title = '%s: [%s]' %(header, len(itr))
  if isinstance(itr, dict):
    strs_body = ['%s -> %s'%(k, v) for k, v in sorted(itr.items())]
  elif hasattr(itr, '__iter__'):
    strs_body = mapl(str, itr)
  else:
    strs_body = '%s%s'%(lvl*'\t', itr)
  strs_body = strs_body if show else []
  str_all = '\n'.join([str_title] + strs_body)
  log.debug(str_all)
def timit(f):
  def timed(*args, **kwargs):
    t0 = time()
    res = f(*args, **kwargs)
    t1 = time()
    log.info('%s: %.3fs', f.__name__, t1-t0)
    return res
  return timed
flatten = lambda lists: chain(*lists)
def flatmap(func, itr): return flatten(map(func, itr))
def mapl(func, itr):  return list(map(func, itr)) # actualize iterator
""" <<<Game Begin>>> """
game = hlt.Game()
# TODO preproc
game.ready("3_Convolve")
## GLOBAL
me = game.me
game_map = game.game_map
DIM_GAME = game_map.width
# dim: [32, 64]; n_turns: [401, 501]
DIM_MIN = 32
MAX_TURN = 401 + (DIM_GAME / DIM_MIN - 1) * 100
age = lambda : game.turn_number / MAX_TURN  # [0., 1.]
# NB decr curio -> start idling!
# rate_fresh = lambda : .5 + age() # [.5, 0.]: incr curio
# rate_fresh = lambda : 1 - age() # [1, 0.]: decr curio
rate_fresh = lambda : .9 # constant curio
# n_drop = lambda : const.MAX_HALITE * (.75 - .25*age())
n_drop = lambda :const.MAX_HALITE * .75
# TODO memoize within rates-closure?

## INTERACT
def dist(ship0, ship1):
  pos0 = ship0.position
  pos1 = ship1.position
  dx = (pos0.x - pos1.x) % DIM_GAME
  dy = (pos0.y - pos1.y) % DIM_GAME
  return dx+dy
def get_ships_near(ship, perim=4):  # foe | mine
  ships_all = [s for p in game.players.values() for s in p.get_ships()]
  # logitr(ships_all, 'ships_all', False)
  in_range = lambda s: s!=ship and dist(ship, s) <= perim 
  return filter(in_range, ships_all)
def clj_inspire(): # perturn CLJ -> Inspire status & utils
  record_inspired = dict()
  def if_inspired(ship):
    inspired = record_inspired.get(ship.id)
    if inspired==None:
      is_ship_foe = lambda s: s.owner != me.id
      ships_foe = list(filter(is_ship_foe, get_ships_near(ship)))
      # logitr(ships_foe, 'ships_foe near %s'%ship, False)
      inspired = len(ships_foe)>1
      record_inspired[ship.id] = inspired
      # if inspired:  log.warning('%s NSPYR!', ship.id)
    return inspired
  return if_inspired
## EVAL
# move_random = lambda : random.choice(Direction.get_all_cardinals())
def p8d2pos(pos_src, Dir): # Pos,Dir -> Pos
  # log.info((pos_src, Dir))
  pos_dst = pos_src.directional_offset(Dir)
  return game_map.normalize(pos_dst)
pos2hlt = lambda p: game_map[p].halite_amount
crds_all = tuple(product(list(range(DIM_GAME)), list(range(DIM_GAME))))
def pos2ngbrs(pos): # Pos -> [Pos]
  p8d2pos_part = partial(p8d2pos, pos)
  pos_ngbrs = pos.get_surrounding_cardinals()
  assert len(pos_ngbrs)==4, pos_ngbrs
  # logitr(pos_ngbrs, '%s.ngbrs'%pos)
  return pos_ngbrs
def clj_position_values(): # perturn CLJ: crd -> val (present)
  calc_val_ngbr = lambda hlt_ngbr: rate_fresh() * hlt_ngbr
  def crd2val(crd):
    x, y = crd
    pos = Position(x, y)
    hlt_self = pos2hlt(pos)
    hlt_ngbrs = mapl(pos2hlt, pos2ngbrs(pos))
    vals_ngbrs = mapl(calc_val_ngbr, hlt_ngbrs)
    val_total = round(hlt_self + mean(vals_ngbrs), 2)
    # log.info('%s -> %s', (pos, hlt_self, hlt_ngbrs), val_total)
    return val_total
  mat_vals = [[crd2val((x,y)) for x in range(DIM_GAME)] 
    for y in range(DIM_GAME)] # NB [y][x]
  df_vals = pd.DataFrame(mat_vals) # NB [x][y]
  def pos2val(pos): return df_vals[pos.x][pos.y]
  def show_value_matrix(): log.debug('Values:\n%s', df_vals)
  # def show(pos, perim=3): log.info('vals %s-near %s:\n', perim, pos, )
  return pos2val, show_value_matrix
# pos2val, show_value_matrix = clj_position_values()
cost4move = lambda pos_src: .1 * pos2hlt(pos_src)
wont_stall = lambda ship: cost4move(ship.position) <= ship.halite_amount
# TODO -> CLJ
def clj_param_pick(if_inspired): # perturn CLJ -> Halite pick-rate (Normal | Inspired)
  record_pick = dict()
  def rate_pick(ship):
    rate_saved = record_pick.get(ship.id)
    if not rate_saved:
      rate_saved = .75 if if_inspired(ship) else .25
      record_pick[ship.id] = rate_saved
    return rate_saved
  return rate_pick

## MOVE
PREC = 3
SID2TASK = dict()  # global; int -> str
pos2crd = lambda pos: (pos.x%DIM_GAME, pos.y%DIM_GAME)
def avoid_hits(): # CLJ: prevent self hits
  crd2sid = dict()  # (int, int) -> sid
  def dst_taken(pos_dst):
    assert isinstance(pos_dst, Position)
    hit = pos2crd(pos_dst) in crd2sid
    # if hit: log.warning('Will hit @%s', dst)
    return hit
  def save_dst(pos_dst, sid):
    crd2sid[pos2crd(pos_dst)] = sid
  # save_dst = lambda dst: crd2sid.add((dst.x%DIM_GAME, dst.y%DIM_GAME))
  def show_dsts():  logitr(crd2sid, 'crd2sid')
  return dst_taken, save_dst, show_dsts
def get_moves(pos2val, rate_pick, if_inspired):
  def p8d2val(ship, pos_src, Dir): # Pos,Dir -> val
    pos_dst = p8d2pos(pos_src, Dir)
    r_fresh = 1. if Dir==O else rate_fresh() 
    cost_move = 0. if Dir==O else -cost4move(pos_src)
    assert cost_move <= 0, (cost_move, 0)
    log.debug('%s val: %s', pos_dst, pos2val(pos_dst))
    val_pos_dst = ceil(rate_pick(ship) * pos2val(pos_dst)) * r_fresh # 0 @Shipyard
    log.debug('%s -> %s: val_pos_dst: %.1f; cost_move: %.1f', pos_src, Dir, val_pos_dst, cost_move)
    return val_pos_dst + cost_move
  def s8d2vimp(ship, Dir, drop=False): # Ship,Dir -> val,sid,Move,Pos
    # log.debug('drop? %s', drop)
    pos_src = ship.position
    val = p8d2val(ship, pos_src, Dir)
    if drop:
      val = val + ship.halite_amount
    val = round(val, PREC)
    # log.debug(val)
    move = ship.move(Dir)
    pos_dst = p8d2pos(pos_src, Dir)
    return (val, ship.id, move, pos_dst)
  def get_vimps(ship): # Ship -> [(val, sid, Move, Pos)]
    sid = ship.id
    task = SID2TASK.get(ship.id)
    # set task
    if not task or ship.halite_amount == 0:
      task = SID2TASK[sid] = Task.roam
    elif task == Task.roam and ship.halite_amount >= n_drop():
      task = SID2TASK[sid] = Task.drop
    log.debug('%s -> %s', ship, task)
    # gen vimps: seed w/ Stay unless on Shipyard -> don't Stay & block
    vimps = [] if ship.position==me.shipyard.position else [s8d2vimp(ship, O)]
    if wont_stall(ship): # enough fuel to move
      if task == Task.drop:
        # _dir_drop = game_map.naive_navigate(ship, me.shipyard.position)
        Dirs_drop = game_map.get_unsafe_moves(ship.position, me.shipyard.position)
      else:
        Dirs_drop = []
      for Dir in [E, N, W, S]:  # O already seeded
        # log.debug('%s vs %s: %s', Dir, Dirs_drop, Dir==Dirs_drop)
        vimps.append(s8d2vimp(ship, Dir, drop=Dir in Dirs_drop))
    # drop val-neg vimps
    # vimps = [(v,i,m,p) for v,i,m,p in vimps if v>=0]
    # HACK: only-Move must happen -> bump-up
    if len(vimps) == 1:
      v,i,m,p = vimps[0]
      vimps[0] = (v+const.SHIP_COST, i, m, p)
    logitr(sorted(vimps, reverse=True), 'vimps <- ship')
    return vimps

  log.info('Age: %.3f; r_fresh: %.3f; n_drop: %d', age(), rate_fresh(), n_drop())
  ships_mine = sorted(me.get_ships(), key=lambda s: s.id)
  vimps = sorted(flatmap(get_vimps, ships_mine), reverse=True)
  logitr(vimps, 'vimps <- turn')
  dst_taken, save_dst, show_dsts = avoid_hits()
  sid_2_pos8val = OrderedDict() # sid:int -> (crd:(int, int), val:float)
  moves = []
  crds = set() # [crd]:(int, int)
  pos_taken = lambda pos: pos2crd(pos) in crds
  for val, sid, move, pos_dst in vimps:
    if sid not in sid_2_pos8val and not dst_taken(pos_dst):
      sid_2_pos8val[sid] = (val, pos_dst)
      save_dst(pos_dst, sid)
      moves.append(move)
      crds.add(pos2crd(pos_dst))
  sids_set = set(sid_2_pos8val.keys())
  sids_all = set(s.id for s in ships_mine)
  sids_left_only = sids_set - sids_all
  sids_right_only = sids_all - sids_set
  # assert len(sids_set)==len(sids_all), (sids_left_only, sids_right_only)
  logitr(moves, 'moves')
  return moves, pos_taken

def get_spawn(moves, pos_taken):
  if all([
    game.turn_number <= 200,
    me.halite_amount >= const.SHIP_COST,
    # not game_map[me.shipyard].is_occupied,
    not pos_taken(me.shipyard.position),
    ]):
    moves.append(me.shipyard.spawn())
  return moves

""" <<<Game Loop>>> """
@timit
def game_loop():
  game.update_frame()
  log.debug(game_map)
  pos2val, show_value_matrix = clj_position_values()
  show_value_matrix()
  # refresh perturn memos
  if_inspired = clj_inspire()
  rate_pick = clj_param_pick(if_inspired)
  # Move & Spawn
  moves, pos_taken = get_moves(pos2val, rate_pick, if_inspired)
  moves_and_spawn = get_spawn(moves, pos_taken)
  # Submit & next
  game.end_turn(moves_and_spawn)
while True: game_loop()

