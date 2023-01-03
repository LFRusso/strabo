import numpy as np
from ..patch import Patch
from ..parcel import Parcel

class PropertyDeveloper:
    def __init__(self, world, agent_type, view_radius=5, memory=100):
        self.world = world
        self.view_radius = view_radius
        self.memory = memory
        self.position = np.random.choice(world.patches.flatten()) # Starts in a random patch of the map
        self.dev_sites = [] # TO DO: initialize dev_sites using starting position
        self.dev_patches = []
        self.considered_patches = []
        self.agent_type = agent_type

        # Weights for each type of developer
        ##        eh  ev  epv  dw   dr  di  dpk dpr dm   x
        self.W = {
            "r": [.1, .2,  0,  .1,  .4,  0,  0,  .2,  0,  0],
            "c": [ 0, .2,  0, .15, .15,  0,  0,  0, .4,  0],
            "i": [ 0, .5,  0,  .3,   0, .1,  0, .1,  0,  0],
            "p": [ 0,  0, .2,  .1,  .1,  0, .4,  0,  0, .2]
        }

    def getRegion(self, i, j):
        region = self.world.patches[max(1,i-self.view_radius):i+self.view_radius, # Adding padding of 1 patch
                         max(1, j-self.view_radius):j+self.view_radius].flatten()
        region = [p for p in region if p.developable] # Selecting only developable patches (excludes water, etc)

        region_parcels = []
        region_patches = []
        for patch in region:
            if (patch.parcel == None):
                region_patches.append(patch)
            elif ( patch.parcel not in region_parcels and patch.parcel.development_type != self.agent_type): # Excludes parcels of same development type as the agent (TO DO: provisory)
                region_parcels.append(patch.parcel)
    

        return region_patches, region_parcels


    # Searches for suitable locations in its surroundings
    def prospect(self, dev_sites):
        i, j = [self.position.i, self.position.j] 
        region_patches, region_parcels = self.getRegion(i, j)
        patch_values, parcel_values = [self.world.patch_values, self.world.parcel_values]
        values = patch_values | parcel_values
        combined_region = region_patches + region_parcels

        if (len(dev_sites)!=0 and (self.last_commit>0 or self.last_relocate>0)): # Move to a seen location
            combined_region = combined_region + dev_sites # Searching in union of region and memory
            region_values = [values[p][self.agent_type] for p in combined_region]
            next_location = combined_region[np.argmax(region_values)]
        else: # Relocate globlally
            self.last_relocate = 5 # Resets relocation counter

            # Selecting all empty patches from the world
            world_patches = [p for p in self.world.patches.flatten() if p.undeveloped and p.developable]
            world_parcels = [p for p in self.world.parcels if p.development_type != self.agent_type] # TO DO: check if conversion to agent_type is possible

            world_sites = world_patches + world_parcels
            sorted_idx = np.argsort([values[p][self.agent_type] for p in world_sites])[::-1]
            world_sites = np.array(world_sites)[sorted_idx]

            # Move to a random site in the top 5 best for the agent
            try:
                next_location = np.random.choice(world_sites[:5])
            except: # No more areas to develop
                return []
            self.dev_patches = []
        self.position = next_location

        #region_patches, region_parcels = self.getRegion() # NOTE: maybe have to be updated after relocation

        # TO DO / NOTE : Check this implementation better later

        dev_parcels = region_parcels
        
        
        dev_patches = []
        for patch in self.dev_patches + region_patches:
            if patch not in dev_patches and patch.undeveloped:
                dev_patches.append(patch)
        dev_patches_sorted_idx = np.argsort([values[p][self.agent_type] for p in dev_patches])[::-1]
        dev_patches = np.array(dev_patches)[dev_patches_sorted_idx] 
        self.dev_patches = list(dev_patches[:int(0.9*len(dev_patches))]) # Selecting only the 90% best patches

        dev_sites = list(dev_patches) + dev_parcels        
        return dev_sites

    # Returns True if as build successfully and False otherwise
    def build(self, site):
        if (isinstance(site, Patch)): # Building in patch is direct
            self.considered_patches.append(site)
            new_parcel = self.world.createParcel(site, development_type=self.agent_type) # TO DO: expand to create parcels of multiple patches
            if (new_parcel == None): 
                return False
            
            for patch in new_parcel.patches:
                # Preventing roads to be built on top of this patch
                self.world.addBlockedPatch(patch)

            return True
        return False

    def getScore(self, patch):
        i, j = [patch.i, patch.j] 
        region_patches, region_parcels = self.getRegion(i, j)

        eh = patch.get_eh(self.world.patches)
        ev, epv = patch.get_ev(self.world.patches)
        dpr = patch.get_dpr()
        dw = patch.get_dw()
        dr = patch.get_dr(region_patches, region_parcels)
        dc = patch.get_dc(region_patches, region_parcels)
        di = patch.get_di(region_patches, region_parcels)
        dm = patch.get_dm(self.world.parcels)
        dpk = patch.get_dm(self.world.parcels)

        A = [eh, ev, epv, dw, dr, di, dpk, dpr, dm, 0]
        W = [self.W['r'], self.W['i'], self.W['i'], self.W['p']]

        Vr, Vc, Vi, _= np.dot(W, A) 
        Vp = (1/Vr + 1/Vc + 1/Vi) * self.W['p'][-1] # Anti-worth

        return {'Vr': Vr, 'Vc': Vc, 'Vi': Vi, 'Vp': Vp}

    def prospectNew(self):
        i, j = [self.position.i, self.position.j] 
        region_patches, region_parcels = self.getRegion(i, j)

        avaliable_patches = self.dev_patches + region_patches # Memory + new
        avaliable_patches = [p for p in avaliable_patches if p not in self.considered_patches and self.world.isAccessible(p)]
        
        # No more avaliable patches, relocate globaly
        while len(avaliable_patches) == 0:
            self.position = np.random.choice(self.world.patches.flatten())
            i, j = [self.position.i, self.position.j] 
            region_patches, region_parcels = self.getRegion(i, j)
            avaliable_patches = [p for p in region_patches if p not in self.considered_patches and self.world.isAccessible(p)]

        scores = [self.getScore(patch)[self.agent_type] for patch in avaliable_patches]

        idx_best = np.argmax(scores)
        best_patch = avaliable_patches[idx_best]

        #print(f"Selected patch: ({best_patch.i}, {best_patch.j}), undeveloped={best_patch.undeveloped}")

        if (self.position == best_patch):
            self.build(self.position)
            print("Building")
        else:
            self.position = best_patch
            print("Relocating")

        return avaliable_patches

    def buildNew(self):
        avaliable_patches = [p for p in self.world.patches.flatten() if p.developable and p.undeveloped and p not in self.considered_patches]

        # Scoring all patches and sorting them by score
        scores = [self.getScore(p)[self.agent_type] for p in avaliable_patches]
        sorted_idx = np.argsort(scores)[::-1]
        sorted_patches = np.array(avaliable_patches)[sorted_idx]

        # Triyng to build in the best score avaliable
        built = False
        for patch in sorted_patches:
            # Checks if a patch is accessible
            if(self.build(patch)):
                break


    # Interacts with the environment
    def interact(self):
        self.dev_patches = self.prospectNew()
        self.dev_patches = self.dev_patches[:min(len(self.dev_patches), self.memory)]

        # Removing already developed patched from the list
        self.dev_patches = [p for p in self.dev_patches if p.developable]

        '''
        self.build(self.position) # My version

        #for site in self.dev_sites: # Paper implementation
        #    self.build(site)

        # Decreases counters
        self.last_commit -= 1
        self.last_relocate -= 1
        '''

        #print(f"Current position: {self.position.i}, {self.position.j}")