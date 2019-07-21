from . import commands

from .util import asrt


class Delta: # positional delta
  alias = 'Dlt'
  def __init__(self, x, y):
    self.x = x
    self.y = y

  def __add__(self, other):
    assert isinstance(other, Delta)
    return Delta(self.x + other.x, self.y + other.y)

  def __sub__(self, other):
    assert isinstance(other, Delta)
    return Delta(self.x - other.x, self.y - other.y)

  def __iadd__(self, other):
    assert isinstance(other, Delta)
    self.x += other.x
    self.y += other.y
    return self

  def __isub__(self, other):
    assert isinstance(other, Delta)
    self.x -= other.x
    self.y -= other.y
    return self

  def __abs__(self):
    assert isinstance(other, Delta)
    return Delta(abs(self.x), abs(self.y))

  def __eq__(self, other):
    assert isinstance(other, Delta)
    return self.x == other.x and self.y == other.y

  def __ne__(self, other):
    assert isinstance(other, Delta)
    return not self.__eq__(other)

  def __lt__(self, other):
    asrt(isinstance, other, Delta)
    return (self.x < other.x 
      or (self.x==other.x and self.y < other.y))

  def __repr__(self):
    return "{}({}, {})".format(
      self.alias, self.x, self.y)

  def __hash__(self):
    return hash((self.alias, self.x, self.y))


# ~ 1-Delta
class Direction(Delta):
  """
  Holds positional tuples in relation to cardinal directions
  """
  North = (0, -1)
  South = (0, 1)
  East = (1, 0)
  West = (-1, 0)

  Still = (0, 0)

  @staticmethod
  def get_all_cardinals():
    """
    Returns all contained items in each cardinal
    :return: An array of cardinals
    """
    return [Direction.North, Direction.South, Direction.East, Direction.West]

  @staticmethod
  def convert(direction):
    """
    Converts from this direction tuple notation to the engine's string notation
    :param direction: the direction in this notation
    :return: The character equivalent for the game engine
    """
    if direction == Direction.North:
      return commands.NORTH
    if direction == Direction.South:
      return commands.SOUTH
    if direction == Direction.East:
      return commands.EAST
    if direction == Direction.West:
      return commands.WEST
    if direction == Direction.Still:
      return commands.STAY_STILL
    else:
      raise IndexError

  @staticmethod
  def invert(direction):
    """
    Returns the opposite cardinal direction given a direction
    :param direction: The input direction
    :return: The opposite direction
    """
    if direction == Direction.North:
      return Direction.South
    if direction == Direction.South:
      return Direction.North
    if direction == Direction.East:
      return Direction.West
    if direction == Direction.West:
      return Direction.East
    if direction == Direction.Still:
      return Direction.Still
    else:
      raise IndexError

# USR: devolved
# absolute -> Position
# relative -> Delta
class Position:
  alias = 'Pos'
  def __init__(self, x, y):
    self.x = x
    self.y = y

  # Dir -> Pos
  def directional_offset(self, direction):
    """
    Returns the position considering a Direction cardinal tuple
    :param direction: the direction cardinal tuple
    :return: a new position moved in that direction
    """
    return self + Delta(*direction)
  # -> [Pos]
  def get_surrounding_cardinals(self):
    """
    :return: Returns a list of all positions around this specific position in each cardinal direction
    """
    return [self.directional_offset(current_direction) for current_direction in Direction.get_all_cardinals()]

  def __add__(self, other):
    asrt(isinstance, other, Delta)
    return Position(self.x + other.x, self.y + other.y)

  def __sub__(self, other): # okay: Pos - Pos -> dist
    return Position(self.x - other.x, self.y - other.y)

  def __iadd__(self, other):
    assert isinstance(other, Delta)
    self.x += other.x
    self.y += other.y
    return self

  def __isub__(self, other):
    assert isinstance(other, Delta)
    self.x -= other.x
    self.y -= other.y
    return self

  def __abs__(self):
    return Position(abs(self.x), abs(self.y))

  def __eq__(self, other):
    assert isinstance(other, Position)
    return self.x == other.x and self.y == other.y

  def __ne__(self, other):
    assert isinstance(other, Position)
    return not self.__eq__(other)

  def __repr__(self):
    return "{}({}, {})".format(
      # self.__class__.__name__,
      self.alias, self.x, self.y)

  def __hash__(self):
    return hash((self.alias, self.x, self.y))


# USER: template shortest-path etc utils
class Zone: # 2 ORDERED anchor-Pos & map-dimension
  def __init__(self, obj0, obj1, dim):
    self.dim = dim
    self.p00 = obj0 if isinstance(obj0, Position) else obj0.position
    self.p11 = obj1 if isinstance(obj1, Position) else obj1.position
    self.wrap_x = self.p00.x > self.p11.x
    self.wrap_y = self.p00.y > self.p11.y
    # self.x00, self.y11 = p00.x, p00.y
    # self.x11, self.y11 = p11.x, p11.y

  def __contains__(self, obj):
    pos = obj if isinstance(obj, Position) else obj.position
    in_x_range = (self.p00.x<=pos.x<=self.p11.x 
      if not self.wrap_x else 
      self.p00.x<=pos.x<=self.dim or 0<=pos.x<=self.p11.x)
    in_y_range = (self.p00.y<=pos.y<=self.p11.y
      if not self.wrap_y else 
      self.p00.y<=pos.y<=self.dim or 0<=pos.y<=self.p11.y)
    return in_x_range and in_y_range

  def __repr__(self):
    return '%s@(%s, %s)'%(
      self.__class__.__name__,
      self.p00,
      self.p11)