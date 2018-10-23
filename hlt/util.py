import logging, time, traceback


def wrap_try(f):
  def _wrap(*args, **kwargs):
    try:
      f(*args, **kwargs)
    except Exception:
      log.error('< Caught exception >\n%s', traceback.format_exc())
  return _wrap


def get_logger(name=__file__, lvl=logging.DEBUG):
  log = logging.getLogger(name)
  log.setLevel(lvl)
  sh = logging.StreamHandler()
  sh.setFormatter(
    logging.Formatter('<%(module)s.%(funcName)s:%(lineno)d> %(message)s'))
  log.addHandler(sh)
  return log
log = get_logger()

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

# TODO auto-recursive
def logitr(itr, header='', show=True):
  tab = '\t'
  def _repr_dict(d, lvl, nl=True): # -> [str]
    str_dict = '\n' if nl else ''
    for k, v in sorted(d.items()):
      str_dict += '%s%s -> %s\n'%(tab*lvl, k, _repr(v, lvl))
    return str_dict
  def _repr_itr(itr, lvl, nl=False): # [str]
    str_itr = '\n' if nl else ''
    str_itr += '\n'.join(tab*lvl+_repr(e, lvl, False) for e in itr)
    return str_itr
  def _repr_atom(atom, lvl=0):
    return tab*lvl + str(atom)
  def _repr(itr, lvl=0, nl=True): # -> [str] ?
    if isinstance(itr, dict): # dict-like
      str_repr = _repr_dict(itr, lvl+1, nl)
    elif hasattr(itr, '__iter__'): # non-dict itr
      str_repr =  _repr_itr(itr, lvl+1, nl)
    else: # non-itr atom
      str_repr = _repr_atom(itr)
    return str_repr
  log.debug('%s: [%s]%s', header, len(itr), _repr(itr) if show else '')

# automatic memo-ization w/ hidden memo
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


if __name__ == '__main__':
  def test(f):
    l = list(range(3))
    d = dict(zip(l, l))
    d[2] = dict(zip(l, l))
    d[2][2] = l
    if f == logitr:
      log.info(d)
      logitr(d, 'test')
    elif f == automemo:
      @automemo()
      def memo_get(k):
        return k+1
      memo_get(1)
      memo_get(0)
      memo_get(1)
      memo_get(2)
      memo_get(0)

  test(logitr)
  # test(automemo)

