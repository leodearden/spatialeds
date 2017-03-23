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
import itertools
from operator import add
try:
    import json
except ImportError:
    import simplejson as json


import opc
import color_utils
import colours

# use for mode switching. Modes are as follows:
# 0: chill
# 1: dance
# 2: rain
# 3: discs
# 4: lava lamp
# 5: rainbow waves
# 6: wobbler
patternNumber = 6

maxPatternNumber = 7

n_pixels = 800  # number of pixels in the included "wall" layout
n_strings = 16
pixels_per_string = int(n_pixels/n_strings)

fps = 60         # frames per second

start_time = time.time()

pixels = [(0.0, 0.0, 0.0) for i in range(n_pixels)]
random_values0 = [random.random() for ii in range(n_pixels)]
random_values1 = [random.random() for ii in range(n_pixels)]
random_values2 = [random.random() for ii in range(n_pixels)]
random_values3 = [random.random() for ii in range(n_pixels)]
random_values4 = [random.random() for ii in range(n_pixels)]
random_values5 = [random.random() for ii in range(n_pixels)]
random_values6 = [random.random() for ii in range(n_pixels)]

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
    def __init__(self, coords_, colour_, spreadPower_, fadeSpeed_, coordList_):
        self.coords = coords_
        self.colour = colour_
        self.spreadPower = spreadPower_ #tuple(random.gauss(spreadPower_, spreadPower_/4) for i in range(3))
        self.fadeSpeed = fadeSpeed_
        self.spawnTime = time.time()
        self.expired = False
        self.maxColour = 255
        self.colourThreshold = min(softWarmWhite)
        self.fadeFactor = (1.0, 1.0, 1.0)
        self.distances = []
        self.distances = tuple(math.sqrt((self.coords[0]-point[0])**2 + (self.coords[1]-point[1])**2) for point in coordList_)


    def tick(self):
        self.fadeFactor = tuple(speed ** (time.time() - self.spawnTime) for speed in self.fadeSpeed)
        if self.maxColour < self.colourThreshold:
            self.expired = True
        self.maxColour = 0

    def getInfluence(self, pointIndex):
        #influenceFactor = tuple(1 / max(self.distances[pointIndex]**spread, 0.01) for spread in self.spreadPower)
        influenceFactor = 1 / max(self.distances[pointIndex]**self.spreadPower, 0.01)

        #result = tuple(channel * influenceFactor[i] * self.fadeFactor[i] for i, channel in enumerate(self.colour))
        result = tuple(channel * influenceFactor * self.fadeFactor[i] for i, channel in enumerate(self.colour))
        for colour in result:
            if colour > self.maxColour:
                self.maxColour = colour

        return result

largeDrops = []

def rain(coordinates, nextDrop, avgInterval, fadeStep):
    global largeDrops

    if (random.random() < 0.05 and len(largeDrops) < 3):
        fadeSpeed = random.uniform(0.5, 0.95)
        largeDrops.append(largeDrop((random.uniform(-5, 5), random.uniform(-5, 5), 0.0), tuple(random.uniform(128, 255) for i in range(3)), random.uniform(1, 2), tuple(color_utils.clamp(random.gauss(fadeSpeed, fadeSpeed/8), 0.5, 0.95) for i in range(3)), coordinates))

    for drop in largeDrops:
        drop.tick()

    largeDrops = [x for x in largeDrops if not x.expired]

    for ii in range(n_pixels):
        bgColour = [0.0, 0.0, 0.0]
        for drop in largeDrops:
            influence = drop.getInfluence(ii)
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

lastDiscShift = 0
timeBetweenDiscShifts = 5
stringColours = list((0, 0, 0) for i in range(n_pixels))
offset = 0.0

