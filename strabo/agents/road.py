import numpy as np

class RoadDeveloper:
    def __init__(self, world, explorers = 20):
        self.world = world
        self.explorers = explorers

    # Gets the path between two patches using the road graph
    def getPath(self, patch1, patch2):
        return

    # Explore the map using the current network and paths
    def runExplore(self):
        # Select interest points to explore
        try: 
            # Selecting Origin parcel
            start = np.random.choice([p for p in self.world.parcels])
            
            # Selecting destination parcel
            destination = np.random.choice([p for p in self.world.parcels])
        except: # Only proceed if those properties have already been developed
            return []

        start_point = (start.i, start.j)
        end_point = (destination.i, destination.j)

        path = self.world.road_graph.findPath(start_point, end_point)
        return path


    # Runs an simulation tick with the world
    def interact(self):
        for i in range(self.explorers):
            path = self.runExplore()

        # Implementation 1: build through all pairs
        ## Problema: tempo de execução
        '''
        # Runnig exploration routine for each pair of developed parcel
        for start_parcel in self.world.parcels:
            for destination_parcel in self.world.parcels:
                start_point = (start_parcel.i, start_parcel.j)
                end_point = (destination_parcel.i, destination_parcel.j)

                path = self.world.road_graph.findPath(start_point, end_point)
                path = path[1:-1] # Start and destination are not converted into roads
                self.world.road_graph.setRoad(path)
                self.world.registerRoad(path)
        # Cleaning alterations in the map due to previous explorations
        self.world.road_graph.clearEdges()
        '''

        # Implementation 2: making road using only one random pair
        ## Problem: road network doesnt reach some places
        '''
        path = self.runExplore()
        path = path[1:-1] # Start and destination are not converted into roads
        self.world.road_graph.setRoad(path)
        self.world.registerRoad(path)
        # Cleaning alterations in the map due to previous explorations
        self.world.road_graph.clearEdges()
        '''

        # Implementation 3: choose start randomly and destination as the block further from the network
        ## Problem: same with 2
        '''
        least_acessible_parcel = self.world.parcels[0]
        for parcel in self.world.parcels:
            if min([p.dp for p in least_acessible_parcel.patches]) < min([p.dp for p in parcel.patches]):
                least_acessible_parcel = parcel
        
        destination_parcel = np.random.choice([p for p in self.world.parcels])

        start_point = (least_acessible_parcel.i, least_acessible_parcel.j)
        end_point = (destination_parcel.i, destination_parcel.j)

        path = self.world.road_graph.findPath(start_point, end_point)
        path = path[1:-1] # Start and destination are not converted into roads
        self.world.road_graph.setRoad(path)
        self.world.registerRoad(path)
        
        # Cleaning alterations in the map due to previous explorations
        self.world.road_graph.clearEdges()
        '''

        # Implementation 4: Make road reach all parcels away from the network
        '''
        inaccessible_parcels  = [parcel for parcel in self.world.parcels if min([patch.dp for patch in parcel.patches]) > self.world.patch_size]
        
        try: # Trying to select an accessible parcel
            destination_parcel = np.random.choice([p for p in self.world.parcels if p not in inaccessible_parcels])
        except: # If impossible (all parcels are not accessible), select ramdom
            try:
                destination_parcel = np.random.choice([p for p in self.world.parcels])
            except:
                return

        #print("construido")
        for start_parcel in inaccessible_parcels:
            start_point = (start_parcel.i, start_parcel.j)
            end_point = (destination_parcel.i, destination_parcel.j)

            path = self.world.road_graph.findPath(start_point, end_point)
            path = path # Start and destination are not converted into roads
            self.world.road_graph.setRoad(path)
            self.world.registerRoad(path)
            #self.world.plotPatches()
        # Cleaning alterations in the map due to previous explorations
        self.world.road_graph.clearEdges()
        '''

        # Implementation 5: go to all inaccessible parcels, starting from random points in the network
        if (len(self.world.parcels) < 2):
            return
        
        road_coords = [(p.i, p.j) for p in self.world.roads]
        inaccessible_parcels = [parcel for parcel in self.world.parcels if (parcel.i, parcel.j) not in road_coords]
        if (len(inaccessible_parcels)==0): # If no inaccessible parcels, return
            return

        if (len(self.world.roads) == 0): # If no roads created yet select start randomly
            start_parcel = np.random.choice(self.world.parcels) 
            destination_parcel = np.random.choice(inaccessible_parcels) # TO DO: correct this, possible to not accessible parcel

            start_point = (start_parcel.i, start_parcel.j)
            end_point = (destination_parcel.i, destination_parcel.j)

            path = self.world.road_graph.findPath(start_point, end_point)
            path = path # Start and destination are not converted into roads
            self.world.road_graph.setRoad(path)
            self.world.registerRoad(path)


        # Build all the reast connecting to the network
        for destination_parcel in inaccessible_parcels:
            start_parcel = np.random.choice(self.world.roads)

            start_point = (start_parcel.i, start_parcel.j)
            end_point = (destination_parcel.i, destination_parcel.j)

            path = self.world.road_graph.findPath(start_point, end_point)
            path = path # Start and destination are not converted into roads
            self.world.road_graph.setRoad(path)
            self.world.registerRoad(path)

        # If there is still an inaccessilble parcel, destroy it
        road_coords = [(p.i, p.j) for p in self.world.roads]
        inaccessible_parcels = [parcel for parcel in inaccessible_parcels if (parcel.i, parcel.j) not in road_coords]
        for parcel in inaccessible_parcels:
            self.world.destroyParcel(parcel)
            print("destroying")

        self.world.road_graph.clearEdges()