import numpy as np

class RoadNet:
    def __init__(self, patches):
        self.patches = patches
        self.X = [i for i in range(len(patches))]
        self.Y = [[patch.y for patch in patch_line] for patch_line in patches] # Average height of the patch
        self.Z = [j for j in range(len(patches[0]))]

        self.blocked = []
        self.edges = {}
        self.roads = []

        # An easier way of getting the heighs for later 
        self.heights = {}
        for i in range(len(self.X)):
            for j in range(len(self.Z)):
                self.heights[(self.X[i], self.Z[j])] = self.Y[i][j]

    
    def addEdge(self, node1, node2):
        self.edges[(node1, node2)] = 0 # Default weight is 0
        self.edges[(node2, node1)] = 0
        # TO DO: add check nodes belong to the region
    
    def setBlocked(self, patch):
        if patch not in self.blocked:
            self.blocked.append(patch)

    def setUnblocked(self, patch):
        if patch in self.blocked:
            self.blocked.remove(patch)

    def getBlocks(self):
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

    # A* implementation using patches as nodes instead of blocks
    def findPathAStar(self, start, dest):
        def getChildren(node, visited, possible_nexts, dest): # Returns nodes accessible from current position
            current_position = node.position
            possible_steps = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            children  = []
            for step in possible_steps:
                next_position = (current_position[0] + step[0], current_position[1] + step[1])

                # 1. Check if next_position belongs to the map
                if next_position not in self.heights.keys():
                    continue
                next_patch = self.patches[next_position] # Retrieving next patch

                # 2. Check if next_position not in blocked blocks
                if next_position in self.blocked:
                    continue

                # 3. Avoid too steep patches (moutains, caves...)
                if abs(next_patch.max_y- next_patch.min_y) > next_patch.size - 1:
                    continue

                # 4. Check if not visited
                if next_position in visited:
                    continue

                # 4. Check if not already in the open_list
                if next_position in possible_nexts:
                    continue

                # All checked, can add to children
                children.append(Node(next_position, node))
            return children

        start_node = Node(start, None)
        start_node.g = start_node.h = start_node.f = 0

        end_node = Node(dest, None)
        end_node.g = end_node.h = end_node.f = 0

        visited_nodes = []
        open_list = [start_node]

        while(len(open_list) != 0):
            # Getting next node
            current_node = open_list[0]
            current_index =  0
            for index, node in enumerate(open_list):
                if node.f < current_node.f:
                    current_node = node
                    current_index = index

            # Popping from list to be visited
            open_list.pop(current_index)
            visited_nodes.append(current_node.position)

            # Reached destination! Retrieve path
            if current_node.position == end_node.position:
                path = []
                node = current_node
                while node != None:
                    path.append(node.position)
                    node = node.parent
                return path[::-1]

            # Retrieve children
            children = getChildren(current_node, visited_nodes, [node.position for node in open_list], dest)
            
            # Calculating values for the children
            for child in children:

                dx = abs(current_node.position[0] - child.position[0])
                dz = abs(current_node.position[1] - child.position[1])
                dy = abs(self.heights[(current_node.position)] - self.heights[(child.position)]) # TO DO: Continua assim

                dist = dx + dy + dz # Distance between current and children
                if ((current_node.position, child.position) in self.edges.keys()):
                    edge_speed_bonus = self.edges[(current_node.position, child.position)]
                else:
                    edge_speed_bonus = 0
                #if (edge_speed_bonus >= 1):
                #    print(edge_speed_bonus)
                child.g = current_node.g + dist/(1 + edge_speed_bonus)  # Distance between start and children

                # Heuristic: Euclidean // Manhattan 
                child_xyz = [*child.position, self.heights[child.position]]
                goal_xyz = [*end_node.position, self.heights[end_node.position]]
                child.h = sum([abs(u - v) for u, v in zip(child_xyz, goal_xyz)])
                #child.h = np.linalg.norm(np.array(child_xyz) - np.array(goal_xyz))
                
                # Final score
                child.f = child.g + child.h

                for node in open_list:
                    if (child == node) and (child.g > node.g):
                        continue
                
                # Add child to open_list
                open_list.append(child)
        return [] # not reached
        

    # If an edge is used, the travel speed within it is increased
    def setEdgeUse(self, edge):
        if (edge in self.roads): # Roads do not receive any bonus
            return

        if (edge not in self.edges.keys()):
            self.addEdge(*edge)
        
        self.edges[edge] += 0.5 # Increase travel speed by 0.5 m/s
        self.edges[edge[::-1]] += 0.5 # Same for the other direction (undirected graph)

    # If an edge is unused, it deteriorates and bonus speed is reduced
    def setEdgeUnused(self, edge):
        if (edge in self.roads): # Roads do not deteriorate
            return

        if (edge not in self.edges.keys()):
            self.addEdge(*edge)
        
        self.edges[edge] -= 0.1 # Decrease travel speed by 0.1 m/s
        self.edges[edge[::-1]] -= 0.1 # Same for the other direction (undirected graph)

        self.edges[edge] = max(self.edges[edge], 0)
        self.edges[edge[::-1]] = max(self.edges[edge[::-1]], 0)

    # Register the development of a new road
    def setRoad(self, path):
        for i in range(len(path)-1):
            edge = (path[i], path[i+1])
            if (edge not in self.edges.keys()):
                self.addEdge(*edge)
            
            self.edges[edge] = 9999 # Increase travel speed to 5 m/s
            self.edges[edge[::-1]] = 9999 # Same for the other direction (undirected graph)

            self.roads.append(edge)
            self.roads.append(edge[::-1])
        return

    # Clears edges bonus, keeping only those associated with roads
    def clearEdges(self):
        self.edges = {}

        for edge in self.roads:
            self.edges[edge] = 9999

    # Finds the path between two blocks, marking the edges found by increasing their speed 
    def findPath(self, start, dest):
        path = self.findPathAStar(start, dest)

        # Increases the travel speed in the edges of the path used
        used_edges = []
        for i in range(len(path)-1):
            edge = (path[i], path[i+1])
            self.setEdgeUse(edge)
            used_edges.append(edge)

        for edge in self.edges.keys():
            if not (edge in used_edges or edge[::-1] in used_edges):
                self.setEdgeUnused(edge)

        return path


class Node:
    def __init__(self, position, parent):
        self.position = position
        self.parent = parent

        self.f = 0
        self.h = 0
        self.g = 0