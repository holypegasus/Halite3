

def foco_range(t0=0, td=0): return range(t0, t0+td+1)
TURNS_FOCO = foco_range(0, 0)
# TURNS_FOCO = foco_range(200, 0)


TURN_LAST_SPAWN = .5 * (TURNS_FOCO[0] or 500)


