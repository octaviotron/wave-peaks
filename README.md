# wave-peaks

Wave data analysis and processing for finding chunks and segments of audio.

This script takes a WAV file as input and detects segments signal data over a thresshold and when a quorum is reached, the lapse is stored in a separated WAV file. This is mainly used in audio files with a long silences or long noise parts where you need to have separated the sound over this thresshold.

The script needs following variables to be set:

* TOP (1-32768): defines where is the top level signal to be consider as "not-noise-signal"
* TASA (0.1-0.99): defines the amount of concurrent peaks ina segment to be considered "not-a-single-peak"
