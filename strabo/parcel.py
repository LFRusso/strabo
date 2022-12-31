from gdpc import geometry as GEO
from gdpc import interface as INTF
from gdpc import toolbox as TB
from gdpc import worldLoader as WL

import cv2
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm

class Parcel:
    def __init__(self, *patches, expand_direction, development_type):
        self.patches = np.array(patches)
        self.development_type = development_type
        self.expand_direction = expand_direction # Used to define to what side the road must be attached to
        
        # Provisory implementation; used to determine agents movement to this parcel
        self.i = patches[0].i - expand_direction[0]
        self.j = patches[0].j - expand_direction[1]

        # Enforcing i and j in map bounds
        # TO DO: improve this later, not cheking upper border
        self.i = max(0, self.i)
        self.j = max(0, self.j)