def discs():
    global offset
    global stringColours
    global lastDiscShift

    # offset -= 0.05

    for ii in range(pixels_per_string):
        avgColour = [0, 0, 0]

        for pixel in range(ii-2, ii+3):
            indexPixel = pixel
            if indexPixel < 0:
                indexPixel += pixels_per_string
            if indexPixel >= pixels_per_string:
                indexPixel -= pixels_per_string

            for colour in range(3):
                avgColour[colour] += stringColours[indexPixel][colour]


        for colour in range(3):
            avgColour[colour] /= 5

        stringColours[ii] = fadeDownTo(stringColours[ii], avgColour, 0.1)

    if time.time() - lastDiscShift > timeBetweenDiscShifts:
        flareLevel = 64
        lastDiscShift = time.time()
        numRings = 5
        ringThickness = 10
        newPalette = random.sample(colours.colours, numRings)
        stringColours = list(itertools.chain.from_iterable(list([x]*ringThickness for x in newPalette)))

    blendedStringColours = []

    remainder = math.fmod(offset, 1.0)
    for ii in range(pixels_per_string):
        blendedStringColours.append(tuple(int((stringColours[ii][colour] * (remainder)) + (stringColours[(ii+1)%pixels_per_string][colour] * (1-remainder))) for colour in range(3)))
        # stringIndex = int(offset+ii) % pixels_per_string
        # pixels[ii] = tuple(colour + flareLevel for colour in fadeVal)

    for ii in range(n_pixels):
        pixels[ii] = blendedStringColours[ii % pixels_per_string]


pixelOrder = 0
lastPixelOrderSwitch = 0
minPixelOrderSwitchInterval = 5

def wobbler():
    global pixelOrder
    global lastPixelOrderSwitch
    timeCosFactor = 2
    wobbleAmplitude = 5
    bandRadius = pixels_per_string/2 + math.cos(time.time()/timeCosFactor)*18 - 13
    colourOffset = 3.14/6
    cosFactor = 6*3.14/(n_pixels/pixels_per_string)
    t = time.time()*4
    offsetOrdering = [ [ 0, 1, 2], [0, 2, 1], [1, 0, 2] ]

    if math.cos(time.time()/timeCosFactor) < -0.99 and time.time() - lastPixelOrderSwitch > minPixelOrderSwitchInterval:
        pixelOrder = (pixelOrder + 1) % len(offsetOrdering)
        lastPixelOrderSwitch = time.time()

    for string in range(n_strings):
        bandLocation = tuple(bandRadius + wobbleAmplitude*math.cos(t + string*cosFactor + colourOffset*offsetOrdering[pixelOrder][colour]) for colour in range(3))
        for pixel in range(pixels_per_string):
            pixCol = [0, 0, 0]
            for colour in range(3):
                distance = bandLocation[colour] - pixel
                if distance < 0:
                    distance *= -1

                pixCol[colour] = (2 + max(bandRadius, 0.0000001)/10)/distance

            r, g, b = color_utils.gamma(pixCol, 2.2)
            pixels[string*pixels_per_string + pixel] = (g*255, r*255, b*255)

def lavaLamp(coordinates):
    t = time.time() * 0.6
    for ii in range(n_pixels):
        # make moving stripes for x, y, and z
        x, y, z = coordinates[ii]
        y += color_utils.cos(x + 0.2*z, offset=0, period=1, minn=0, maxx=0.6)
        z += color_utils.cos(x, offset=0, period=1, minn=0, maxx=0.3)
        x += color_utils.cos(y + z, offset=0, period=1.5, minn=0, maxx=0.2)

        # rotate
        x, y, z = y, z, x

        # make x, y, z -> r, g, b sine waves
        r = color_utils.cos(x, offset=t / 4, period=2, minn=0, maxx=1)
        g = color_utils.cos(y, offset=t / 4, period=2, minn=0, maxx=1)
        b = color_utils.cos(z, offset=t / 4, period=2, minn=0, maxx=1)
        r, g, b = color_utils.contrast((r, g, b), 0.5, 1.5)

        # black out regions
        r2 = color_utils.cos(x, offset=t / 10 + 12.345, period=3, minn=0, maxx=1)
        g2 = color_utils.cos(y, offset=t / 10 + 24.536, period=3, minn=0, maxx=1)
        b2 = color_utils.cos(z, offset=t / 10 + 34.675, period=3, minn=0, maxx=1)
        clampdown = (r2 + g2 + b2)/2
        clampdown = color_utils.remap(clampdown, 0.8, 0.9, 0, 1)
        clampdown = color_utils.clamp(clampdown, 0, 1)
        r *= clampdown
        g *= clampdown
        b *= clampdown

        # color scheme: fade towards blue-and-orange
        g = g * 0.6 + ((r+b) / 2) * 0.4

        # apply gamma curve
        # only do this on live leds, not in the simulator
        r, g, b = color_utils.gamma((r, g, b), 2.2)

        pixels[ii] = (g*256, r*256, b*256)

