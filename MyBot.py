#!/usr/bin/env python3
# Python 3.6
import logging as log
import random

import hlt
from hlt import constants
from hlt.positionals import Direction, Position
N = Direction.North
E = Direction.East
W = Direction.West
S = Direction.South
O = Direction.Still
EXP = 'expand'
RET = 'return'
## Utils
def asrt(expr, e0, e1): assert expr, '%s != %s'%(e0, e1)
# TODO recursive indent logitr
def logitr(itr, header='', show=True, lvl=0):
  str_title = '%s: [%s]' %(header, len(itr))
  if isinstance(itr, dict):
    strs_body = ['%s -> %s'%(k, v) for k, v in sorted(itr.items())]
  elif hasattr(itr, '__iter__'):
    strs_body = list(map(str, itr))
  else:
    strs_body = '%s%s'%(lvl*'\t', itr)
  strs_body = strs_body if show else []
  str_all = '\n'.join([str_title] + strs_body)
  log.debug(str_all)

""" <<<Game Begin>>> """
game = hlt.Game()
# TODO preproc
game.ready("2_Param")
## Global & Progress
me = game.me
game_map = game.game_map
DIM_GAME = game_map.width
# dim: [32, 64]; n_turns: [401, 501]
DIM_MIN = 32
MAX_TURN = 401 + (DIM_GAME / DIM_MIN - 1) * 100
log.info('Max turns: %s', int(MAX_TURN))
age = lambda : game.turn_number / MAX_TURN  # [0, 1]
# TODO memoize within rates-closure

## Interact
def dist(ship0, ship1):
  pos0 = ship0.position
  pos1 = ship1.position
  dx = (pos0.x - pos1.x) % DIM_GAME
  dy = (pos0.y - pos1.y) % DIM_GAME
  return dx+dy
def ships_in_range(ship, perim=4):  # foe | mine
  ships_all = [s for p in game.players.values() for s in p.get_ships()]
  # logitr(ships_all, 'ships_all', False)
  in_range = lambda s: s!=ship and dist(ship, s) <= perim 
  return filter(in_range, ships_all)
record_inspired = dict()
def if_inspired(ship):
  inspired = record_inspired.get(ship.id)
  if inspired==None:
    is_ship_foe = lambda s: s.owner != me.id
    ships_foe = list(filter(is_ship_foe, ships_in_range(ship)))
    # logitr(ships_foe, 'ships_foe near %s'%ship, False)
    inspired = len(ships_foe)>1
    record_inspired[ship.id] = inspired
    # if inspired:  log.warning('%s NSPYR!', ship.id)
  return inspired
  # return len(ships_foe) > 1

## Eval
# move_random = lambda : random.choice(Direction.get_all_cardinals())
def p8d2pos(pos_src, _dir):
  # log.info((p, d))
  pos_dst = pos_src.directional_offset(_dir)
  pos_dst.x %= DIM_GAME 
  pos_dst.y %= DIM_GAME 
  return pos_dst
pos2val = lambda p: game_map[p].halite_amount
cost4move = lambda pos_src: .1 * pos2val(pos_src)
will_stall = lambda ship: cost4move(ship.position) > ship.halite_amount
rate_keep = lambda : .5 * (1 - age())  # 1 - decay
record_pick = dict()
def rate_pick(ship):
  rate_saved = record_pick.get(ship.id)
  if not rate_saved:
    rate_saved = .75 if if_inspired(ship) else .25
    record_pick[ship.id] = rate_saved
  return rate_saved
def p8d2val(ship, pos_src, _dir):  # Pos + Dir -> val
  pos_dst = p8d2pos(pos_src, _dir)
  r_keep = 1. if _dir==O else rate_keep() 
  cost_move = 0. if _dir==O else -cost4move(pos_src)
  asrt((cost_move <= 0), cost_move, 0)
  val_pos_dst = rate_pick(ship) * pos2val(pos_dst) * r_keep  # 0 for shipyard
  return val_pos_dst - cost_move
def s8d2vmp(ship, _dir, ret=False):
  pos_src = ship.position
  val = p8d2val(ship, pos_src, _dir)
  if ret:
    # log.warning('RET vmp -> %s', s8d2vmp(ship, _dir))
    val = min(val+ship.halite_amount, constants.MAX_HALITE)
  move = ship.move(_dir)
  pos_dst = p8d2pos(pos_src, _dir)
  return (val, move, pos_dst)

