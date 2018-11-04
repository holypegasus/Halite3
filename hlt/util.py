## Utils
import logging as log, time, traceback
from itertools import chain, product

## DATA
def flatmap(func, itr): return list(chain(*map(func, itr)))
def mapl(func, itr):  return list(map(func, itr)) # actualize iterator
def maps(funcs, itr): # map multiple functions over iterable
  for f in funcs: itr = map(f, itr)
  return itr
## DEBUG
LVL2LGR = dict(
  debug=log.debug,
  info=log.info,
  warn=log.warning,
  )
def logret(lvl='debug', logargs=False, show=True):
  def _func(f):
    def _args(*args, **kwargs):
      logf = LVL2LGR[lvl]
      if logargs: logf('args: %s & kwargs: %s', args, kwargs)
      res = f(*args, **kwargs)
      logf('%s(%s & %s) => %s', f.__name__, args, kwargs, res)
      return res
    return _args
  return _func
def logitr(itr, header='', show=True, lvl='debug'):
  if isinstance(itr, dict):
    strs_itr = ['%s -> %s'%(k, v) for k, v in itr.items()]
  elif hasattr(itr, '__iter__'):
    strs_itr = map(str, itr)
  else:
    strs_itr = [str(itr)]
  str_itr = '\n'.join(strs_itr)
  LVL2LGR[lvl]('%s: [%s]%s', header, len(itr), '\n'+str_itr if show else '')
def wrap_try(f):
  def _wrap(*args, **kwargs):
    try:
      f(*args, **kwargs)
    except Exception:
      log.error('< Caught exception >\n%s', traceback.format_exc())
  return _wrap
def timit(lvl='info'):
  def _func(f):
    def _args(*args, **kwargs):
      t0 = time.time()
      res = f(*args, **kwargs)
      t1 = time.time()
      LVL2LGR[lvl]('%s: %.3fs', f.__name__, t1-t0)
      return res
    return _args
  return _func
## OTHER
# automatic memo-ization w/ private-memo
def automemo(func_key=lambda k:k, dict_type=dict, lvl='debug'):
  d = dict_type()
  logf = LVL2LGR[lvl]
  def _func(f):
    def _args(*args):
      k = func_key(args) # NB Python3 lambda takes single-arg
      if k in d:
        # LVL2LGR[lvl]('%s -> %s', k, d[k])
        logf('%s: %s -> %s', f.__name__, k, d[k])
        return d[k]
      else:
        d[k] = f(*args)
        logf('%s: %s +> %s', f.__name__, k, d[k])
        return d[k]
    return _args
  return _func

if __name__ == '__main__':
  l = list(range(3))
  d = dict(zip(l, l))
  d[2] = dict(zip(l, l))
  d[2][2] = l
  def test_logret():
    @logret(lvl='warn')
    def f(x):  return x
    mapl(f, range(-2, 2))
  def test_logitr(data):  logitr(data, 'test', lvl='warn')
  def test_automemo():
    @automemo(lvl='warn')
    def get_1(k):
      return k+1
    get_1(1)
    get_1(0)
    get_1(1)
    get_1(2)
    get_1(0)

  test_logret()
  test_logitr(d)
  test_automemo()
