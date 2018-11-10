## Utils: generic
import logging as log, time, traceback
from functools import partial
from itertools import chain, product
from operator import truth

import numpy as np
import pandas as pd

## DATA
def flatmap(func, itr): return list(chain(*map(func, itr)))
def mapl(func, itr):  return list(map(func, itr)) # actualize iterator
def maps_itr(funcs, itr, lazy=True): # itr-major: map([f], itr) ~ itr>f>f>..
  for f in funcs: itr = map(f, itr)
  return itr if lazy else list(itr)
def maps_func(funcs, itr, lazy=True): # func-major: [map(f, itr)] ~ [f(itr),..]
  fmap = map if lazy else mapl
  return [fmap(f, itr) for f in funcs]
#@ automatic memo-ization w/ private-memo
def memo(f_key=lambda k:k, dict_type=dict, lvl='debug'):
  d = dict_type()
  logf = lvl2lgr(lvl)
  def memo_f(f):
    def memo_a(*args):
      k = f_key(args) # NB Python3 lambda takes single-arg
      if k in d:
        logf('%s$ %s -> %s', f.__name__, k, d[k])
        return d[k]
      else:
        d[k] = f(*args)
        logf('%s$ %s +> %s', f.__name__, k, d[k])
        return d[k]
    return memo_a
  return memo_f

## DEBUG
iterable = lambda obj: hasattr(obj, '__iter__')
dictable = lambda obj: isinstance(obj, dict)
strable = lambda obj: isinstance(obj, str)
boolable = lambda obj: isinstance(obj, bool)
def null(obj):
  if isinstance(obj, pd.DataFrame): return obj.empty()
  elif boolable(obj): return False
  else: return not truth(obj)
def asrt(rel, e0, e1):
  assert rel(e0, e1), '! %s: %s <> %s'%(rel.__name__, e0, e1)
_LVL2LGR = dict(
  debug=log.debug,
  info=log.info,
  warn=log.warning,
  )
def lvl2lgr(lvl='info'):
  def _log_none(*args, **kwargs): pass
  return dict(
    none=_log_none,
    debug=log.debug,
    info=log.info,
    warn=log.warning,
    )[lvl]
def logitr(itr, header='', show=True, lvl='debug'):
  logf = lvl2lgr(lvl)
  if null(itr):
    strs_itr = []
    len_itr = 0
  elif dictable(itr):
    strs_itr = ['%s -> %s'%(k, v) for k, v in sorted(itr.items())]
    len_itr = len(itr)
  elif iterable(itr) and not strable(itr): # non-str iterable
    strs_itr = mapl(str, itr)
    len_itr = len(itr)
  else: # str | other
    strs_itr = [str(itr)]
    len_itr = -1
  str_len = '[%s]'%len_itr if len_itr!=-1 else ''
  if show and len_itr>0:  str_itr = '\n\t'.join(['']+strs_itr)
  else: str_itr = ''
  logf('%s: %s%s', header, str_len, str_itr)
def _str_args_kwargs(args, kwargs): # -> str
  if args and kwargs:
    return '%s; %s'
  else:
    return (args or kwargs) or ''
#@ log [args @func-start] [args|ret @func-end]
def logaz(opts='za', lvl='debug'):
  log_input = opts.startswith('a')
  log_args8output = opts.endswith('za')
  log_output = opts.endswith('z')
  def logaz_f(f):
    def logaz_a(*args, **kwargs):
      str_input = _str_args_kwargs(args, kwargs)
      f_name = f.__name__ if hasattr(f, '__name__') else ''
      if log_input: logf('%s $ %s ...', f_name, str_input)
      res = f(*args, **kwargs)
      if log_args8output: logitr(res, header='%s $ %s =>'%(f_name, str_input), lvl=lvl)
      elif log_output:  logitr(res, header='%s =>'%f_name, lvl=lvl)
      return res
    return logaz_a
  return logaz_f
#@ try-except
def wrap_try(f):
  def _wrap(*args, **kwargs):
    try:
      f(*args, **kwargs)
    except Exception:
      log.error('< Caught exception >\n%s', traceback.format_exc())
  return _wrap
#@ timer
def timit(lvl='info', logargs=False):
  def timit_f(f):
    def timit_a(*args, **kwargs):
      t0 = time.time()
      res = f(*args, **kwargs)
      if not logargs or (not args and not kwargs):
        str_params = ''
      elif args and kwargs:
        str_params = '$ %s; %s'%(args, kwargs)
      elif args:
        str_params = '$ %s'%args
      elif kwargs:
        str_params = '$ %s'%kwargs
      lvl2lgr(lvl)('%s%s ~ %d ms', f.__name__, str_params, round((time.time()-t0)*1000))
      return res
    return timit_a
  return timit_f

## TEST
def listify(nested):
  if isinstance(nested, (map, list)):
    return [listify(e) for e in nested]
  else: return nested
@logaz('za', lvl='warn')
def test(f, *args, lvl='warn', itr2list=False):
  res = f(*args)
  # f_name = f.__name__ if hasattr(f, '__name__') else ''
  # lvl2lgr(lvl)('Done testing < %s >', f_name)
  return listify(res) if itr2list else res
def tests(f, list_args):
  part_test = partial(test, f)
  mapl(part_test, list_args)


if __name__ == '__main__':
  r = range(3)
  t = (r, r)
  l = list(r)
  s = set(r)
  d = dict(zip(*t))
  lvl_test = 'warn'
  sq = lambda x: x**2
  cb = lambda x: x**3

  def test_maps_itr():
    test(maps_itr, [sq, cb], l, itr2list=True)
  def test_maps_func():
    test(maps_func, [sq, cb], l, itr2list=True)
  def test_logitr():
    part_logitr = partial(logitr, lvl=lvl_test)
    tests(part_logitr, [r,t,l,s,d])
  def test_logaz():
    @logaz('aza', lvl='warn')
    def f(x):  return x
    tests(f, [r,t,l,s,d])
  def test_memo():
    @memo(lvl='warn')
    def get_1(k): return k
    tests(get_1, [1,2,3,2,1])

  test_maps_itr()
  test_maps_func()
  # test_logitr()
  # test_logaz()
  # test_memo()
