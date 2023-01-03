import numpy as np

from gdpc import geometry as GEO
from gdpc import interface as INTF
from gdpc import toolbox as TB
from gdpc import worldLoader as WL

from strabo.world import World
from strabo.agents.property import PropertyDeveloper
from strabo.agents.road import RoadDeveloper


def buildCity(world, *property_agents, road_agent, steps): 
    # Start by building a first property
    while(len(world.parcels)==0):
        property_agents[0].interact()
    # Build the start of the road
    for i in range(50):
        road_agent.runExplore() 

    start_point = (world.parcels[0].i, world.parcels[0].j)
    path = []
    while (len(path)==0): # Build at least one road
        dest_patch = np.random.choice(world.patches.flatten())
        end_point = (dest_patch.i, dest_patch.j)
        path = world.road_graph.findPath(start_point, end_point)
    world.registerRoad(path) 
    world.plotPatches()
    for i in range(steps):
        for agent in property_agents:
            agent.buildNew()
            #world.plotPatches()

        road_agent.interact()
        #world.plotPatches()
        

def commitToWorld(world):
    blocks = ['oak_planks', 'dark_oak_planks', 'acacia_planks']
    for patch in world.patches.flatten():
        if (patch.undeveloped == False):
            block = np.random.choice(blocks)
            x, z = patch.xz_coordinates.T
            y = patch.region_heights.flatten()
            for i, j, k in zip(x.flatten(), y.flatten(), z.flatten()):
                print(i, j, k)
                INTF.placeBlock(i, j-1, k, block)

        if (patch.type == "road"):
            block = 'obsidian'
            x, z = patch.xz_coordinates.T
            y = patch.region_heights.flatten()
            for i, j, k in zip(x.flatten(), y.flatten(), z.flatten()):
                print(i, j, k)
                INTF.placeBlock(i, j-1, k, block)


# Seleciona região ao redor do jogador
STARTX, STARTY, STARTZ, ENDX, ENDY, ENDZ = INTF.requestPlayerArea(200, 200)  # BUILDAREA

world = World(STARTX, STARTY, STARTZ, ENDX, ENDY, ENDZ, patch_size=5)
r_agent = PropertyDeveloper(world, "Vr")
c_agent = PropertyDeveloper(world, "Vc")
i_agent = PropertyDeveloper(world, "Vi")
road_agent = RoadDeveloper(world, explorers = 100)

buildCity(world, r_agent, c_agent, i_agent, road_agent=road_agent, steps=10)

world.plotPatches()

'''
road_agent = RoadDeveloper(world, explorers=30)
r_agent = PropertyDeveloper(world, "Vr")
c_agent = PropertyDeveloper(world, "Vc")
i_agent = PropertyDeveloper(world, "Vi")

buildCity(world, r_agent, c_agent, i_agent, road_agent, road_agent, steps=30)

world.plotPatches()
'''
x = input("commit? ")
if (x == 'y'):  
    commitToWorld(world)
