from gdpc import geometry as GEO
from gdpc import interface as INTF
from gdpc import toolbox as TB
from gdpc import worldLoader as WL

import cv2
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm

VIEW_RADIUS = 5

# Euclidean distance between two patches
def patchDistances(p1, p2):
    return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

class Patch:
    def __init__(self, i, j, heights, size, xz_coordinates, WorldSlice):
        self.size = size
        self.xz_coordinates = xz_coordinates
        self.region_heights = heights
        self.min_y = np.min(heights)
        self.max_y = np.max(heights)
        self.WorldSlice = WorldSlice
        self.i = i
        self.j = j

        self.type = self.getPatchType()

        self.undeveloped = True
        self.developable = False if self.type in ['water', 'tree', 'lava', 'cave', 'road'] else True

        # Patch coords (avg of blocks)
        self.y = self.getAvgHeight()
        self.x = np.mean(xz_coordinates.T[0].flatten())
        self.z = np.mean(xz_coordinates.T[1].flatten())

        self.parcel = None

        self.population = 0 # Total population
        self.e = self.y # Elevation
        self.dwater = np.inf # Distance from water
        self.dp = np.inf # Distance to primary roads
        self.eh = None # Elevation advantage
        self.ev = None # Variance in elevation (negative)
        self.epv = None # Variance in elevation (positive)
        self.efp = None # Flood plain elevation
        self.dpr = None # Proximity to primary roads
        self.dw = None # Proximity to water score
        self.dm = None # Proximity to market
        self.dr = None # Residential denisty
        self.dc = None # Comercial density
        self.di = None # Industrial density
        self.cc = None # Comercial clustering 
        self.dpk = np.inf # Distance to park
        self.dcom = np.inf # Distance to commercial development

    # Residential value
    def Vr(self):
        return 1 

    # Residential value
    def Vc(self):
        return 1

    # Residential value
    def Vi(self):
        return 1

    def update_dwater(self, patches):
        water_patches = [p for p in patches.flatten() if p.type == 'water']
        self.dwater  = min([patchDistances(self, water_source) for water_source in water_patches]+[np.inf])

    def update_eh(self, patches, e_offset=0):
        avg_e = np.mean([p.e for p in patches.flatten()])
        self.eh = np.exp((self.e - avg_e - e_offset)**2 / -128)

    def update_ev(self, patches):
        region = patches[max(0,self.i-VIEW_RADIUS):self.i+VIEW_RADIUS+1,
                         max(0, self.j-VIEW_RADIUS):self.j+VIEW_RADIUS+1]
        region_e = [p.e for p in np.array(region).flatten()]
        self.ev = np.exp( -np.var(region_e) )

    def update_epv(self, patches):
        region = patches[max(0,self.i-VIEW_RADIUS):self.i+VIEW_RADIUS+1,
                         max(0, self.j-VIEW_RADIUS):self.j+VIEW_RADIUS+1]
        region_e = [p.e for p in np.array(region).flatten()]
        self.epv = np.var(region_e)

    def update_efp(self, patches, ew):
        self.efp = 1/ ( (self.e - ew)**2 + .1) # Changed from origianl paper to avoid division by zero

    def update_dpr(self):
        self.dpr = np.exp(-self.dp)

    def update_dw(self):
        self.dw = (1 + self.dwater)**-2

    def update_dm(self):
        self.dm = 0.5*(1 + self.dpr)*self.cc*self.dc
        return
    
    def update_dr(self, patches):
        # TO DO (need parcel implementation)
        self.dr = 0
        return

    def update_dc(self, patches):
        # TO DO (need parcel implementation)
        self.dc = 0
        return

    def update_di(self, patches):
        # TO DO (need parcel implementation)
        self.di = 0
        return

    def update_cc(self, patches):
        # TO DO (need parcel implementation)
        self.cc = 1
        return

    def boundToParcel(self, parcel):
        self.parcel = parcel

    def getAvgHeight(self):
        return np.mean(self.region_heights)

    def getPatchBlocks(self):
        blocks = np.empty((self.size, self.size), dtype=object)

        for i in range(self.size):
            for j in range(self.size):
                x, z = self.xz_coordinates[i, j]
                y = self.region_heights[i, j]

                # y coordinate returned from WorldSlice.heightmaps['MOTION_BLOCKING_NO_LEAVES']  is
                # the air block on top. If we want to know the block type have to check bellow
                block = self.WorldSlice.getBlockAt(x, y-1, z) # Using WorldSlice instead of IT.getBlock for performance (checks and conversions are unnecessary here)
                blocks[i, j] = block

        return blocks


    def getPatchType(self):
        blocks = self.getPatchBlocks()

        for block in blocks.flatten():
            if block=='minecraft:lava': 
                return 'lava'
            elif block=='minecraft:water':
                return 'water'
            elif block=='minecraft:cave_air':
                return 'cave'
            elif 'log' in block:
                return 'tree'
        return 'land'
