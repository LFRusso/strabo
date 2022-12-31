import numpy as np

from gdpc import geometry as GEO
from gdpc import interface as INTF
from gdpc import toolbox as TB
from gdpc import worldLoader as WL

from strabo.world import World
from strabo.agents.property import PropertyDeveloper
from strabo.agents.road import RoadDeveloper


def buildCity(world, *agents, steps): 
    for i in range(steps):
        for agent in agents:
            agent.interact()

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
            block = 'cobblestone'
            x, z = patch.xz_coordinates.T
            y = patch.region_heights.flatten()
            for i, j, k in zip(x.flatten(), y.flatten(), z.flatten()):
                print(i, j, k)
                INTF.placeBlock(i, j-1, k, block)


# Seleciona região ao redor do jogador
STARTX, STARTY, STARTZ, ENDX, ENDY, ENDZ = INTF.requestPlayerArea(100, 100)  # BUILDAREA

world = World(STARTX, STARTY, STARTZ, ENDX, ENDY, ENDZ, patch_size=5)

road_agent = RoadDeveloper(world, explorers=30)
r_agent = PropertyDeveloper(world, "Vr")
c_agent = PropertyDeveloper(world, "Vc")
i_agent = PropertyDeveloper(world, "Vi")

buildCity(world, r_agent, c_agent, i_agent, road_agent, road_agent, steps=30)

world.plotPatches()

x = input("commit? ")
if (x == 'y'):  
    commitToWorld(world)