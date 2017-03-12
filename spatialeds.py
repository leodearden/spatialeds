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
import socket
import fcntl
import struct
import errno
import optparse
try:
    import json
except ImportError:
    import simplejson as json


import opc
import color_utils

# use for mode switching. Modes are as follows:
# 0: chill
# 1: dance
# 2: rain
patternNumber = 2

maxPatternNumber = 3

n_pixels = 800  # number of pixels in the included "wall" layout
pixels_per_string = 50
fps = 60         # frames per second

start_time = time.time()

pixels = [(0.0, 0.0, 0.0) for i in range(n_pixels)]

# Stack overflow special. I'll figure out what it does if it stops working.
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

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
            pixels[ii] = (r, g, b)

def fadeDownTo(fromVal, toVal, step):
    result = [0.0, 0.0, 0.0]

    for colour in range(3):
        if fromVal[colour] != toVal[colour]:
            diff = fromVal[colour] - toVal[colour]
            result[colour] = fromVal[colour] - diff*step
        else:
            result[colour] = toVal[colour]

    return tuple(result)

warmWhite = (197, 255, 143)
softWarmWhite = tuple(x*0.3 for x in warmWhite)

#sunLight = (255, 215, 120)
sunLight = (247, 223, 160)

stdDev = 25

class largeDrop:
    def __init__(self, coords_, colour_, spreadPower_, fadeSpeed_):
        self.coords = coords_
        self.colour = colour_
        self.spreadPower = spreadPower_
        self.fadeSpeed = fadeSpeed_
        self.spawnTime = time.time()
        self.expired = False
        self.maxColour = 255
        self.colourThreshold = min(softWarmWhite)
        self.fadeFactor = (1.0, 1.0, 1.0)


    def tick(self):
        self.fadeFactor = tuple(speed ** (time.time() - self.spawnTime) for speed in self.fadeSpeed)
        if self.maxColour < self.colourThreshold:
            self.expired = True
        self.maxColour = 0

    def getInfluence(self, pointCoords):
        distanceBetween = math.sqrt((self.coords[0]-pointCoords[0])**2 + (self.coords[1]-pointCoords[1])**2)
        influenceFactor = 1 / max(distanceBetween**self.spreadPower, 0.01)

        result = tuple(channel * influenceFactor * self.fadeFactor[i] for i, channel in enumerate(self.colour))
        for colour in result:
            if colour > self.maxColour:
                self.maxColour = colour

        return result

largeDrops = []

def rain(coordinates, nextDrop, avgInterval, fadeStep):
    global largeDrops

    if (random.random() < 0.05 and len(largeDrops) < 5):
        fadeSpeed = random.uniform(0.5, 0.95)
        largeDrops.append(largeDrop((random.uniform(-5, 5), random.uniform(-5, 5), 0.0), tuple(random.uniform(128, 255) for i in range(3)), random.uniform(1, 2), tuple(color_utils.clamp(random.gauss(fadeSpeed, fadeSpeed/8), 0.5, 0.95) for i in range(3))))

    for drop in largeDrops:
        drop.tick()

    largeDrops = [x for x in largeDrops if not x.expired]

    for ii in range(n_pixels):
        bgColour = [0.0, 0.0, 0.0]
        for drop in largeDrops:
            influence = drop.getInfluence(coordinates[ii])
            for colour in range(3):
                bgColour[colour] = min(bgColour[colour] + influence[colour], 255)
                if bgColour[colour] < softWarmWhite[colour]:
                    bgColour[colour] = softWarmWhite[colour]


        stringPosition = ii % pixels_per_string
        cosFactor = 2*3.14/pixels_per_string
        timeFactor = 0.07
        colourOffset = (0.05, 0.1, 0.0)
        # slowWaveVal = color_utils.remap(math.cos(-time.time() + stringPosition*cosFactor + offset)
        pixels[ii] = fadeDownTo(pixels[ii], bgColour, fadeStep)

    if (time.time() > nextDrop):
        pixels[random.randrange(n_pixels)] = tuple(color_utils.clamp(random.gauss(x, stdDev*255.0/x), pixels[ii][i], 255) for i, x in enumerate(warmWhite))
        nextDrop = time.time() + random.gauss(avgInterval, avgInterval/2)

    return nextDrop


def main():
    global patternNumber

    #-------------------------------------------------------------------------------
    # set up UDP socket

    UDP_IP = get_ip_address("wlan0")
    UDP_PORT = 5005

    print ("Connected to WLAN with IP " + UDP_IP)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.bind((UDP_IP, UDP_PORT))

    #-------------------------------------------------------------------------------
    # handle command line

    parser = optparse.OptionParser()
    parser.add_option('-l', '--layout', dest='layout', default='disc.json',
                      action='store', type='string',
                      help='layout file')
    parser.add_option('-s', '--server', dest='server', default='127.0.0.1:7890',
                      action='store', type='string',
                      help='ip and port of server')

    options, args = parser.parse_args()

    #-------------------------------------------------------------------------------
    # parse layout file

    print
    print '    parsing layout file'
    print

    coordinates = []
    for item in json.load(open(options.layout)):
        if 'point' in item:
            coordinates.append(tuple(item['point']))

    #-------------------------------------------------------------------------------
    # connect to server

    client = opc.Client(options.server)
    if client.can_connect():
        print('    connected to %s' % options.server)
    else:
        # can't connect, but keep running in case the server appears later
        print('    WARNING: could not connect to %s' % options.server)
    print('')


    #-------------------------------------------------------------------------------
    # send pixels

    print('    sending pixels forever (control-c to exit)...')
    print('')

    nextDrop = 0.0

    while True:
        #---------------------------------------------------------------------------
        # listen for commands from the remote

        try:
            data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        except socket.error, e:
            # nothing available
            pass
        else:
            patternNumber = (patternNumber + 1) % maxPatternNumber

        #---------------------------------------------------------------------------
        # use the current pattern

        if patternNumber == 0:
            rainbowWaves(29, -13, 19)

        elif patternNumber == 1:
            rainbowWaves(1.4, -2.6, 3.8)

        elif patternNumber == 2:
            nextDrop = rain(coordinates, nextDrop, 0.005, 0.1)

        client.put_pixels(pixels, channel=0)
        time.sleep(1 / fps)

if __name__ == "__main__":
    main()
