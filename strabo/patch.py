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

        self.dmarket = np.inf
        self.population = 0 # Total population
        self.e = self.y # Elevation
        self.dwater = np.inf # Distance from water
        self.dp = np.inf # Distance to primary roads
        self.eh = None # Elevation advantage
        self.ev = None # Variance in elevation (negative)
        self.epv = None # Variance in elevation (positive)
        self.dpr = None # Proximity to road
        self.dw = None # Proximity to water (score)
        self.dm = None # Proximity to market
        self.dr = None # Residential denisty
        self.dc = None # Comercial density
        self.di = None # Industrial density
        self.dpk = np.inf # Distance to park
        self.dcom = np.inf # Distance to commercial development

    # Euclidean distance to water source
    def get_dwater(self, patches):
        water_patches = [p for p in patches.flatten() if p.type == 'water']
        self.dwater  = min([patchDistances(self, water_source) for water_source in water_patches]+[np.inf])
        return self.dwater

    # Elevation advantage
    def get_eh(self, patches, e_offset=10):
        avg_e = np.mean([p.e for p in patches.flatten()])
        self.eh = np.exp((self.e - avg_e - e_offset)**2 / -128)
        return self.eh

    # Variance in elevation (negative and positive)
    def get_ev(self, patches):
        region = patches[max(0,self.i-VIEW_RADIUS):self.i+VIEW_RADIUS+1,
                         max(0, self.j-VIEW_RADIUS):self.j+VIEW_RADIUS+1]
        region_e = [p.e for p in np.array(region).flatten()]

        self.ev = np.exp( -np.var(region_e) )
        self.epv = np.var(region_e)
        return self.ev, self.epv

    # # Proximity to road
    def get_dpr(self):
        self.dpr = np.exp(-self.dp)
        return self.dpr

    # Proximity to water (score)
    def get_dw(self):
        self.dw = np.exp(-self.dwater)
        #self.dw = (1 + self.dwater)**-2
        return self.dw

    # Proximity to market (score)
    def get_dm(self, parcels):
        market_parcels = [p for p in parcels if p.development_type=='Vc']
        market_patches = []
        for parcel in market_parcels:
            market_patches += list(parcel.patches)
        self.dcom  = min([patchDistances(self, market) for market in market_patches]+[np.inf])

        self.dm = np.exp(-self.dcom)
        #self.dm = (1 + self.dmarket)**-2
        return self.dm

    # Proximity to park (score)
    def get_dpk(self, parcels):
        park_parcels = [p for p in parcels if p.development_type=='Vp']
        park_patches = []
        for parcel in park_parcels:
            park_patches += list(parcel.patches)
        dpark  = min([patchDistances(self, park) for park in park_patches]+[np.inf])

        self.dpk = np.exp(-park)
        return self.dpk
    
    # Residential denisty
    def get_dr(self, region_patches, region_parcels):
        res_patches = [p for p in region_parcels if p.development_type=='Vr']
        total_patches = [p for p in region_parcels] + region_patches

        self.dr = len(res_patches)/len(total_patches)
        return self.dr

    # Comercial density
    def get_dc(self, region_patches, region_parcels):
        com_patches = [p for p in region_parcels if p.development_type=='Vc']
        total_patches = [p for p in region_parcels] + region_patches

        self.dc = len(com_patches)/len(total_patches)
        return self.dc

    # Industrial density
    def get_di(self, region_patches, region_parcels):
        ind_patches = [p for p in region_parcels if p.development_type=='Vi']
        total_patches = [p for p in region_parcels] + region_patches

        self.di = len(ind_patches)/len(total_patches)
        return self.di


    # Makes this patch be part of a certain parcel
    def boundToParcel(self, parcel):
        self.parcel = parcel

    # Average height of blocks inside this patch
    def getAvgHeight(self):
        return np.mean(self.region_heights)

    # Return the block types in this patch
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

    # Sets the type of this patch depending on the blocks inside it
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