## 
CARGO_RETURN = 0.75 * constants.MAX_HALITE
SID2TASK = dict()  # int -> str
SID2DST8VAL = dict()  # int -> ((int, int), float)
# Ship -> [(Val, Move, Pos)]
def get_vmps(ship):
  sid = ship.id
  task = SID2TASK.get(ship.id)
  # set task
  if not task or ship.halite_amount == 0:
    task = SID2TASK[sid] = EXP
  elif task == EXP and ship.halite_amount >= CARGO_RETURN:
    task = SID2TASK[sid] = RET
  log.info('%s -> %s', ship, task)
  # gen vmps
  if ship.position == me.shipyard.position:
    vmps = []  # don't Stay & block
  else:  # seed w/ Stay unless on Shipyard
    vmps = [s8d2vmp(ship, O)]
  if not will_stall(ship):
    if task == RET:
      # prioritize Return
      _dir_ret = game_map.naive_navigate(ship, me.shipyard.position)
      vmps.append(s8d2vmp(ship, _dir_ret, ret=True))
      # # HACK also plan other acts as fallback to avoid Hit
      for _dir in [N, E, W, S]:  # O already seeded
        if _dir != _dir_ret:
          vmps.append(s8d2vmp(ship, _dir))
    else:
      asrt((task==EXP), task, EXP)
      for _dir in [N, E, W, S]:  # O already seeded
        vmps.append(s8d2vmp(ship, _dir))
  # drop val-neg vmps
  vmps = [(v,m,p) for v,m,p in vmps if v>=0]
  # sort desc
  vmps = sorted(vmps, reverse=True)
  return vmps
# prevent Hit
def avoid_hits():
  crd_dsts = set()  # (int, int)
  def will_hit(dst):
    assert isinstance(dst, Position)
    hit = (dst.x, dst.y) in crd_dsts
    if hit: log.warning('Will hit @%s', dst)
    return hit
  save_dst = lambda dst: crd_dsts.add((dst.x%DIM_GAME, dst.y%DIM_GAME))
  def show_dsts():  logitr(crd_dsts, 'crd_dsts')
  return will_hit, save_dst, show_dsts

def get_moves():
  log.info('Age: %.3f; r_keep: %.3f', age(), rate_keep())
  vmps_all = map(get_vmps, me.get_ships())
  vmps_all_sorted = sorted(vmps_all, reverse=True)  # highest val first
  # transient: planned destination-coordinates
  # save_dst8val lambda
  def sort_vmps_all(vmps_all):
    # logitr(vmps_all, 'prefltr')
    vmps_all = [vmp for vmp in vmps_all if vmp]
    # logitr(vmps_all, 'presort')
    return sorted(vmps_all, key=lambda vmps: vmps[0][0], reverse=True)
  will_hit, save_dst, show_dsts = avoid_hits()
  # prioritize single-option vmps over multi
  def partition(vmps_all):
    vmps_single = []
    vmps_multi = []
    for vmps in vmps_all:
      if len(vmps) == 1:
        vmps_single.append(vmps)
      else:
        vmps_multi.append(vmps)
    # log.info('%s vs %s', len(vmps_single), len(vmps_multi))
    return vmps_single, vmps_multi
  def register(vmps_single):
    moves = []
    for vmps in vmps_single:
      asrt(len(vmps)==1, len(vmps), 1)
      val, move, pos = vmps[0]
      save_dst(pos)
      moves.append(move)
    return moves
  def fltr(vmps_all):
    vmps_single, vmps_multi = partition(vmps_all)
    moves_fltr = register(vmps_single)
    return vmps_multi, moves_fltr
  def control_traffic(vmps_all):
    moves = []
    vmps_all = sort_vmps_all(vmps_all)
    logitr(vmps_all, 'vmps_all', False)
    # first register all singular options
    vmps_all, moves_fltr = fltr(vmps_all)
    moves += moves_fltr
    while vmps_all:
      vmps_next = vmps_all[0]
      val, move, pos_dst = vmps_next[0]
      if not will_hit(pos_dst):
        save_dst(pos_dst)
        moves.append(move)
        # drop allocated vmp
        vmps_all = vmps_all[1:]
      else:
        # drop vmp that would-have Hit
        vmps_next = vmps_next[1:]  
        if vmps_next:
          vmps_all[0] = vmps_next
        else:
          vmps_all = vmps_all[1:]
        vmps_all = sort_vmps_all(vmps_all)
      # same update
      vmps_all, moves_fltr = fltr(vmps_all)
      moves += moves_fltr
    return moves
  show_dsts()
  return control_traffic(vmps_all_sorted)

def get_spawn():
  if all([
    game.turn_number <= 200,
    me.halite_amount >= constants.SHIP_COST,
    not game_map[me.shipyard].is_occupied,
    ]):
    return [me.shipyard.spawn()]
  else: return []

""" <<<Game Loop>>> """
while True:
  game.update_frame()
  # refresh perturn memos
  record_pick = dict()
  record_inspired = dict()
  # Move & Spawn
  command_queue = get_moves() + get_spawn()
  logitr(command_queue, 'comms')
  # Submit & next
  game.end_turn(command_queue)

