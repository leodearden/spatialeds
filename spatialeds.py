#!/usr/bin/env python

"""
Spatialised LED pattern generator.

Based on a demo client for Open Pixel Control
http://github.com/zestyping/openpixelcontrol

Creates a shifting rainbow plaid pattern by overlaying different sine waves
in the red, green, and blue channels.

To run:
First start the gl simulator using the included "wall" layout

    make
    bin/gl_server layouts/wall.json

Then run this script in another shell to send colors to the simulator

    python_clients/raver_plaid.py

"""

from __future__ import division
import sys
import os
cwd = os.getcwd()

sys.path.insert(0, cwd+"/openpixelcontrol/python/")

import time
import math
import random

import opc
import color_utils
from gamma import gamma_table

# use for mode switching. Modes are as follows:
# 0: chill
# 1: dance
# 2: rain
patternNumber = 2

n_pixels = 800  # number of pixels in the included "wall" layout
fps = 60         # frames per second

start_time = time.time()

pixels = [(0.0, 0.0, 0.0) for i in range(n_pixels)]
output = [(0.0, 0.0, 0.0) for i in range(n_pixels)]

def rainbowWaves(speed_r, speed_g, speed_b):
        # how many sine wave cycles are squeezed into our n_pixels
        # 24 happens to create nice diagonal stripes on the wall layout
        freq_r = 24
        freq_g = 24
        freq_b = 24

        t = (time.time() - start_time) * 5

        for ii in range(n_pixels):
            pct = (ii / n_pixels)
            # diagonal black stripes
            pct_jittered = (pct * 77) % 37
            blackstripes = color_utils.cos(pct_jittered, offset=t*0.05, period=1, minn=-1.5, maxx=1.5)
            blackstripes_offset = color_utils.cos(t, offset=0.9, period=60, minn=-0.5, maxx=3)
            blackstripes = color_utils.clamp(blackstripes + blackstripes_offset, 0, 1)
            # 3 sine waves for r, g, b which are out of sync with each other
            r = blackstripes * color_utils.remap(math.cos((t/speed_r + pct*freq_r)*math.pi*2), -1, 1, 0, 256)
            g = blackstripes * color_utils.remap(math.cos((t/speed_g + pct*freq_g)*math.pi*2), -1, 1, 0, 256)
            b = blackstripes * color_utils.remap(math.cos((t/speed_b + pct*freq_b)*math.pi*2), -1, 1, 0, 256)
            output[ii] = (r, g, b)

def fadeDownTo(fromVal, toVal, step):
    result = [0.0, 0.0, 0.0]

    for colour in range(3):
        if fromVal[colour] > toVal[colour] + step:
            result[colour] = fromVal[colour] - step
        else:
            result[colour] = toVal[colour]

    return tuple(result)

# do this in 10-bit, because otherwise the gamma correction looks janky
warmWhite = (859, 1023, 683)
softWarmWhite = tuple(x*0.6 for x in warmWhite)

def rain(nextDrop, avgInterval, fadeStep):
    if (time.time() > nextDrop):
        pixels[random.randrange(n_pixels)] = warmWhite
        nextDrop = time.time() + random.gauss(avgInterval, avgInterval/2)

    for ii in range(n_pixels):
        pixels[ii] = fadeDownTo(pixels[ii], softWarmWhite, fadeStep)
        output[ii] = tuple(gamma_table[int(x)] for x in pixels[ii])
        # if ii == 0:
            # print softWarmWhite

    return nextDrop


def main():
    #-------------------------------------------------------------------------------
    # handle command line

    if len(sys.argv) == 1:
        IP_PORT = 'localhost:7890'
    elif len(sys.argv) == 2 and ':' in sys.argv[1] and not sys.argv[1].startswith('-'):
        IP_PORT = sys.argv[1]
    else:
        print('''
    Usage: raver_plaid.py [ip:port]

    If not set, ip:port defauls to 127.0.0.1:7890
    ''')
        sys.exit(0)


    #-------------------------------------------------------------------------------
    # connect to server

    client = opc.Client(IP_PORT)
    if client.can_connect():
        print('    connected to %s' % IP_PORT)
    else:
        # can't connect, but keep running in case the server appears later
        print('    WARNING: could not connect to %s' % IP_PORT)
    print('')


    #-------------------------------------------------------------------------------
    # send pixels

    print('    sending pixels forever (control-c to exit)...')
    print('')

    nextDrop = 0.0

    while True:
        if patternNumber == 0:
            rainbowWaves(29, -13, 19)

        elif patternNumber == 1:
            rainbowWaves(1.4, -2.6, 3.8)

        elif patternNumber == 2:
            nextDrop = rain(nextDrop, 0.05, 1)

        client.put_pixels(output, channel=0)
        time.sleep(1 / fps)

if __name__ == "__main__":
    main()
