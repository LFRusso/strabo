import numpy as np
from ..patch import Patch
from ..parcel import Parcel

class PropertyDeveloper:
    def __init__(self, world, agent_type, view_radius=5):
        self.world = world
        self.view_radius = view_radius
        self.position = np.random.choice(world.patches.flatten()) # Starts in a random patch of the map
        self.dev_sites = [] # TO DO: initialize dev_sites using starting position
        self.dev_patches = []
        self.last_commit = 5
        self.last_relocate = 5
        self.agent_type = agent_type

    def getRegion(self):
        i, j = [self.position.i, self.position.j] 
        region = self.world.patches[max(0,i-self.view_radius):i+self.view_radius+1,
                         max(0, j-self.view_radius):j+self.view_radius+1].flatten()
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
        region_patches, region_parcels = self.getRegion()
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

    def build(self, site):
        if (isinstance(site, Patch)): # Building in patch is direct
            new_parcel = self.world.createParcel(site, development_type=self.agent_type) # TO DO: expand to create parcels of multiple patches
            if (new_parcel == None): 
                return
            self.last_commit = 5 # Resets last commit counter
            self.world.updateWorld()
            
            '''
            # Removing current patch from the developable patches list
            if (site in self.dev_sites):
                self.dev_sites.remove(site)
            if (site in self.dev_patches):
                self.dev_patches.remove(site)
            # Preventing roads to be built on top of this patch
            self.world.addBlockedPatch(site)
            '''
            # Removing new parcel's patches from the list of free spaces
            for patch in new_parcel.patches:
                if (patch in self.dev_sites):
                    self.dev_sites.remove(patch)
                if (patch in self.dev_patches):
                    self.dev_patches.remove(patch)
                # Preventing roads to be built on top of this patch
                self.world.addBlockedPatch(patch)


        elif (isinstance(site, Parcel)): # Building in patcel requires check if it is worth replacing old parcel
             patch_values, parcel_values = self.world.getValues()
             current_value = parcel_values[site][site.development_type]
             new_value = parcel_values[site][self.agent_type]

             if (new_value / current_value > 1.2): # 20% at least increase in value
                site.development_type = self.agent_type
                self.last_commit = 5 # Resets last commit counter
                self.world.updateWorld()

    # Interacts with the environment
    def interact(self):
        self.dev_sites = self.prospect(self.dev_sites)
        self.build(self.position) # My version

        #for site in self.dev_sites: # Paper implementation
        #    self.build(site)

        # Decreases counters
        self.last_commit -= 1
        self.last_relocate -= 1

        print(f"Current position: {self.position.i}, {self.position.j}")