# wave-peaks
Wave data analysis and processing for finding chunks and segments of audio.

The script needs following variables to be set:

* TOP (1-32768): defines where is the top level signal to be consider as "not-noise-signal"
* TASA (0.1-0.99): defines the amount of concurrent peaks ina segment to be considered "not-a-single-peak"
