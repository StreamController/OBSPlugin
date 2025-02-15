from .MixinBase import MixinBase, State


class ToggleMixin(MixinBase):
    def next_state(self) -> State:
        match self.current_state:
            case State.UNKNOWN:
                raise ValueError()
            case State.DISABLED:
                return State.ENABLED
            case State.ENABLED:
                return State.DISABLED
