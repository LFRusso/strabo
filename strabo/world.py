from gdpc import worldLoader as WL

import cv2
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm

from .patch import Patch
from .parcel import Parcel
from .roadnet import RoadNet

class World:
    def __init__(self, STARTX, STARTY, STARTZ, ENDX, ENDY, ENDZ, patch_size=5):
        self.STARTX = STARTX
        self.STARTY = STARTY
        self.STARTZ = STARTZ 
        self.ENDX = ENDX 
        self.ENDY = ENDY 
        self.ENDZ = ENDZ 
        self.patch_size = patch_size
        self.ew = 63 # Default ocean elevation in Minecraft
        self.parcels = []
        self.roads = []
    
        self.WORLDSLICE = WL.WorldSlice(STARTX, STARTZ, ENDX + 1, ENDZ + 1)  
        self.HEIGHTMAP = self.WORLDSLICE.heightmaps['MOTION_BLOCKING_NO_LEAVES']

        self.width, self.height = len(self.HEIGHTMAP) // patch_size, len(self.HEIGHTMAP[0]) // self.patch_size 
        self.patches = self.getPatches()

        # Weights for each type of developer
        self.W = {
            "r": [.1, .2, 0, .3, .4, 0, 0, 0, 0, 0, 0],
            "c": [0, .2, 0, .15, .15, 0, 0, 0, .4, .1, 0],
            "i": [0, .5, 0, .3, 0, .1, 0, .1, 0, 0, 0],
            "p": [0, 0, .2, .1, .1, 0, .4, 0, 0, 0, .2]
        }

        self.undeveloped = True
        #self.patch_values, self.parcel_values = self.getValues() # Since this funcion is slow, store those values here (they have to be updated manually after avery development)

        ## Road network
        self.road_graph = RoadNet(self.patches)
        
        # Water and lava patches are impossible to pass in the road
        for patch in self.patches.flatten():
            if patch.type in ["water", "lava"]:
                self.road_graph.setBlocked((patch.i, patch.j))

    # Checks if it is possible to create a path from the road network to this patch
    def isAccessible(self, patch):
        # If there is not a road network yet, check if is accessible through other parcel
        if(len(self.roads) == 0  and len(self.parcels) == 0):
            return True 

        if (len(self.roads)!=0):
            # Selecting a random network patch
            start = np.random.choice(self.roads)

            start_point = (start.i, start.j)
            end_point = (patch.i, patch.j)

            path = self.road_graph.findPath(start_point, end_point)
            if (len(path)==0):
                return False
        else:
            start = np.random.choice(self.parcels)

            start_point = (start.i, start.j)
            end_point = (patch.i, patch.j)

            path = self.road_graph.findPath(start_point, end_point)
            if (len(path)==0):
                return False

        return True
        

    # Reads a list of blocks and converts intersected patches into roads
    def registerRoadBlocks(self, blocks):
        for patch in self.patches.flatten():
            x, z = patch.xz_coordinates.T
            patch_blocks = [(i, j) for i, j in zip(x.flatten(), z.flatten())]
            
            #print(not set(blocks).isdisjoint(patch_blocks))
            #continue
            if (not set(blocks).isdisjoint(patch_blocks)):
                patch.type = 'road'
                patch.developable = False
 
    # Sets patches as roads
    def registerRoad(self, path):
        for p in path:
            self.patches[p].type = 'road'
            if self.patches[p] not in self.roads:
                self.roads.append(self.patches[p])
            self.patches[p].developable = False

            # Updating dp for all developed patches
            for parcel in self.parcels:
                for patch in parcel.patches:
                    patch.dp = min(patch.dp, self.patch_size*sum([abs(u - v) for u, v in zip((patch.i, patch.j), p)]) )

    # Sets all blocks of a given patch as blocked in the road network 
    def addBlockedPatch(self, patch):
        self.road_graph.setBlocked((patch.i, patch.j))
        return

    def updateWorld(self):
        self.patch_values, self.parcel_values = self.getValues()

    # Divides land into patches for development
    def getPatches(self):
        # Truncate building area based on the patch size
        width, height = self.width, self.height

        patches = []
        for i in tqdm(range(0, width)):
            patches.append([])
            for j in range(0, height):
                # Getting heights
                patch_heights = self.HEIGHTMAP[i*self.patch_size:i*self.patch_size+self.patch_size, 
                                     j*self.patch_size:j*self.patch_size+self.patch_size]
                
                coords = np.transpose(np.mgrid[self.STARTX + i*self.patch_size:self.STARTX + i*self.patch_size+self.patch_size, 
                                                     self.STARTZ + j*self.patch_size:self.STARTZ + j*self.patch_size+self.patch_size])

                # Creating new patch of undeveloped land
                patch = Patch(i, j, patch_heights, self.patch_size, coords, self.WORLDSLICE)
                patches[i].append(patch)
        patches = np.array(patches)
        return patches

    # Utility function to normalize the individual parameters before calculating final value 
    def normalizeParameter(self, value, map_values):
        if (value == 0):
            return 0
        
        mean_value = np.mean(map_values)
        if (value == mean_value):
            norm_value = 1
        elif (value < mean_value):
            norm_value = np.exp2(1 - mean_value/value)
        else:
            norm_value = 2 - np.exp2(1 - value/mean_value)

        return norm_value

    # Calculates the values for each type of development for all patches
    def getValues(self):
        def getPartialValues(patch):
            flatten_patches = self.patches.flatten()

            eh_list = [p.eh for p in flatten_patches]
            ev_list = [p.ev for p in flatten_patches]
            epv_list = [p.epv for p in flatten_patches]
            dw_list = [p.dw for p in flatten_patches]
            dr_list = [p.dr for p in flatten_patches]
            di_list = [p.di for p in flatten_patches]
            dpk_list = [p.dpk for p in flatten_patches]
            dpr_list = [p.dpr for p in flatten_patches]
            dm_list = [p.dm for p in flatten_patches]
            dcom_list = [p.dcom for p in flatten_patches]

            eh = self.normalizeParameter(patch.eh, eh_list)      
            ev = self.normalizeParameter(patch.ev, ev_list)        
            epv = self.normalizeParameter(patch.epv, epv_list)        
            dw = self.normalizeParameter(patch.dw, dw_list)        
            dr = self.normalizeParameter(patch.dr, dr_list)   
            di = self.normalizeParameter(patch.di, di_list)     
            dpk = self.normalizeParameter(patch.dpk, dpk_list)  
            dpr = self.normalizeParameter(patch.dpr, dpr_list)        
            dm = self.normalizeParameter(patch.dm, dm_list)        
            dcom = self.normalizeParameter(patch.dcom, dcom_list)        
    
            ## Residential, Comercial and Industrial scores
            ## Park score can only be calculated partially due to the need of calculating the anti-worth

            A = [eh, ev, epv, dw, dr, di, dpk, dpr, dm, dcom, 0]
            W = [self.W['r'], self.W['i'], self.W['i'], self.W['p']]

            Vr, Vc, Vi, Vp_partial = np.dot(W, A) # TO DO: add constraints of eq. and table III
            return {'Vr': Vr, 'Vc': Vc, 'Vi': Vi, 'Vp': Vp_partial}


        partial_values = {}
        for patch in self.patches.flatten():
            partial_values[patch] = getPartialValues(patch)

        # Calculating normalized Anti-Worth for each patch
        for patch in self.patches.flatten():
            x_list = [1/V['Vr'] + 1/V['Vr'] + 1/V['Vi'] for V in partial_values.values()]
            
            V = partial_values[patch]
            x = 1/V['Vr'] + 1/V['Vr'] + 1/V['Vi']
            x = self.normalizeParameter(x, x_list)

            # Calculating final values by adding the contribution of Anti-Worth to the park value
            partial_values[patch]['Vp'] += self.W['p'][-1] * x
            

        # Calculating values for parcels
        patch_values = partial_values
        parcel_values = {}
        for parcel in self.parcels:
            parcel_values[parcel] = {'Vr': np.mean([patch_values[p]['Vr'] for p in parcel.patches]),
                                     'Vc': np.mean([patch_values[p]['Vc'] for p in parcel.patches]),
                                     'Vi': np.mean([patch_values[p]['Vi'] for p in parcel.patches]),
                                     'Vp': np.mean([patch_values[p]['Vp'] for p in parcel.patches])}

        return patch_values, parcel_values

    # Returns the distance of a patch the the network
    def getPatchNetworkDistance(self, patch):
        roads = [patch for patch in self.patches.flatten() if patch.type=="road"]
        dist = np.inf
        for net_patch in roads:
            dist = min(dist, self.patch_size*sum([abs(u - v) for u, v in zip((patch.i, patch.j), (net_patch.i, net_patch.j))]))
        
        patch.dp = dist
        return dist

    # Given a starting patch and a certain devleopment type, select some of its neighbours to make a new parcel
    def createParcel(self, initial_patch, development_type):
        B = 4 # Size of a block
        parcel_patches = [initial_patch] # Patches that will make up the new parcel
        print(f"Patch {(initial_patch.i, initial_patch.j)}, developable: {initial_patch.developable}, Type: {initial_patch.type}, Step: Initial")

        
        # Step 1: chooding a direction to expand away form the network
        possible_directions = [(0,1), (1, 0), (-1, 0), (0, -1)]
        expand_direction = None
        for direction in possible_directions:
            if ((direction[0] + initial_patch.i < 0) or (direction[0] + initial_patch.i >= self.width) or
               (direction[1] + initial_patch.j < 0) or (direction[1] + initial_patch.j >= self.height)): # Checking if is in bounds
               continue
            
            # Checking if next patch is going away from the road network as intended and has the other requirements
            next_patch = self.patches[direction[0] + initial_patch.i, direction[1] + initial_patch.j]
            if (next_patch.developable and (self.getPatchNetworkDistance(next_patch) > self.getPatchNetworkDistance(initial_patch)
                                            or self.getPatchNetworkDistance(initial_patch) == np.inf)):
                expand_direction = direction
                break # Next position chosen

        # Unable to expand the parcel
        # TO DO: try attaching to a neighboring parcel
        if(expand_direction==None):
            return
        
        # Step 2: expanding B/2 blocks in that direction
        for i in range(int(B/2)):
            last_patch = initial_patch
            next_patch = self.patches[expand_direction[0] + last_patch.i, expand_direction[1] + last_patch.j]
            if (not next_patch.developable):
                break
            print(f"Patch {(next_patch.i, next_patch.j)}, developable: {next_patch.developable}, Type: {next_patch.type}, Step: Expanding")
            parcel_patches.append(next_patch)
            last_patch = next_patch

        # Step 3: widening selected patch strip
        widening_patches = []
        wide_direction = expand_direction[::-1] # widening direction is perpendicular to the expand direction
        for patch in parcel_patches:
            if ((wide_direction[0] + patch.i < 0) or (wide_direction[0] + patch.i >= self.width) or
               (wide_direction[1] + patch.j < 0) or (wide_direction[1] + patch.j >= self.height)): # Checking if is in bounds
               continue

            next_patch = self.patches[wide_direction[0] + patch.i, wide_direction[1] + patch.j]
            if (next_patch.developable):
                print(f"Patch {(next_patch.i, next_patch.j)}, developable: {next_patch.developable}, Type: {next_patch.type}, Step: Widening")
                widening_patches.append(next_patch)

        parcel_patches += widening_patches

        # Check if patches dont already belong to an existing parcel
        for patch in parcel_patches:
            if patch.parcel != None:
                print("Trying to assign patch already used in another parcel.")
                return

        new_parcel = Parcel(*parcel_patches, expand_direction=expand_direction, development_type=development_type)
        for patch in parcel_patches:
            patch.parcel = new_parcel
            patch.undeveloped = False
            print(f"Setting ({patch.i}, {patch.j}) developed")
        self.parcels.append(new_parcel)

        return new_parcel

    def destroyParcel(self, parcel):
        for patch in parcel.patches:
            patch.parcel = None
            patch.undeveloped = True
            patch.type = 'land'
            self.road_graph.setUnblocked((patch.i, patch.j))
        self.parcels.remove(parcel)
        del parcel

    # Visualize map divided in patches
    def plotPatches(self, title=None):
        R,G,B = np.zeros([3, self.width, self.height], dtype=np.uint8)

        for i, x in enumerate(self.patches):
            for j, y in enumerate(x):
                if (y.type=='water'):
                    B[i,j] = 254
                elif (y.type=='lava'):
                    R[i,j] = 254
                elif (y.type=='land'):
                    G[i,j] = 254
                    B[i,j] = 100
                elif (y.type=='tree'):
                    G[i,j] = 254/2
                elif (y.type=='cave'):
                    G[i,j] = 100
                    B[i,j] = 100
                    R[i,j] = 100
                elif (y.type=='road'):
                    G[i,j] = 0
                    B[i,j] = 0
                    R[i,j] = 0
                else:
                    G[i,j] = 254
                    B[i,j] = 254
                    R[i,j] = 254

        for parcel in self.parcels: # Seeing parcels
            for patch in parcel.patches:
                if parcel.development_type == 'Vr': 
                    G[patch.i,patch.j] = 254
                    B[patch.i,patch.j] = 254
                    R[patch.i,patch.j] = 0

                elif parcel.development_type == 'Vc': 
                    G[patch.i,patch.j] = 254
                    B[patch.i,patch.j] = 0
                    R[patch.i,patch.j] = 254

                elif parcel.development_type == 'Vi': 
                    G[patch.i,patch.j] = 100
                    B[patch.i,patch.j] = 100
                    R[patch.i,patch.j] = 254

        RGB = np.array([R,G,B]).T

        plt.figure()
        if title:
            plt.title(title)
        plt.imshow(RGB)
        plt.show()
