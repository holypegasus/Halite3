#!/usr/bin/env python3
# Python 3.6
import logging, random
# Import the Halite SDK, which will let you interact with the game.
import hlt
# This library contains constant values.
from hlt import constants
# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

""" <<<Game Begin>>> """
game = hlt.Game()
# TODO preproc
game.ready("MyPythonBot")

# sid -> dest # TODO (task, dest)
sid2dest = dict()
def fsm_status():
  # # status FSM
  # if ship.id not in ship_status:
  #   ship_status[ship.id] = "exploring"
  # elif ship_status[ship.id] == "returning":
  #   if ship.position == me.shipyard.position:
  #     ship_status[ship.id] = "exploring"
  #   else:
  #     return ship.move(game_map.naive_navigate(ship, me.shipyard.position))
  # elif ship.halite_amount >= constants.MAX_HALITE / 4:
  #   ship_status[ship.id] = "returning"
  pass

# little -> nearest most

# many -> unload

def get_moves():
  move_random = lambda : random.choice(Direction.get_all_cardinals())
  def fltr_move(moves):
    # TODO avoid collision
    moves = [m for m in moves]
    return moves
  def get_move(ship):
    logging.info("Ship {} has {} halite.".format(ship.id, ship.halite_amount))
    # move
    if any([
      game_map[ship.position].halite_amount < constants.MAX_HALITE / 10,
      ship.is_full,
      ]):
      return ship.move(move_random())
    else:
      return ship.stay_still()

  moves = map(get_move, me.get_ships())
  moves = fltr_move(moves)
  return moves

def get_spawn():
  if all([
    game.turn_number <= 200,
    me.halite_amount >= constants.SHIP_COST,
    not game_map[me.shipyard].is_occupied,
    ]):
    return [me.shipyard.spawn()]
  else: return []

def get_dropoff():
  # me.get_dropoffs() -> [locs]
  # ship.make_dropoff() -> move
  # game_map.calculate_distance(loc0, loc1) -> int
  pass


""" <<<Game Loop>>> """
while True:
  game.update_frame()
  me = game.me
  game_map = game.game_map
  # Move & Spawn
  command_queue = get_moves() + get_spawn()
  logging.info(command_queue)
  # Submit & next
  game.end_turn(command_queue)


