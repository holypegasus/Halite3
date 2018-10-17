#!/usr/bin/env python3
# Python 3.6
import logging, random

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
def logitr(itr, header='', lvl=0):
  str_title = '%s: [%s]' %(header, len(itr))
  if isinstance(itr, dict):
    strs_body = ['%s -> %s'%(k, v) for k, v in sorted(itr.items())]
  elif hasattr(itr, '__iter__'):
    strs_body = list(map(str, itr))
  else:
    strs_body = '%s%s'%(lvl*'\t', itr)
  str_all = '\n'.join([str_title] + strs_body)
  logging.info(str_all)

""" <<<Game Begin>>> """
game = hlt.Game()
# TODO preproc
game.ready("1_Eval")

# move_random = lambda : random.choice(Direction.get_all_cardinals())
def p8d2pos(pos, _dir):
  # logging.info((p, d))
  return pos.directional_offset(_dir)
pos2val = lambda p: game_map[p].halite_amount
cost4move = lambda pos_src: .1 * pos2val(pos_src)
will_stall = lambda ship: cost4move(ship.position) > ship.halite_amount
DECAY = .5  # aka InterestRate
def p8d2val(pos_src, _dir):
  pos_dst = p8d2pos(pos_src, _dir)
  decay = 1. if _dir==O else DECAY 
  cost_move = 0. if _dir==O else -cost4move(pos_src)
  asrt((cost_move <= 0), cost_move, 0)
  val = .25 * pos2val(pos_dst) * decay - cost_move
  return val
CARGO_RETURN = constants.MAX_HALITE/2
SID2TASK = dict()
def get_moves():
  def s8d2vmp(ship, _dir, ret=False):
    pos_src = ship.position
    val = p8d2val(pos_src, _dir)
    if ret:
      # logging.warning('RET vmp -> %s', s8d2vmp(ship, _dir))
      val = min(val+ship.halite_amount, constants.MAX_HALITE)
    move = ship.move(_dir)
    pos_dst = p8d2pos(pos_src, _dir)
    return (val, move, pos_dst)
  # Ship -> [(Val, Move, Pos)]
  def get_vmps(ship):
    sid = ship.id
    task = SID2TASK.get(ship.id)
    # set task
    if not task or ship.halite_amount == 0:
      task = SID2TASK[sid] = EXP
    elif task == EXP and ship.halite_amount >= CARGO_RETURN:
      task = SID2TASK[sid] = RET
    logging.info('%s -> %s', ship, task)
    # gen vmps
    if ship.position == me.shipyard.position:
      vmps = []
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
  # logging.info("%s -> %s :: %s", ship, dest, coords_dests)
  vmps_all = map(get_vmps, me.get_ships())
  vmps_all_sorted = sorted(vmps_all, reverse=True)  # highest val first
  # transient: planned dests
  coords_dests = set()
  def will_hit(dest):
    assert isinstance(dest, Position)
    hit = (dest.x, dest.y) in coords_dests
    if hit: logging.warning('Will hit @%s', dest)
    return hit
  def save_coord_dest(dest):
    coords_dests.add((dest.x, dest.y))
  def sort_vmps_all(vmps_all):
    # logitr(vmps_all, 'prefltr')
    vmps_all = [vmp for vmp in vmps_all if vmp]
    # logitr(vmps_all, 'presort')
    return sorted(vmps_all, key=lambda vmps: vmps[0][0], reverse=True)
    # if vmps_all:
    #   vmps_all = sorted(vmps_all, key=lambda vmps: vmps[0][0], reverse=True)
    # return vmps_all
  # prioritize single-option vmps over multi
  def partition(vmps_all):
    vmps_single = []
    vmps_multi = []
    for vmps in vmps_all:
      if len(vmps) == 1:
        vmps_single.append(vmps)
      else:
        vmps_multi.append(vmps)
    logging.info('%s vs %s', len(vmps_single), len(vmps_multi))
    return vmps_single, vmps_multi
  def register(vmps_single):
    moves = []
    for vmps in vmps_single:
      asrt(len(vmps)==1, len(vmps), 1)
      val, move, pos = vmps[0]
      save_coord_dest(pos)
      moves.append(move)
    return moves
  def fltr(vmps_all):
    vmps_single, vmps_multi = partition(vmps_all)
    moves_fltr = register(vmps_single)
    return vmps_multi, moves_fltr
  def control_traffic(vmps_all):
    moves = []
    vmps_all = sort_vmps_all(vmps_all)
    logitr(vmps_all, 'vmps_all')
    # first register all singular options
    vmps_all, moves_fltr = fltr(vmps_all)
    moves += moves_fltr
    while vmps_all:
      vmps_next = vmps_all[0]
      val, move, pos_dst = vmps_next[0]
      if not will_hit(pos_dst):
        save_coord_dest(pos_dst)
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
    logitr(coords_dests, 'dests')
    return moves
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
  me = game.me
  game_map = game.game_map
  # Move & Spawn
  command_queue = get_moves() + get_spawn()
  logitr(command_queue, 'comms')
  # Submit & next
  game.end_turn(command_queue)


