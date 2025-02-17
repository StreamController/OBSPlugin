"""
These mixins are designed to separate the logic of managing one-by-one entities
with OBS and representing how a user may wish to manage those entities.

To use:

1. In your base action (e.g., `InputMuteBase`)...
    * Inherit from `MixinBase` (e.g., `class InputMuteBase(OBSActionBase,
      MixinBase, ABC)`).
    * Read and write your entity's state in `MixinBase`'s `current_state`,
      using `State` (e.g., `self.current_state = State.UNKNOWN`).
    * In `get_config_rows`, include `self.mixin_config_rows()` as the final
      config rows.
2. For a Toggle variant, declare a class that inherits from the Toggle mixin
   and your base, in that order. You do not need to define anything in this
   class; `pass` is sufficient. Example:
   `class ToggleInputMute(ToggleMixin, InputMuteBase): pass`
3. For a Set variant, do the same but with the Set mixin.
4. Create and register your actions as usual in your plugin base.
"""

from .MixinBase import State, MixinBase
from .ToggleMixin import ToggleMixin
from .SetMixin import SetMixin
