# vgm2electron

Python script for converting SN76489 VGM files to Acorn Electron Beeper ULA data

Highly experimental.

The approach I used is to filter out noise channels, and then interleave short square wave beeps based on current 3 channel usage of the source VGM to try and approximate the tune with just a simple single channel square wave generator that the Acorn Electron has.

It isn't a good general purpose solution really, since there are no volume controls on the Electron - just output on/off - we have to decide how to manage music with 15-volume levels for each of the 3 input voice channels and this is pretty subjective from tune-to-tune.

The best conversion that has come out so far from this script has been the Bad Apple music by Inverse Phase (converted from https://bitshifters.github.io/posts/prods/bs-badapple.html to https://twitter.com/0xC0DE6502/status/1205618230708129793?s=20)


Some better approaches might be:
* Arpeggiate based on the number of currently active channels - this way we can be sure that all channels get heard
* Bias arpeggiation based on the volume contribution per channel