def rainbowWavesGetPixelColour(rgb0, rgb1, rgb2, waveOffset, random_values, ii):
    t = time.time()*0.6

    if random_values[ii] < 0.5:
        r, g, b = tuple(rgb0[channel] / 128.0 for channel in range(3))
    elif random_values[ii] < 0.85:
        r, g, b = tuple(rgb1[channel] / 128.0 for channel in range(3))
    else:
        r, g, b = tuple(rgb2[channel] / 128.0 for channel in range(3))

    stringIndex = ii % pixels_per_string

    # twinkle occasional LEDs
    twinkle_speed = 0.03
    twinkle_density = 0.8
    twinkle = (random_values[ii]*7 + time.time()*twinkle_speed) % 1
    twinkle = abs(twinkle*2 - 1)
    twinkle = color_utils.remap(twinkle, 0, 1, -1/twinkle_density, 1.1)
    twinkle = color_utils.clamp(twinkle, -0.5, 1.1)
    twinkle **= 5
    twinkle *= color_utils.cos(t - stringIndex/float(pixels_per_string), offset=waveOffset, period=7, minn=0.1, maxx=1.0) ** 20
    twinkle = color_utils.clamp(twinkle, -0.3, 1)
    r *= twinkle
    g *= twinkle
    b *= twinkle

    # apply gamma curve
    # only do this on live leds, not in the simulator
    #r, g, b = color_utils.gamma((r, g, b), 2.2)

    return (g*256, r*256, b*256)
    #pixels[ii] =  (g*256, r*256, b*256)

def rainbowWaves(coordinates):
    offsetMultiplier = 1.0/7
    for ii in range(n_pixels):
        pixels[ii] = (0, 0, 0)
        pixels[ii] = map(add, pixels[ii], rainbowWavesGetPixelColour(colours.hardPink, colours.crimson, colours.neonRose, 0.0, random_values0, ii))
        pixels[ii] = map(add, pixels[ii], rainbowWavesGetPixelColour(colours.orange, colours.brightOrange, colours.lightOrange, offsetMultiplier*1, random_values1, ii))
        pixels[ii] = map(add, pixels[ii], rainbowWavesGetPixelColour(colours.paleYellow, colours.brightYellow, colours.lightOrange, offsetMultiplier*2, random_values2, ii))
        pixels[ii] = map(add, pixels[ii], rainbowWavesGetPixelColour(colours.mint, colours.lime, colours.aqua, offsetMultiplier*3, random_values3, ii))
        pixels[ii] = map(add, pixels[ii], rainbowWavesGetPixelColour(colours.cobalt, colours.sky, colours.indigo, offsetMultiplier*4, random_values4, ii))
        pixels[ii] = map(add, pixels[ii], rainbowWavesGetPixelColour(colours.indigo, colours.neonPurple, colours.imperialPurple, offsetMultiplier*5, random_values5, ii))
        pixels[ii] = map(add, pixels[ii], rainbowWavesGetPixelColour(colours.lilac, colours.neonPurple, colours.neonRose, offsetMultiplier*6, random_values6, ii))

udpInitialised = False

def main():
    global patternNumber
    global udpInitialised


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
        if not udpInitialised:
            #-------------------------------------------------------------------------------
            # set up UDP socket

            try:
                UDP_IP = get_ip_address("wlan0")
            except Exception as e:
                pass
            else:
                udpInitialised = True
                UDP_PORT = 5005

                print ("Connected to WLAN with IP " + UDP_IP)

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setblocking(0)
                sock.bind((UDP_IP, UDP_PORT))
        else:
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

        elif patternNumber == 3:
            discs()

        elif patternNumber == 4:
            lavaLamp(coordinates)

        elif patternNumber == 5:
            rainbowWaves(coordinates)

        elif patternNumber == 6:
            wobbler()

        client.put_pixels(pixels, channel=0)
        time.sleep(1 / fps)

if __name__ == "__main__":
    main()
