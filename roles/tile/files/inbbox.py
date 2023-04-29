#!/usr/bin/env python3

import re,math
import argparse
import sys

def TileToMeters(tx, ty, zoom):
  initialResolution = 20037508.342789244 * 2.0 / 256.0
  originShift = 20037508.342789244
  tileSize = 256.0
  zoom2 = (2.0**zoom)
  res = initialResolution / zoom2
  mx = (res*tileSize*(tx+1))-originShift
  my = (res*tileSize*(zoom2-ty))-originShift
  return mx, my

# this will give the BBox Parameter from x,y,z
def TileToBBox(z,x,y):
  x1,y1=TileToMeters(x-1,y+1,z)
  x2,y2=TileToMeters(x,y,z)
  lon1=x2lon(x1)
  lon2=x2lon(x2)
  lat1=y2lat(y1)
  lat2=y2lat(y2)
  return [[lon1,lat1],[lon2,lat2]]

def y2lat(y):
  return (180 / math.pi) * (2 * math.atan(math.exp( y/6378137)) - math.pi/2)

def x2lon(x):
  return (180 / math.pi) * x/6378137

def flush_out(str):
  sys.stdout.write(str)
  sys.stdout.flush()

parser = argparse.ArgumentParser(description='Apache Rewritemap cmd: check if tile url is inside given bounding box')
parser.add_argument('-b','--bbox', nargs=4, type=float, required=True, help='bounding box')
parser.add_argument('-m','--minz', type=int, required=True, help='minzoom (return false if zoom < minzoom)')
args = parser.parse_args()

bbox=[[args.bbox[0],args.bbox[1]],[args.bbox[2],args.bbox[3]]]

while sys.stdin:
  try:
    strLine = sys.stdin.readline().strip()
    # our URI in the longest form is
    # http://<our-server>/<subdir>/<z>/<x>/<y>.<ext>
    # we are only interested in <z>/<x>/<y>
    regex='.*?([0-9]+)/([0-9]+)/([0-9]+)\....$'
    res=re.findall(regex,strLine)
    if len(res) != 1:
      flush_out("xNULL\n")
    else:
      if (int(res[0][0]) >= args.minz):
        tcoor=TileToBBox(int(res[0][0]),int(res[0][1]),int(res[0][2]))
        if ((tcoor[0][0] <= bbox[1][0]) and (tcoor[1][1] >= bbox[0][1]) and (tcoor[1][0] >= bbox[0][0]) and (tcoor[0][1] <= bbox[1][1])):
          flush_out("TRUE\n")
        else:
          flush_out("FALSE\n")
      else:
        flush_out("FALSE\n")
  except:
    flush_out("NULL\n")

