# vgm2electron

Python script for converting SN76489 VGM files to Acorn Electron Beeper ULA data

**Highly experimental!**

Unlike the BBC Micro, the Acorn Electron has no dedicated sound chip, it simply has a counter built into the system's ULA that can be programmed to drive a speaker as a primitive squarewave generator. That means the Electron has only one squarewave channel with two volumes - on/off. There's no envelopes and no HW noise generator (although noise can be simulated in software at the expense of many CPU cycles).

### Driving the Electron Beeper

We can drive the frequency of the speaker by setting the ULA counter as a single byte, which gives us an output tone range of 122Hz to 31.25Khz (inaudible).

The EAUG guide says that frequency range is 244Hz to 62.5Khz and is calculated as:

`Sound frequency in Hertz = 1 MHz / [16 * (S + 1)]`

_Where `S` is the ULA byte set at SHEILA `&FE06` ranging from 0 (highest frequency) to 255 (lowest frequency)_

However I've found this to be incorrect, and that actually the formula is:

`Sound frequency in Hertz = 1 MHz / [32 * (S + 1)]`

Which is actually good news, since 122Hz (~B2) is a much better low end range - if it were 244Hz (~B3), most music would sound tinny and horrible with that bottom octave missing.

Register settings between 0 and 6 are beyond the upper range of a standard 88-key piano, so most of the 8 bit register values 7-255 translate to useful note frequencies (albeit with some precision loss on actual tuning to correct musical scale note frequencies).

Setting the register to zero generates a 32.25Khz frequency, which is effectively inaudible so we can treat that as a "speaker off" state to give us a very primitive volume on/off control.

### Conversion Approach

So in order to create music for what is effectively a simple beeper we have to use some tricks.

The general approach I used is to filter out noise channels, and then interleave short square wave beeps based on current 3 channel usage, with priority given to channel 1 of the source VGM to try and approximate the tune with just a simple single channel square wave generator that the Acorn Electron has.

A second technique I've tried is similar to that, but a straight modulation between the number of currently active channels. This can work better for some tunes, less so for others.

This script isn't a good general purpose solution just now, since there are no volume controls on the Electron - just output on/off - we have to decide how to manage music with 15-volume levels for each of the 3 input voice channels and this is pretty subjective from tune-to-tune.

The best conversion that has come out so far from this script has been the Bad Apple music by Inverse Phase (converted from https://bitshifters.github.io/posts/prods/bs-badapple.html to https://twitter.com/0xC0DE6502/status/1205618230708129793?s=20)

## Usage
The script requires Python 3 and takes a VGM file as an input, converting it to a file called `<filename>.electron.vgm` output.

```
Vgm2Electron.py : VGM music converter for Acorn Electron
Written in 2019 by Simon Morris, https://github.com/simondotm/vgm-packer

usage: vgm2electron.py [-h] [-o <output>] [-v] [-a <nnn>] [-t <nnn>]
                       [-c [1][2][3]] [-q <n>]
                       input
```

The script also emits a binary byte stream of the VGM music as raw ULA data (`<filename>.ula.bin`) which can be loaded on an Acorn Electron and sent to the ULA SHEILA `&FE06` counter register at 1 byte every 50Hz. The ULA needs to be in non cassette mode for this counter to drive the speaker instead.

The ULA data is pretty big, but it tends to compress quite well, so it is possible to use this data on actual Acorn Electron hardware from an 6502 assembler music driver for example.

TODO: I really need to append an `0x01` byte at the end of the ULA bin stream to signify end of data! `0x00` is volume off, and `0x01` should never actually be output in the wild so we can use it as an EOF token.

## Notes


Some better approaches might be:
* Arpeggiate based on the number of currently active channels - this way we can be sure that all channels get heard
* Bias arpeggiation based on the volume contribution per channel
* Reset the arpeggiator when new tones are triggered since sometimes they get lost if they trigger on dan offcycle (since the arpeggiation is driven by simple `frame number MOD 3` atm)


# Related Projects

See also the good work to get music playing on Acorn Electron by [Negative Phase](https://github.com/NegativeCharge/Releases)

A 6502 music player for the ULA BIN files this script generates also by Negative Phase - https://github.com/NegativeCharge/vgm2electron-Player

And also another 6502 Electron music player by TôBach - https://github.com/OSToastBach/Electro-Player
