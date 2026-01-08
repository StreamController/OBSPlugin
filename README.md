# OBS Plugin for StreamController

A StreamController plugin for controlling OBS Studio through the obs-websocket protocol.

## Actions

### Scene Management
- **Switch Scene** - Switches OBS to a specific scene selected from the available scenes in your current scene collection.
- **Switch Scene Collection** - Changes the active scene collection in OBS to the one you select from the available collections.

### Streaming & Recording
- **Toggle Stream** - Starts or stops streaming in OBS and displays the stream duration when active.
- **Toggle Record** - Starts or stops recording in OBS and displays the recording duration when active.
- **Rec Play/Pause** - Pauses or resumes an active recording without stopping it completely.

### Replay Buffer
- **Toggle Replay Buffer** - Enables or disables the replay buffer feature in OBS.
- **Save Replay Buffer** - Saves the current replay buffer to disk (requires replay buffer to be active).

### Input Control
- **Toggle Input Mute** - Toggles the mute state of a selected audio input source between muted and unmuted.
- **Set Input Mute** - Sets a selected audio input source to a specific mute state (muted or unmuted).
- **Input Dial** - Controls the volume level of an audio input source using a dial interface and toggles mute on button press.

### Scene Items
- **Toggle Scene Item Enabled** - Toggles the visibility of a specific source within a scene between visible and hidden.
- **Set Scene Item Enabled** - Sets a specific source within a scene to a specific visibility state (visible or hidden).

### Filters
- **Toggle Filter** - Toggles a source filter between enabled and disabled states.
- **Set Filter** - Sets a source filter to a specific state (enabled or disabled).

### Other
- **Toggle Virtual Camera** - Starts or stops the OBS virtual camera output.
- **Toggle Studio Mode** - Enables or disables Studio Mode in OBS for preview/program workflow.
- **Trigger Transition** - Executes the current transition to switch from preview to program scene in Studio Mode.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
