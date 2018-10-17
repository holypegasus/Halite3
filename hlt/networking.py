import json
import logging
import sys

from .common import read_input
from . import constants
from .game_map import GameMap, Player


class Game:
  """
  The game object holds all metadata pertinent to the game and all its contents
  """
  def __init__(self):
    """
    Initiates a game object collecting all start-state instances for the contained items for pre-game.
    Also sets up basic logging.
    """
    self.turn_number = 0

    # Grab constants JSON
    raw_constants = read_input()
    constants.load_constants(json.loads(raw_constants))

    num_players, self.my_id = map(int, read_input().split())

    logging.basicConfig(
      filename="replays/bot-{}.log".format(self.my_id),
      filemode="w",
      level=logging.DEBUG,
      format='<%(module)s.%(funcName)s:%(lineno)d> %(message)s',
    )

    self.players = {}
    for player in range(num_players):
      self.players[player] = Player._generate()
    self.me = self.players[self.my_id]
    self.game_map = GameMap._generate()

  def ready(self, name):
    """
    Indicate that your bot is ready to play.
    :param name: The name of your bot
    """
    send_commands([name])
    logging.info("Successfully created bot! My Player ID is {}.".format(self.my_id))

  def update_frame(self):
    """
    Updates the game object's state.
    :returns: nothing.
    """
    self.turn_number = int(read_input())
    worth_store = self.me.halite_amount
    ships_mine = self.me.get_ships()
    worth_ships = len(ships_mine)*constants.SHIP_COST
    worth_cargo = sum(s.halite_amount for s in ships_mine)
    worth_total = worth_store + worth_ships + worth_cargo

    logging.info("====== TURN {turn:03} : {store} + {ship} + {cargo} => {total} ======".format(
      turn=self.turn_number,
      store=worth_store,
      ship=worth_ships,
      cargo=worth_cargo,
      total=worth_total,
      ))

    for _ in range(len(self.players)):
      player, num_ships, num_dropoffs, halite = map(int, read_input().split())
      self.players[player]._update(num_ships, num_dropoffs, halite)

    self.game_map._update()

    # Mark cells with ships as unsafe for navigation
    for player in self.players.values():
      for ship in player.get_ships():
        self.game_map[ship.position].mark_unsafe(ship)

      self.game_map[player.shipyard.position].structure = player.shipyard
      for dropoff in player.get_dropoffs():
        self.game_map[dropoff.position].structure = dropoff

  @staticmethod
  def end_turn(commands):
    """
    Method to send all commands to the game engine, effectively ending your turn.
    :param commands: Array of commands to send to engine
    :return: nothing.
    """
    send_commands(commands)


def send_commands(commands):
  """
  Sends a list of commands to the engine.
  :param commands: The list of commands to send.
  :return: nothing.
  """
  print(" ".join(commands))
  sys.stdout.flush()
