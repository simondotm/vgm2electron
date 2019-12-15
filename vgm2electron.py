#!/usr/bin/env python
# vgm2electron.py
# Tool for converting SN76489-based PSG VGM data to Acorn Electron
# By Simon Morris (https://github.com/simondotm/)
# See https://github.com/simondotm/vgm-packer
#
# Copyright (c) 2019 Simon Morris. All rights reserved.
#
# "MIT License":
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.




import functools
import itertools
import struct
import sys
import time
import binascii
import math
import operator
import os

from modules.vgmparser import VgmStream

class VgmElectron:

	OUTPUT_RAWDATA = False # output raw dumps of the data that was compressed by LZ4/Huffman
	VERBOSE = True

	def __init__(self):
		print("init")

			
	#----------------------------------------------------------
	# Utilities
	#----------------------------------------------------------


	# split the packed raw data into 11 separate streams
	# returns array of 11 bytearrays
	def split_raw(self, rawData, stripCommands = True):

		registers = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
		registers_opt = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

		latched_channel = -1

		output_block = bytearray()
		output_blocks = []

		for o in range(11):
			output_blocks.append( bytearray() )

		if stripCommands:
			register_mask = 15
		else:
			register_mask = 255

		# unpack the raw binary data in 11 arrays of register data without any deltas between them
		# eg. the raw chip writes to all 11 registers every frame
		n = 0
		Packet = True
		verbose = False

		while (Packet):
			packet_size = rawData[n]
			if verbose:
				print("packet_size=" + str(packet_size))
			n += 1
			if packet_size == 255:
				Packet = False
			else:
				for x in range(packet_size):
					d = rawData[n+x]
					#if verbose:
					#   print "  frame byte number=" +str(x)
					#   print "    frame byte=" +str(d)
					if d & 128:
						# latch
						c = (d>>5)&3
						latched_channel = c
						if d & 16:
							# volume
							if verbose:
								print(" volume on channel " + str(c))
							registers[c+7] = d & register_mask

						else:
							# tone
							if verbose:
								print(" tone on channel " + str(c))

							registers[c*2+0] = d & register_mask                    

					else:
						if verbose:
							print(" tone data on latched channel " + str(latched_channel))
						registers[latched_channel*2+1] = d # we no longer do any masking here # d & 63 # tone data only contains 6 bits of info anyway, so no need for mask
						if latched_channel == 3:
							print("ERROR CHANNEL")





				# emit current state of each of the 11 registers to 11 different bytearrays
				for x in range(11):
					output_blocks[x].append( registers[x] )

				# next packet                
				n += packet_size

		#print(output_blocks[6])

		#IGNORE we no longer do this - let the decoder do it instead.
		if False:
			# make sure we only emit tone3 when it changes, or 15 for no-change
			# this prevents the LFSR from being reset
			lastTone3 = 255  
			for x in range(len(output_blocks[6])):
				t = output_blocks[6][x]
				if t == lastTone3:
					output_blocks[6][x] = 15
				lastTone3 = t

		#    print(output_blocks[6])

		# Add EOF marker (0x08) to tone3 byte stream
		output_blocks[6].append(0x08)	# 0x08 is an invalid noise tone.

		# return the split blocks
		return output_blocks


	# given an array of data points, serialize it to a bytearray
	# size is the number of bytes to be used to represent each element in the source array.
	def toByteArray(self, array, size = 1):
		r = bytearray()
		for v in array:
			if size < 2:
				r.append(v & 255)
			else:
				r.append(v & 255)
				r.append(v >> 8)
		return r


	#----------------------------------------------------------
	# Process(filename)
	# Convert the given VGM file to an electron VGM file
	#----------------------------------------------------------
	def process(self, src_filename, dst_filename):

		# load the VGM file, or alternatively interpret as a binary
		if src_filename.lower()[-4:] != ".vgm":
			print("ERROR: Not a VGM source")
			return

		vgm = VgmStream(src_filename)
		data_block = vgm.as_binary()

		data_offset = 0

		# parse the header
		header_size = data_block[0]       # header size
		play_rate = data_block[1]       # play rate

		if header_size == 5 and play_rate == 50:
			packet_count = data_block[2] + data_block[3]*256       # packet count LO
			duration_mm = data_block[4]       # duration mm
			duration_ss = data_block[5]       # duration ss
			
			data_offset = header_size+1
			data_offset += data_block[data_offset]+1
			data_offset += data_block[data_offset]+1


			print("header_size=" +str(header_size))
			print("play_rate="+str(play_rate))
			print("packet_count="+str(packet_count))
			print("duration_mm="+str(duration_mm))
			print("duration_ss="+str(duration_ss))
			print("data_offset="+str(data_offset))
		else:
			print("No header.")

		print("")

		# Trim off the header data. The rest is raw data.
		data_block = data_block[data_offset:]


		#----------------------------------------------------------
		# Unpack the register data into 11 separate data streams
		#----------------------------------------------------------
		registers = self.split_raw(data_block, True)

		#----------------------------------------------------------
		# Begin VGM conversion to Electron
		#----------------------------------------------------------

        # Filter out channels we do not need
        # Modify all volumes to full or none
        # Interleave sound to a single channel
        # output final VGM
        





		vgm_stream = bytearray()
		vgm_time = 0
		
		electron_data = bytearray()

		# given an SN76489 tone register value, return the equivalent Electron ULA register setting
		def sn_to_electron(tone_value):
			
			# hack to protect against divbyzero
			if (tone_value == 0):
				tone_value = 1

			hz = float(vgm.vgm_source_clock) / ( 2.0 * float(tone_value) * 16.0)
			print("   sn_to_electron freq " + str(hz) + "hz")
			# electron 
			# Sound frequency = 1 MHz / [32 * (S + 1)]
			# f * 32*(S+1) = 1Mhz
			# 32*(S+1) = 1Mhz / f
			# (S+1) = 1Mhz / f*32

			#print ("SN freq is " + str(hz))

			ula6 = int( 1000000.0 / (hz * 32.0) ) - 1

			# check we are within range
			if ula6 < 0:
				print("  WARNING: Electron freqency '" + str(ula6) + "' too high (" + str(hz) + ")")
				ula6 = 0

			if ula6 > 255:
				print("  WARNING: Electron frequency '" + str(ula6) + "' too low (" + str(hz) + ")") 
				ula6 = 255
			
			return ula6

		#--------------------------------------------------------------
		# conversion settings
		#--------------------------------------------------------------


		# convert the register data to a vgm stream
		sample_interval = 882 # 50hz - TODO: use frame rate

		# 0-3 represents approx the loudest 50% of volumes (=ON), 4-15 are the quietest 50% (=OFF) 
		ATTENTUATION_THRESHOLD1 = 4
		ATTENTUATION_THRESHOLD2 = 6
		ATTENTUATION_THRESHOLD3 = 8

		# define the number of octaves to transpose whole song by, in case too much bass getting lost
		TRANSPOSE_OCTAVES1 = 0
		TRANSPOSE_OCTAVES2 = 0
		TRANSPOSE_OCTAVES3 = -1
		USE_TONE3 = True

		# TODO: make these all parameters
		# Add channel filter option
		# Add mix type options
		# --attentuation 468 --filter 123 --transpose 00F --mix 123 --arpeggio 2 --rate 50 
		# Add option to clamp or transpose out of range frequencies
		# Make the .ula output file filename.electron.ula
		# Add 0x01 as a terminating byte in the output ULA

		MIX_RATE = 2 # modulo 2 for interleaving channels

		# other options
		# bias for channels
		# transpose or silence out of range notes

		channel_mix = 0

		#--------------------------------------------------------------
		# pre-process music to suit Electron capabilities
		#--------------------------------------------------------------
		for i in range(len(registers[0])):

			print("Frame " + str(i))

			#--------------------------------------------------------------
			# step 1- map volumes to 1-bit precision
			#--------------------------------------------------------------
			# 11 registers per frame
			# Tone 0 HL Tone 1 HL Tone 2 HL Tone 3 Vol 0123
			for r in range(11):

				if r > 6:
					register_data = registers[r][i]
					# apply the threshold for each channel
					threshold = ATTENTUATION_THRESHOLD1
					if r == 8:
						threshold = ATTENTUATION_THRESHOLD2
					if r == 9:
						threshold = ATTENTUATION_THRESHOLD3

					# if its a volume, map to loudest volume or no volume (using logarithmic scale)
					if register_data < threshold:
						register_data = 0 # full volume
					else:
						register_data = 15 # zero volume

					registers[r][i] = register_data

			#--------------------------------------------------------------
			# step 2 - transpose to fit frequency range
			#--------------------------------------------------------------

			# final step - bring tone1 into the frequency range of the electron
			# if the frequency goes below the range of the ULA capabilities, add an octave

			def retune(octaves, l,h,v):

				#if (octaves == 0):
				#	print("  No transpose performed, octaves set to 0")
				#	return
					
				print( "  tonehi=" + str(registers[h][i]) + ", tonelo=" + str(registers[l][i]))

				tone_value = (registers[h][i] << 4) + registers[l][i] 
				if tone_value > 0:
					tone_freq = float(vgm.vgm_source_clock) / ( 2.0 * float(tone_value) * 16.0)
					print("  Retune, Channel " + str(int(l/2)) + " tone=" + str(tone_value) + ", freq=" + str(tone_freq))
					
					# electron baseline is 122Hz not 244Hz as the AUG states.
					baseline_freq = 1000000.0 / (32.0*256.0)
					target_freq = tone_freq
					retuned = 0


					transpose = abs(octaves)
					while retuned != transpose: # target_freq < baseline_freq:
						if (octaves < 0):
							target_freq /= 2.0
						else:
							target_freq *= 2.0
						retuned += 1


					# if cant reach baseline freq, transpose once, then silence if still too low :(
					if target_freq < baseline_freq:
						print("  WARNING: Freq too low - Added " + str(1) + " octave(s) - from " + str(target_freq) + " to " + str(target_freq*2.0) + "Hz")
						# better to just clamp low frequencies at the bottom, and risk tuning issues rather than transposition jumps
						target_freq = baseline_freq #*= 2.0
						retuned = 1
						if target_freq < baseline_freq:
							registers[v][i] = 15
							print("   Tone " + str(i) + " silenced because frequency too low - " + str(target_freq))
							#target_freq *= 2.0
							#retuned += 1



					if retuned:
						#print("  WARNING: Freq too low - Added " + str(retuned) + " octave(s) - from " + str(tone_freq) + " to " + str(target_freq) + "Hz")
						tone_value = int( round( float(vgm.vgm_source_clock) / (2.0 * target_freq * 16.0 ) ) )
						registers[h][i] = tone_value >> 4
						registers[l][i] = tone_value & 15

			# transpose
			#if TRANSPOSE_OCTAVES > 0:
			print(" Transposing ")
			retune(TRANSPOSE_OCTAVES1, 0,1,7)
			retune(TRANSPOSE_OCTAVES2, 2,3,8)
			retune(TRANSPOSE_OCTAVES3, 4,5,9)

			#--------------------------------------------------------------
			# Step 3 - mix the 2 primary channels down to 1 channel
			#--------------------------------------------------------------
			# map channel 2 to channel 1
			# noise channel is completely ignored

			print(" Downmix channels ")
			#print("Frame " + str(i))

			vol1 = registers[7][i]
			vol2 = registers[8][i]
			vol3 = registers[9][i]

			tone_active = vol1 != 15 or vol2 != 15 or vol3 != 15

			if tone_active:


				print("  Tone active, mixing")
				
				output_tone = 1
				
				# interleaving of channels 1+2 is done on odd/even frames for a consistent effect
				mix = (i % MIX_RATE) == 0 #(i & 1) == 0
				# random is no good, thought it might average out but it sounds , well random
				#mix = random.random() < 0.5 

				# test code to see if modulo 3 any good, it wasn't
				if False:

					if channel_mix == 0 and vol1 != 0:
						channel_mix = (channel_mix + 1) % 3

					if channel_mix == 1 and vol2 != 0:
						channel_mix = (channel_mix + 1) % 3

					if channel_mix == 1 and vol3 != 0:
						channel_mix = (channel_mix + 1) % 3

					

					output_tone = (channel_mix % 3) + 1
					print("output tone=" + str(output_tone))
					channel_mix = (channel_mix + 1) % 3
						

				if True:

					# detect if channel 1 needs priority this frame
					# - its volume is on, and the alternative frame mix flag is good
					c1p = vol1 == 0 and mix

					# don't give channel 2 priority if tone is the same and channel1 is playing
					c1f = (registers[1][i] << 4) + registers[0][i] 
					c2f = (registers[3][i] << 4) + registers[2][i] 
					sametone = (c1f == c2f/2) or (c1f == c2f * 2) or (c1f == c2f)
					sametone = sametone and (vol1 == vol2) and (vol1 == 0)

					if vol1 == 0 and sametone: #diff < 100: #registers[0][i] == registers[2][i] and registers[1][i] == registers[2][i] and vol1 == 0:
						c1p = True
						print("  NOTE: channel 1 & channel 2 have same tone")

					

					# replace channel 1 data with channel 2 data
					# if, channel2 is active, but c1 doesn't have priority this frame
					if vol2 == 0 and not c1p:# and vol1 != 0:
						output_tone = 2

					# if no volume on tone1, we can look at channel 3 too
					if USE_TONE3:
						#if registers[7][i] == 15:
						if vol1 == 15 and vol2 == 15 and vol3 == 0 and not mix:# and not c1p and output_tone != 2:
							print("tone3 active")
							output_tone = 3

				# pick which tone to output
				if output_tone == 1:
					# do nothing
					output_tone = 1
				elif output_tone == 2:
					registers[0][i] = registers[2][i]
					registers[1][i] = registers[3][i]
					registers[7][i] = registers[8][i]
				elif output_tone == 3:
					registers[0][i] = registers[4][i]
					registers[1][i] = registers[5][i]
					registers[7][i] = registers[9][i]
				else:
					print("UNHANDLED CASE - output_tone not set")




			# output ULA data
			final_volume = registers[7][i]
			ula_tone = 0 # zero is highest freq. so inaudible, so thats how we handle volume
			if final_volume == 0:
				final_tone1 = (registers[1][i] << 4) + registers[0][i] 
				ula_tone = sn_to_electron(final_tone1)
			electron_data.append( ula_tone )
				

		# write to output ULA file
		ula_file = open(dst_filename + ".ula.bin", 'wb')
		ula_file.write(electron_data)
		ula_file.close()



		#--------------------------------------------------------------
		# Final stage - output to vgm
		#--------------------------------------------------------------
		
		#           Tone1-----  Tone2-----  Tone3-----  Tone4 Vol1  Vol2  Vol3  Vol4
		control = [ 0x80, 0x00, 0xa0, 0x00, 0xc0, 0x00, 0xe0, 0x90, 0xb0, 0xd0, 0xf0 ]
		#filter = [ 0,1,2,3,7,8 ]
		#filter = [ 2,3,8 ]
		filter = [ 0,1,7 ]
		#filter = [ 0,1,2,3,4,5,6,7,8,9,10 ]


		last_tone3 = 255
		for i in range(len(registers[0])):

			# 11 registers per frame
			# Tone 0 HL Tone 1 HL Tone 2 HL Tone 3 Vol 0123
			for r in range(11):
				register_data = registers[r][i]
				
				# dont update noise register unless different

				update = True
				if r == 6:
					if register_data == last_tone3:
						update = False
					else:
						last_tone3 = register_data

			

				if not r in filter:
					update = False

				if update:
					register_data |= control[r]
					vgm_stream.extend( struct.pack('B', 0x50) ) # COMMAND
					vgm_stream.extend( struct.pack('B', register_data) ) # DATA

			# next frame
			if sample_interval == 882: # wait 50
				vgm_stream.extend( struct.pack('B', 0x63) ) 
			elif sample_interval == 735: # wait 60
				vgm_stream.extend( struct.pack('B', 0x62) ) 
			else:
				vgm_stream.extend( struct.pack('B', 0x61) ) 
				vgm_stream.extend( struct.pack('B', sample_interval % 256) ) 
				vgm_stream.extend( struct.pack('B', sample_interval / 256) )                         
	
		
		# END command
		vgm_stream.extend( struct.pack('B', 0x66) ) 










		vgm.write_vgm(vgm_stream, dst_filename)

		#output = bytearray()

		# write the electron vgm file
		#open(dst_filename, "wb").write( output )


#------------------------------------------------------------------------
# Main()
#------------------------------------------------------------------------

import argparse



# Determine if running as a script
if __name__ == '__main__':

	print("Vgm2Electron.py : VGM music converter for Acorn Electron")
	print("Written in 2019 by Simon Morris, https://github.com/simondotm/vgm-packer")
	print("")

	epilog_string = ""

	parser = argparse.ArgumentParser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog=epilog_string)

	parser.add_argument("input", help="VGM source file (must be single SN76489 PSG format) [input]")
	parser.add_argument("-o", "--output", metavar="<output>", help="write VGC file <output> (default is '[input].vgc')")
	parser.add_argument("-v", "--verbose", help="Enable verbose mode", action="store_true")
	args = parser.parse_args()


	src = args.input
	dst = args.output
	if dst == None:
		dst = os.path.splitext(src)[0] + ".electron.vgm"

	# check for missing files
	if not os.path.isfile(src):
		print("ERROR: File '" + src + "' not found")
		sys.exit()

	packer = VgmElectron()
	packer.VERBOSE = args.verbose
	packer.process(src, dst)



