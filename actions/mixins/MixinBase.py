from abc import ABC, abstractmethod
from enum import IntEnum

from loguru import logger as log


class State(IntEnum):
    """
    Basic enum for representing state of an item in OBS. `bool(value)` is
    guaranteed to provide the expected semantics for DISABLED (False) and
    ENABLED (True).
    """

    UNKNOWN = -1
    DISABLED = 0
    ENABLED = 1


class MixinBase(ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_state: State = State.UNKNOWN

    @property
    def current_state(self) -> State:
        return self._current_state

    @current_state.setter
    def current_state(self, val: int | State):
        if not val in State:
            log.warning(f"current_state setter called with non-State type {type(val)=} {val=}.")
            val = State(val)

        self._current_state = val

    @abstractmethod
    def next_state(self) -> State:
        pass

    def mixin_config_rows(self) -> list:
        return []
