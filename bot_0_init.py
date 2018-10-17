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


def get_moves():
  move_random = lambda : random.choice(Direction.get_all_cardinals())
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

  return list(map(get_move, me.get_ships()))

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
  logging.info(command_queue)
  # Submit & next
  game.end_turn(command_queue)


