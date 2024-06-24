from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

import sys
import os
import threading
from datetime import timedelta
from loguru import logger as log

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

from OBSActionBase import OBSActionBase

from actions.ToggleRecord.ToggleRecord import ToggleRecord
from actions.ToggleStream.ToggleStream import ToggleStream

from actions.ToggleReplayBuffer.ToggleReplayBuffer import ToggleReplayBuffer
from actions.SaveReplayBuffer.SaveReplayBuffer import SaveReplayBuffer

from actions.ToggleVirtualCamera.ToggleVirtualCamera import ToggleVirtualCamera

from actions.ToggleStudioMode.ToggleStudioMode import ToggleStudioMode
from actions.TriggerTransition.TriggerTransition import TriggerTransition

from actions.ToggleInputMute.ToggleInputMute import ToggleInputMute

from actions.ToggleSceneItemEnabled.ToggleSceneItemEnabled import ToggleSceneItemEnabled

from actions.RecPlayPause.RecPlayPause import RecPlayPause
from actions.SwitchScene.SwitchScene import SwitchScene

class OBS(PluginBase):
    def __init__(self):
        super().__init__()

        # Launch backend
        print("launch backend")
        self.launch_backend(os.path.join(self.PATH, "backend", "backend.py"), os.path.join(self.PATH, "backend", ".venv"), open_in_terminal=False)
        print("backend launched")

        self.lm = self.locale_manager
        self.lm.set_to_os_default()


        self.register(
            plugin_name=self.lm.get("plugin.name"),
            github_repo="https://github.com/StreamController/OBSPlugin",
            plugin_version="1.0.1",
            app_version="1.0.0-alpha"
        )

        # Recording
        toggle_record_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleRecord,
            action_id_suffix="ToggleRecord",
            action_name=self.lm.get("actions.toggle-record.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED
            }
        )
        self.add_action_holder(toggle_record_action_holder)

        rec_play_pause_action_holder = ActionHolder(
            plugin_base=self,
            action_base=RecPlayPause,
            action_id_suffix="RecPlayPause",
            action_name=self.lm.get("actions.rec-play-pause.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED
            }
        )
        self.add_action_holder(rec_play_pause_action_holder)

        # Streaming
        toggle_stream_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleStream,
            action_id_suffix="ToggleStream",
            action_name=self.lm.get("actions.toggle-stream.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED
            }
        )
        self.add_action_holder(toggle_stream_action_holder)

        # Replay Buffer
        toggle_replay_buffer_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleReplayBuffer,
            action_id_suffix="ToggleReplayBuffer",
            action_name=self.lm.get("actions.toggle-replay-buffer.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            }
        )
        self.add_action_holder(toggle_replay_buffer_action_holder)

        save_replay_buffer_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SaveReplayBuffer,
            action_id_suffix="SaveReplayBuffer",
            action_name=self.lm.get("actions.save-replay-buffer.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            }
        )
        self.add_action_holder(save_replay_buffer_action_holder)

        # Virtual Camera
        toggle_virtual_camera_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleVirtualCamera,
            action_id_suffix="ToggleVirtualCamera",
            action_name=self.lm.get("actions.toggle-virtual-camera.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            }
        )
        self.add_action_holder(toggle_virtual_camera_action_holder)

        # Studio Mode
        toggle_studio_mode_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleStudioMode,
            action_id_suffix="ToggleStudioMode",
            action_name=self.lm.get("actions.toggle-studio-mode.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            }
        )
        self.add_action_holder(toggle_studio_mode_action_holder)

        trigger_transition_action_holder = ActionHolder(
            plugin_base=self,
            action_base=TriggerTransition,
            action_id_suffix="TriggerTransition",
            action_name=self.lm.get("actions.trigger-transition.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            }
        )
        self.add_action_holder(trigger_transition_action_holder)

        # Input Muting
        toggle_input_mute_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleInputMute,
            action_id_suffix="ToggleInputMute",
            action_name=self.lm.get("actions.toggle-input-mute.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            }
        )
        self.add_action_holder(toggle_input_mute_action_holder)

        # Scenes
        switch_scene_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SwitchScene,
            action_id_suffix="SwitchScene",
            action_name=self.lm.get("actions.switch-scene.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED
            }
        )
        self.add_action_holder(switch_scene_action_holder)

        # Scene Items
        toggle_scene_item_enabled_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleSceneItemEnabled,
            action_id_suffix="ToggleSceneItemEnabled",
            action_name=self.lm.get("actions.toggle-scene-item-enabled.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            }
        )
        self.add_action_holder(toggle_scene_item_enabled_action_holder)

        # Load custom css
        self.add_css_stylesheet(os.path.join(self.PATH, "style.css"))

    def get_connected(self):
        try:
            return self.backend.get_connected()
        except Exception as e:
            log.error(e)
            return False