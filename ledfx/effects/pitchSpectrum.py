import numpy as np
import voluptuous as vol

from ledfx.color import RGB
from ledfx.effects.audio import MAX_MIDI, MIN_MIDI, AudioReactiveEffect
from ledfx.effects.gradient import GradientEffect


class PitchSpectrumAudioEffect(AudioReactiveEffect, GradientEffect):
    NAME = "Pitch Spectrum"
    CATEGORY = "Classic"

    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Optional(
                "blur",
                description="Amount to blur the effect",
                default=1.0,
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10)),
            vol.Optional(
                "mirror",
                description="Mirror the effect",
                default=True,
            ): bool,
            vol.Optional(
                "fade_rate",
                description="Rate at which notes fade",
                default=0.15,
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional(
                "responsiveness",
                description="Responsiveness to note changes",
                default=0.15,
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
        }
    )

    def config_updated(self, config):
        self.avg_midi = None

    def audio_data_updated(self, data):
        # Grab the filtered melbank
        y = self.melbank(filtered=False, size=self.pixel_count)
        midi_value = data.pitch()
        if midi_value is None:
            midi_value = 0
        note_color = RGB(0, 0, 0)
        if not self.avg_midi:
            self.avg_midi = midi_value

        # Average out the midi values to be a little more stable
        if midi_value >= MIN_MIDI:
            self.avg_midi = (
                self.avg_midi * (1.0 - self._config["responsiveness"])
                + midi_value * self._config["responsiveness"]
            )

        # Grab the note color based on where it falls in the midi range
        if self.avg_midi >= MIN_MIDI:
            midi_scaled = (self.avg_midi - MIN_MIDI) / (MAX_MIDI - MIN_MIDI)
            midi_scaled = max(0, min(midi_scaled, 1))
            note_color = self.get_gradient_color(midi_scaled)

        # Mix in the new color based on the filterbank information and fade out
        # the old colors
        # Mix colors for each pixel
        new_colors = np.multiply(self.pixels, (1 - y[:, None])) + np.multiply(
            note_color, y[:, None]
        )

        # Apply fade_rate
        fade_rate = self._config["fade_rate"]
        black = np.zeros((self.pixel_count, 3))
        new_colors = np.multiply(new_colors, (1 - fade_rate)) + np.multiply(
            black, fade_rate
        )

        # Assign new_colors back to self.pixels
        self.pixels = new_colors
