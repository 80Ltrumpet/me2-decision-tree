from threading import Timer
from typing import Any, Callable, Iterable, Mapping, Optional

class PeriodicTimer:
  """Periodically calls a function with a specified interval in seconds."""
  def __init__(self,
               interval: float,
               function: Callable[..., None],
               args: Optional[Iterable] = None,
               kwargs: Optional[Mapping[str, Any]] = None) -> None:
    """Creates a timer that periodically calls function with arguments args and
    keyword arguments kwargs every interval seconds."""
    def periodic_function(*_args: Any, **_kwargs: Any) -> None:
      function(*_args, **_kwargs)
      self.timer = Timer(interval, periodic_function, _args, _kwargs)
      self.timer.start()
    self.timer = Timer(interval, periodic_function, args, kwargs)

  def cancel(self) -> None:
    """Cancels the periodic timer."""
    self.timer.cancel()

  def start(self) -> None:
    """Starts the periodic timer."""
    # NOTE: This implementation is not restartable.
    self.timer.start()