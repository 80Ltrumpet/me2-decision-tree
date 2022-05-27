#
# Copyright (c) 2022 Andrew Lehmer
#
# Distributed under the MIT License.
#

from __future__ import annotations
from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress
import signal
from threading import Timer
from typing import Any, Optional

class PeriodicTimer:
  """Periodically calls a function with a specified interval in seconds."""
  def __init__(self,
               interval: float,
               function: (Callable[..., Any]),
               args: Optional[Iterable] = None,
               kwargs: Optional[Mapping[str, Any]] = None):
    """Creates a timer that periodically calls function with arguments args and
    keyword arguments kwargs every interval seconds."""
    def periodic_function(*_args: Any, **_kwargs: Any):
      function(*_args, **_kwargs)
      self.timer = Timer(interval, periodic_function, _args, _kwargs)
      self.timer.start()
    self.timer = Timer(interval, periodic_function, args, kwargs)

  def __enter__(self) -> PeriodicTimer:
    self.start()
    return self

  def __exit__(self, *_: Any):
    self.cancel()

  def cancel(self):
    """Cancels the periodic timer."""
    self.timer.cancel()

  def start(self):
    """Starts the periodic timer."""
    # NOTE: This implementation is not restartable.
    self.timer.start()


class SigintHandler:
  """Thread-safe context manager for SIGINT handling
  
  If this is used on a child thread, it will have no effect.
  """
  def __init__(self, handler):
    """Sets the SIGINT handler.
    
    See https://docs.python.org/3/library/signal.html#signal.signal for more
    information on acceptable handler arguments.
    """
    self.handler = handler
    self.original = signal.SIG_DFL

  def __enter__(self) -> SigintHandler:
    with suppress(ValueError):
      self.original = signal.signal(signal.SIGINT, self.handler)
    return self

  def __exit__(self, *_: Any):
    with suppress(ValueError):
      signal.signal(signal.SIGINT, self.original)