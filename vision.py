# Code for filtering non-visible blocks based on a given observation and small tests

import MalmoPython
import numpy as np

from util import *

################################################################################
# Configuration for observation cube and vision handling
################################################################################

CUBE_OBS = "cube10"  # Name that will be used in XML/JSON
CUBE_SIZE = 2  # Size in 1 direction
FOV = 70  # Default Field of View for Minecraft

# This is a list of all transparant blocks that the agent can see through.
TRANSPARANT_BLOCKS = ["glass", "air", "sapling", "cobweb", "flower", "mushroom",
                      "torch", "ladder", "fence", "iron_bars", "glass_pane", "vines", "lily_pad",
                      "sign", "item_frame", "flower_pot", "skull", "armor_stand", "banner", "tall_grass",
                      "lever", "pressure_plate", "redstone_torch", "button", "trapdoor", "tripwire",
                      "tripwire_hook", "redstone", "rail", "beacon", "cauldron", "brewing_stand"]

BLOCK_WOOD = "log"


################################################################################
# Main Vision handling class
################################################################################

class VisionHandler(object):
    """
    Class for handling vision through the use of observation cubes, cube size
    is in 1 direction. Use this class to help the agent "see".
    """

    def __init__(self, size):
        super(VisionHandler, self).__init__()
        self.size = size

        # Since real cube size is for both directions, we also do +1 for player
        self.realSize = size * 2 + 1
        self.numElements = self.realSize ** 3
        self.center = size
        self.matrix = np.zeros((self.realSize, self.realSize, self.realSize),
                               dtype="|S25")

        self.__setupVisibilityMatrix()
        self.__setupVisibleBlockList()

    def __repr__(self):
        return "{}".format(self.matrix)

    def updateFromObservation(self, cubeObservation):
        """
        Converts the 1D list of blocks into our 3D matrix. Don't forget to call
        filterOccluded() afterwards!
        """

        # Sanity check, just in case
        if len(cubeObservation) != self.numElements:
            raise ValueError("cube observation uses different cube size!")

        # Directly copy over the list to a numpy matrix, reset the shape, and
        # swap the y and z axes (previous index / Malmo uses x, z, y)
        # 25 characters should be enough for block names...
        temp = np.array(cubeObservation, dtype="|S25")
        temp = np.reshape(temp, (self.realSize, self.realSize, self.realSize))
        self.matrix = np.swapaxes(temp, 1, 2)

    def areValidRelCoords(self, relX, relY, relZ):
        """ Returns True/False if the given relative coords are valid. """
        if relX < -self.size or relX > self.size:
            return False

        if relY < -self.size or relY > self.size:
            return False

        if relZ < -self.size or relZ > self.size:
            return False

        return True

    def getBlockAtRelPos(self, relX, relY, relZ):
        """
        Returns the block at the given x, y, z position relative to the player.
        Returns empty string if -size > x, y, z or x, y, z > size (out of bounds).
        This also corresponds to "we don't know whats there".
        """
        if self.areValidRelCoords(relX, relY, relZ):
            return self.matrix[self.center + relY, self.center + relX, self.center + relZ]
        else:
            return ""

    def isBlock(self, relX, relY, relZ, blockName):
        """ Returns True/False if the given block is at the given relative position. """
        # print "isBlock: {} {} {}: {}".format(relX, relY, relZ,
        # 	self.getBlockAtRelPos(relX, relY, relZ))
        return self.getBlockAtRelPos(relX, relY, relZ) == blockName

    def findBlocks(self, blockName):
        """
        Returns a list of [x, y, z] coordinates as a list of numpy arrays, where
        the given block is. An empty list is returned if the block cant be found.
        """
        coordinates = []

        for block in self.visibleBlocks:
            x, y, z = block.getXYZ()

            if self.isBlock(x, y, z, blockName):
                coordinates.append(np.array([x, y, z]))

        return coordinates

    def findWood(self):
        """ See findBlocks function, returns coordinates of wood/log. """
        return self.findBlocks(BLOCK_WOOD)

    def getWalkableBlocks(self):
        """ Returns a list of all [x, y, z] blocks that the player can stand on. """

        walkableBlocks = []

        for block in self.visibleBlocks:
            x, y, z = block.getXYZ()

            if self.isBlock(x, y, z, "air") and self.isBlock(x, y + 1, z, "air"):
                walkableBlocks.append(np.array([x, y, z]))

        return walkableBlocks

    def __setupVisibilityMatrix(self):
        self.visible = np.zeros((self.realSize, self.realSize, self.realSize), dtype=bool)

    def __fixDefaultVisibility(self):
        """ We can always "see" the 2 blocks where the player is standing """
        self.visible[self.center, self.center, self.center] = True
        self.visible[self.center + 1, self.center, self.center] = True

    def isVisible(self, relX, relY, relZ):
        """ Returns True/False if the given relative x, y, z block is visible. """
        return self.visible[self.center + relY, self.center + relX, self.center + relZ]

    def setVisible(self, relX, relY, relZ):
        """ Sets the given relative x, y, z block to visible """
        self.visible[self.center + relY, self.center + relX, self.center + relZ] = True

    def setInvisible(self, relX, relY, relZ):
        """ Sets the block at relative x, y, z coordinates to empty string. """
        self.visible[self.center + relY, self.center + relX, self.center + relZ] = False

    def applyVisibility(self):
        """ Applies the visiblity matrix to the observation matrix. """
        for x in range(-self.size, self.size + 1):
            for y in range(-self.size, self.size + 1):
                for z in range(-self.size, self.size + 1):
                    if not self.isVisible(x, y, z):
                        self.matrix[self.center + y, self.center + x, self.center + z] = ""

        self.updateVisibleBlockList()

    def __setupVisibleBlockList(self):
        """
        Used to setup the list of visible blocks that can be used by FOV
        filtering and raytracing.
        """

        self.visibleBlocks = []

    def addVisibleBlock(self, block):
        self.visibleBlocks.append(block)

    def updateVisibleBlockList(self):
        """ Updates the list of visible blocks """
        self.__setupVisibleBlockList()

        for x in range(-self.size, self.size + 1):
            for y in range(-self.size, self.size + 1):
                for z in range(-self.size, self.size + 1):
                    if self.isVisible(x, y, z):
                        self.addVisibleBlock(Block(x, y, z))

    def __filterCoarse(self):
        """
        Determines the visibility matrix by doing a fast, coarse filtering of
        non-visible blocks, by looking at transparant blocks around the player
        and expanding outwards. This is a helper function and shouldnt be used
        directly outside this class. Ensure the self.visible matrix is available
        and initialized properly (aka, everything to False)...
        """

        # First we filter out all blocks that are not adjacent to a transparant
        # block, since they will not be visible anyway. We do this by starting
        # from the players eyes, and gradually marking visible/unvisible blocks
        # outwards.

        # The blocks where the player is standing is always visible of course...
        # Unless we are suffocating... in which case we're fucked...
        # Future TODO: Figure something out or not, I dont care
        if self.getBlockAtRelPos(0, 0, 0) not in TRANSPARANT_BLOCKS and \
                        self.getBlockAtRelPos(0, 1, 0) not in TRANSPARANT_BLOCKS:

            # Yup, we're suffocating... FUCK FUCK FUCK
            for i in range(42):
                print "I CAN'T BREEEAATTHEEE!! HELP ME I'M FUCKING SUFFOCATING!!!"

        self.__fixDefaultVisibility()

        # We basically expand our search for visible blocks outward from where
        # the player is standing, and check adjacant blocks to see if they are
        # visible.
        # There are edge cases in which a block is not marked visible because
        # none of its neighbors have been marked as such, but they are in fact
        # potentially visible since its neighbors will be marked visible later
        # on. We can either fix this by doing multiple passes (easy), or by
        # changing the loops to work in an actual, outwards spiral (harder)...
        # Future TODO: Improve upon multiple passes method with something smarter
        iterations = 0

        while True:
            changedSomething = False

            for x in range(0, self.size + 1) + range(-1, -self.size - 1, -1):
                for y in range(0, self.size + 1) + range(-1, -self.size - 1, -1):
                    for z in range(0, self.size + 1) + range(-1, -self.size - 1, -1):

                        # If this block is already visible, skip it
                        if self.isVisible(x, y, z):
                            continue

                        # Check 6 surrounding blocks if they're visible, first
                        # we check left and right blocks (x direction)
                        if x + 1 < self.size and self.isVisible(x + 1, y, z) and \
                                        self.getBlockAtRelPos(x + 1, y, z) in TRANSPARANT_BLOCKS:
                            self.setVisible(x, y, z)
                            changedSomething = True
                            continue

                        if x - 1 > -self.size and self.isVisible(x - 1, y, z) and \
                                        self.getBlockAtRelPos(x - 1, y, z) in TRANSPARANT_BLOCKS:
                            self.setVisible(x, y, z)
                            changedSomething = True
                            continue

                        # Then we check above and below blocks (y direction)
                        if y + 1 < self.size and self.isVisible(x, y + 1, z) and \
                                        self.getBlockAtRelPos(x, y + 1, z) in TRANSPARANT_BLOCKS:
                            self.setVisible(x, y, z)
                            changedSomething = True
                            continue

                        if y - 1 > -self.size and self.isVisible(x, y - 1, z) and \
                                        self.getBlockAtRelPos(x, y - 1, z) in TRANSPARANT_BLOCKS:
                            self.setVisible(x, y, z)
                            changedSomething = True
                            continue

                        # And finally check front and back blocks (z direction)
                        if z + 1 < self.size and self.isVisible(x, y, z + 1) and \
                                        self.getBlockAtRelPos(x, y, z + 1) in TRANSPARANT_BLOCKS:
                            self.setVisible(x, y, z)
                            changedSomething = True
                            continue

                        if z - 1 > -self.size and self.isVisible(x, y, z - 1) and \
                                        self.getBlockAtRelPos(x, y, z - 1) in TRANSPARANT_BLOCKS:
                            self.setVisible(x, y, z)
                            changedSomething = True
                            continue

                        # If no nieighbors are visible, this block is likely not
                        # visible either.
                        self.setInvisible(x, y, z)

            iterations += 1

            if not changedSomething:
                break

    def __filterFOV(self, lookAt):
        """ Filters out all non-visible blocks that the agent cannot see """

        # Convert all currently visible blocks to blocks of triangles. Also, we
        # do a simple angle test with blocks that are absolutely out of view

        # TODO: Fix fov calculation into correct one that minecraft uses...
        fov = radians(FOV)

        # print "lookAt = {}, fov = {}\n".format(lookAt, fov)
        print "coarse filtered matrix = \n{}".format(self.matrix)

        for block in self.visibleBlocks:
            x, y, z = block.getXYZ()

            # Skip all non-visible blocks
            if self.isVisible(x, y, z):
                # Check dot product visibility for visible blocks, aka
                # angle test for every corner of the block. If one of
                # the corners is visible, then the block is considered
                # visible as well.
                cornerVisible = False
                corners = block.getCorners()

                for i in range(len(corners)):
                    cornerDir = getNormalizedVector(corners[i])
                    angle = acos(np.dot(cornerDir, lookAt))
                    # print "corner {}, angle = {}".format(i, angle)

                    if angle >= -fov and angle <= fov:
                        cornerVisible = True
                        # print "\tblock is visible!"
                        break

                if not cornerVisible:
                    # print "\t block is NOT visible!"
                    self.setInvisible(x, y, z)

        self.__fixDefaultVisibility()

    def _filterRayTraced(self, lookAt, playerIsCrouching=False):
        """
        Filters occluded blocks by using ray-tracing of the visible blocks...
        TODO: FINISH THIS AND FIX IT
        """

        # Now we can ray-trace all the blocks... First, we setup a 2D grid of
        # rays that we will shoot from the players eyes...
        numX = 160
        numY = 90
        distance = 0.1

        # Calculate some FOV bullshit
        aspectRatio = numX * 1.0 / numY
        fov = radians(FOV) / 2.0
        ratioFov = tan(fov)

        # Get the origin of the camera (aka the eyes)
        origin = np.array([0, PLAYER_EYES_CROUCHING if playerIsCrouching else PLAYER_EYES, 0])

        # Get left and up directions of the image plane
        left = getNormalizedVector(np.cross(lookAt + np.array([0, 0.1, 0]), lookAt))
        up = getNormalizedVector(np.cross(lookAt, left))
        left = getNormalizedVector(np.cross(up, lookAt))

        # Get corners of the view plane and plane vectors
        center = origin + lookAt * distance
        p0 = center - left + up
        p1 = center + left + up
        p2 = center - left - up
        right = p1 - p0
        up = p2 - p0

        # Make a copy of the visiblity matrix, since we need our own
        visibleBackup = np.copy(self.visible)

        # The visibility matrix is reset because we only mark the visible blocks
        # as visible, and dont filter out visible blocks
        self.__setupVisibilityMatrix()

        # Generate all the rays and trace them
        for y in range(numY):
            # Make sure vStep is in the range [-1.0, 1.0]
            vStep = y * 2.0 / numY - 1.0

            for x in range(numX):
                # Make sure uStep is also in the same range
                uStep = x * 2.0 / numX - 1.0

                # Calculate ray direction vector based on x and y coords
                rayDirection = lookAt + right * ratioFov * aspectRatio * uStep + \
                               up * ratioFov * vStep
                ray = Ray(origin, getNormalizedVector(rayDirection))

                # Trace new ray for intersection, test against all visible blocks...
                intersectedBlocks = []
                intersectedBlockTypes = []
                intersectionT = []

                for block in self.visibleBlocks:
                    # Don't do early out, since we need the closest t for sorting...
                    t = block.intersect(ray, False)

                    if t is not None:
                        intersectedBlocks.append(block)
                        x, y, z = block.getXYZ()
                        intersectedBlockTypes.append(self.getBlockAtRelPos(x, y, z))
                        intersectionT.append(t)

                # Check if this ray hit anything and update visibility
                if intersectedBlocks != []:
                    # Now we need to order the intersected blocks based on their
                    # intersected t values, so we can clip non-visible blocks...
                    order = np.array(intersectionT).argsort()
                    orderedBlocks = np.array(intersectedBlocks)[order]
                    orderedTypes = np.array(intersectedBlockTypes)[order]

                    hitNonTransparantBlock = False

                    # We can only see transparant blocks until we hit the first
                    # non-transparant block, all the others are likely occluded
                    # for this pixel
                    for block, blockType in zip(orderedBlocks, orderedTypes):
                        x, y, z = block.getXYZ()

                        if blockType in TRANSPARANT_BLOCKS:
                            if not hitNonTransparantBlock:
                                self.setVisible(x, y, z)
                        else:
                            if not hitNonTransparantBlock:
                                hitNonTransparantBlock = True
                                self.setVisible(x, y, z)

                            # We can stop now since no other blocks will be
                            # marked as visible
                            break

        self.__fixDefaultVisibility()

    def filterOccluded(self, lookAt, playerIsCrouching=False):
        """ Filters out all occluded blocks that the agent cannot see. """

        lookAt = getNormalizedVector(lookAt)

        # First we setup the visibility matrix, and do coarse filtering
        self.__setupVisibilityMatrix()
        self.__setupVisibleBlockList()  # Used for __filterFOV and _filterRayTraced
        self.__filterCoarse()
        self.applyVisibility()

        # Then we do more advanced filtering based on the FOV of the player
        # oldVisible = np.copy(self.visible)
        # self.__filterFOV(lookAt)
        # difference = (oldVisible != self.visible)
        # print "filterFOV changed something = {}".format(difference.any())
        # self.applyVisibility()

        # Finally, we can do ray-tracing to determine occluded blocks...
        # oldVisible = np.copy(self.visible)
        # self._filterRayTraced(lookAt, playerIsCrouching)
        # difference = (oldVisible != self.visible)
        # print "filterRayTraced changed something = {}".format(difference.any())
        # self.applyVisibility()

        # print self.matrix


################################################################################
# Classes for raytracing, includes Ray, Triangle and Block class
################################################################################

class Ray(object):
    """
    Helper class to handle Rays that are used for ray-tracing with minecraft
    blocks, to perform realistic visibility tests.
    """

    # Some constants to use for ray-tracing
    MAX_T = 1e34
    EPSILON_T = 0.0001

    def __init__(self, origin, direction):
        """
        Origin and direction should be 3D numpy vectors, and direction must be
        normalized.
        """
        super(Ray, self).__init__()
        self.origin = origin
        self.direction = direction

    def getOrigin(self):
        return self.origin

    def getDirection(self):
        return self.direction

    def getPosition(self, t):
        """ Returns the position of the ray for the given t value. """
        return self.origin + t * self.direction


class Triangle(object):
    """
    Helper class to handle Triangles that are used for ray-tracing with minecraft
    blocks, to perform realistic visibility tests.
    """
    INTERSECTION_EPSILON = 0.000001

    def __init__(self, normal, vertices):
        """
        Please use 3D numpy vectors for every vector. Note that vertices should
        be a list or numpy array of three, 3D numpy vectors, and normal must be
        a normalized vector.
        """
        super(Triangle, self).__init__()
        self.normal = normal
        self.vertices = np.copy(vertices)
        self.edge1 = vertices[1] - vertices[0]
        self.edge2 = vertices[2] - vertices[0]

    def intersect(self, ray):
        """
        Checks if the given ray intersects this triangle, and if so, returns the
        corresponding t value. If not, None is returned.
        """

        # Calculate if the ray can actually intersect the triangle (dot product)
        p = np.cross(ray.getDirection(), self.edge2)
        det = np.dot(self.edge1, p)

        if det > -Triangle.INTERSECTION_EPSILON and det < Triangle.INTERSECTION_EPSILON:
            return None

        # Possible intersection, calculate bary-centric coordinates
        inverseDet = 1.0 / det
        temp = ray.getOrigin() - self.vertices[0]
        u = np.dot(temp, p) * inverseDet

        if u < 0.0 or u > 1.0:
            return None

        q = np.cross(temp, self.edge1)
        v = np.dot(ray.getDirection(), q) * inverseDet

        if v < 0.0 or u + v > 1.0:
            return None

        # Calculate t value since we have a valid intersection
        t = np.dot(self.edge2, q) * inverseDet
        return t


class Block(object):
    """
    Helper class to handle Blocks that are used for ray-tracing with minecraft
    blocks, to perform realistic visibility tests.
    """

    def __init__(self, relX, relY, relZ):
        """
        Initializes the block with the relative x, y, z coordinates to the
        player, and constructs 6 triangles for the 3 closest perpendicular faces.
        """
        self.x = relX
        self.y = relY
        self.z = relZ

        # Get all corners of this block, labeled clockwise...
        self.corners = [
            np.array([relX + 1, relY + 1, relZ], dtype=float),  # "Top" corners
            np.array([relX + 1, relY + 1, relZ + 1], dtype=float),
            np.array([relX, relY + 1, relZ + 1], dtype=float),
            np.array([relX, relY + 1, relZ], dtype=float),

            np.array([relX + 1, relY, relZ], dtype=float),  # "Bottom" corners
            np.array([relX + 1, relY, relZ + 1], dtype=float),
            np.array([relX, relY, relZ + 1], dtype=float),
            np.array([relX, relY, relZ], dtype=float),
        ]

        # TODO: Double check normals/vertices again... (seem ok now...) (check again)
        # Get closest and furthest face orthogonal to x direction in z, y plane
        normalX1 = getNormalizedVector(np.array([-relX, relY, relZ]))
        normalX2 = getNormalizedVector(np.array([relX, relY, relZ]))

        # Create 4 triangles for those 2 faces
        faceX11 = Triangle(normalX1, [self.corners[3], self.corners[2], self.corners[6]])
        faceX12 = Triangle(normalX1, [self.corners[3], self.corners[6], self.corners[7]])
        faceX21 = Triangle(normalX2, [self.corners[0], self.corners[4], self.corners[5]])
        faceX22 = Triangle(normalX2, [self.corners[0], self.corners[5], self.corners[1]])

        # Get lowest and highest face orthogonal to y direction in x, z plane
        normalY1 = getNormalizedVector(np.array([relX, -relY, relZ]))
        normalY2 = getNormalizedVector(np.array([relX, relY, relZ]))

        faceY11 = Triangle(normalY1, [self.corners[4], self.corners[5], self.corners[6]])
        faceY12 = Triangle(normalY1, [self.corners[4], self.corners[6], self.corners[7]])
        faceY21 = Triangle(normalY2, [self.corners[0], self.corners[1], self.corners[2]])
        faceY22 = Triangle(normalY2, [self.corners[0], self.corners[2], self.corners[3]])

        # Get closest and furthest face orthogonal to z direction in x, y plane
        normalZ1 = getNormalizedVector(np.array([relX, relY, -relZ]))
        normalZ2 = getNormalizedVector(np.array([relX, relY, relZ]))

        faceZ11 = Triangle(normalZ1, [self.corners[1], self.corners[5], self.corners[6]])
        faceZ12 = Triangle(normalZ1, [self.corners[1], self.corners[6], self.corners[2]])
        faceZ21 = Triangle(normalZ2, [self.corners[0], self.corners[3], self.corners[7]])
        faceZ22 = Triangle(normalZ2, [self.corners[0], self.corners[7], self.corners[4]])

        # Collect all of the triangles
        self.triangles = [faceX11, faceX12, faceX21, faceX22,
                          faceY11, faceY12, faceY21, faceY22,
                          faceZ11, faceZ12, faceZ21, faceZ22]

    def __repr__(self):
        return "Block at x = {}, y = {}, z = {}".format(self.x, self.y, self.z)

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def getZ(self):
        return self.z

    def getXYZ(self):
        return np.array([self.x, self.y, self.z])

    def getCorners(self):
        return self.corners

    def intersect(self, ray, doEarlyOut=True):
        """
        Returns t value if ray intersects the block, else None. Optionally,
        doEarlyOut can be set to False to return the lowest valid t value, if any.
        """

        lowestT = 1e38

        for triangle in self.triangles:
            t = triangle.intersect(ray)

            if doEarlyOut:
                if t > 0.0 and t is not None:
                    return t
            else:
                if t > 0.0 and t < lowestT:
                    lowestT = t

        return lowestT if lowestT is not 1e38 else None

        """
        Class for handling vision through the use of observation cubes, cube size
        is in 1 direction. Use this class to help the agent "see".
        """

        def __init__(self, size):
            super(VisionHandler, self).__init__()
            self.size = size

            # Since real cube size is for both directions, we also do +1 for player
            self.realSize = size * 2 + 1
            self.numElements = self.realSize ** 3
            self.center = size
            self.matrix = np.zeros((self.realSize, self.realSize, self.realSize),
                                   dtype="|S25")

            self.__setupVisibilityMatrix()
            self.__setupVisibleBlockList()

        def __repr__(self):
            return "{}".format(self.matrix)

        def updateFromObservation(self, cubeObservation):
            """ Converts the 1D list of blocks into our 3D matrix. """

            # Sanity check, just in case
            if len(cubeObservation) != self.numElements:
                raise ValueError("cube observation uses different cube size!")

            # Directly copy over the list to a numpy matrix, reset the shape, and
            # swap the y and z axes (previous index / Malmo uses x, z, y)
            # 25 characters should be enough for block names...
            temp = np.array(cubeObservation, dtype="|S25")
            temp = np.reshape(temp, (self.realSize, self.realSize, self.realSize))
            self.matrix = np.swapaxes(temp, 1, 2)
            self.filterOccluded()

        def areValidRelCoords(self, relX, relY, relZ):
            """ Returns True/False if the given relative coords are valid. """
            if relX < -self.size or relX > self.size:
                return False

            if relY < -self.size or relY > self.size:
                return False

            if relZ < -self.size or relZ > self.size:
                return False

            return True

        def getBlockAtRelPos(self, relX, relY, relZ):
            """
            Returns the block at the given x, y, z position relative to the player.
            Returns empty string if -size > x, y, z or x, y, z > size (out of bounds).
            This also corresponds to "we don't know whats there".
            """
            if self.areValidRelCoords(relX, relY, relZ):
                return self.matrix[self.center + relY, self.center + relX, self.center + relZ]
            else:
                return ""

        def isBlock(self, relX, relY, relZ, blockName):
            """ Returns True/False if the given block is at the given relative position. """
            return self.getBlockAtRelPos(relX, relY, relZ) == blockName

        def findBlocks(self, blockName):
            """
            Returns a np array of np.array([x, y, z]) coordinates, where the given
            block is. An empty list is returned if the block cant be found. The
            returned list is sorted by distance from the player, so the closest
            blocks will be returned first.
            """
            coordinates = []
            distances = []
            playerPos = np.array([0, 0, 0])

            # Find the block we're looking for
            for block in self.visibleBlocks:
                x, y, z = block

                if self.isBlock(x, y, z, blockName):
                    coordinates.append(np.array([x, y, z]))
                    distances.append(getVectorDistance(block, playerPos))

            # Now we sort the blocks based on distance from the player
            coordinates = np.array(coordinates)
            distances = np.array(distances)
            sortedIndices = distances.argsort()
            return coordinates[sortedIndices]

        def getWalkableBlocks(self):
            """ Returns a list of all [x, y, z] blocks that the player can stand on. """
            walkableBlocks = []

            for block in self.visibleBlocks:
                x, y, z = block

                # TODO: Check if the block below our feet is a solid block that we
                # can stand on...
                if self.isBlock(x, y, z, "air") and self.isBlock(x, y + 1, z, "air"):
                    walkableBlocks.append(np.array([x, y, z]))

            return walkableBlocks

        def __setupVisibilityMatrix(self):
            self.visible = np.zeros((self.realSize, self.realSize, self.realSize), dtype=bool)

        def __fixDefaultVisibility(self):
            """ We can always "see" the 2 blocks where the player is standing """
            self.visible[self.center, self.center, self.center] = True
            self.visible[self.center + 1, self.center, self.center] = True

        def isVisible(self, relX, relY, relZ):
            """ Returns True/False if the given relative x, y, z block is visible. """
            return self.visible[self.center + relY, self.center + relX, self.center + relZ]

        def __setVisible(self, relX, relY, relZ):
            """ Sets the given relative x, y, z block to visible """
            self.visible[self.center + relY, self.center + relX, self.center + relZ] = True

        def __setInvisible(self, relX, relY, relZ):
            """ Sets the block at relative x, y, z coordinates to empty string. """
            self.visible[self.center + relY, self.center + relX, self.center + relZ] = False

        def __applyVisibility(self):
            """ Applies the visiblity matrix to the observation matrix. """
            for x in range(-self.size, self.size + 1):
                for y in range(-self.size, self.size + 1):
                    for z in range(-self.size, self.size + 1):
                        if not self.isVisible(x, y, z):
                            self.matrix[self.center + y, self.center + x, self.center + z] = ""

            self.__updateVisibleBlockList()

        def __setupVisibleBlockList(self):
            """
            Used to setup the list of visible blocks that can be used by FOV
            filtering and raytracing.
            """

            self.visibleBlocks = []

        def __addVisibleBlock(self, block):
            self.visibleBlocks.append(block)

        def __updateVisibleBlockList(self):
            """ Updates the list of visible blocks """
            self.__setupVisibleBlockList()

            for x in range(-self.size, self.size + 1):
                for y in range(-self.size, self.size + 1):
                    for z in range(-self.size, self.size + 1):
                        if self.isVisible(x, y, z):
                            self.__addVisibleBlock(np.array([x, y, z]))

        def __filterCoarse(self):
            """
            Determines the visibility matrix by doing a fast, coarse filtering of
            non-visible blocks, by looking at transparant blocks around the player
            and expanding outwards. This is a helper function and shouldnt be used
            directly outside this class. Ensure the self.visible matrix is available
            and initialized properly (aka, everything to False)...
            """

            # First we filter out all blocks that are not adjacent to a transparant
            # block, since they will not be visible anyway. We do this by starting
            # from the players eyes, and gradually marking visible/unvisible blocks
            # outwards.

            # The blocks where the player is standing is always visible of course...
            # Unless we are suffocating... in which case we're fucked...
            # Future TODO: Figure something out or not, I dont care
            if self.getBlockAtRelPos(0, 0, 0) not in TRANSPARANT_BLOCKS and \
                            self.getBlockAtRelPos(0, 1, 0) not in TRANSPARANT_BLOCKS:

                # Yup, we're suffocating... FUCK FUCK FUCK
                for i in range(42):
                    print "I CAN'T BREEEAATTHEEE!! HELP ME I'M FUCKING SUFFOCATING!!!"

            self.__fixDefaultVisibility()

            # We basically expand our search for visible blocks outward from where
            # the player is standing, and check adjacant blocks to see if they are
            # visible.
            # There are edge cases in which a block is not marked visible because
            # none of its neighbors have been marked as such, but they are in fact
            # potentially visible since its neighbors will be marked visible later
            # on. We can either fix this by doing multiple passes (easy), or by
            # changing the loops to work in an actual, outwards spiral (harder)...
            # Future TODO: Improve upon multiple passes method with something smarter
            iterations = 0

            while True:
                changedSomething = False

                for x in range(0, self.size + 1) + range(-1, -self.size - 1, -1):
                    for y in range(0, self.size + 1) + range(-1, -self.size - 1, -1):
                        for z in range(0, self.size + 1) + range(-1, -self.size - 1, -1):

                            # If this block is already visible, skip it
                            if self.isVisible(x, y, z):
                                continue

                            # Check 6 surrounding blocks if they're visible, first
                            # we check left and right blocks (x direction)
                            if x + 1 < self.size and self.isVisible(x + 1, y, z) and \
                                            self.getBlockAtRelPos(x + 1, y, z) in TRANSPARANT_BLOCKS:
                                self.__setVisible(x, y, z)
                                changedSomething = True
                                continue

                            if x - 1 > -self.size and self.isVisible(x - 1, y, z) and \
                                            self.getBlockAtRelPos(x - 1, y, z) in TRANSPARANT_BLOCKS:
                                self.__setVisible(x, y, z)
                                changedSomething = True
                                continue

                            # Then we check above and below blocks (y direction)
                            if y + 1 < self.size and self.isVisible(x, y + 1, z) and \
                                            self.getBlockAtRelPos(x, y + 1, z) in TRANSPARANT_BLOCKS:
                                self.__setVisible(x, y, z)
                                changedSomething = True
                                continue

                            if y - 1 > -self.size and self.isVisible(x, y - 1, z) and \
                                            self.getBlockAtRelPos(x, y - 1, z) in TRANSPARANT_BLOCKS:
                                self.__setVisible(x, y, z)
                                changedSomething = True
                                continue

                            # And finally check front and back blocks (z direction)
                            if z + 1 < self.size and self.isVisible(x, y, z + 1) and \
                                            self.getBlockAtRelPos(x, y, z + 1) in TRANSPARANT_BLOCKS:
                                self.__setVisible(x, y, z)
                                changedSomething = True
                                continue

                            if z - 1 > -self.size and self.isVisible(x, y, z - 1) and \
                                            self.getBlockAtRelPos(x, y, z - 1) in TRANSPARANT_BLOCKS:
                                self.__setVisible(x, y, z)
                                changedSomething = True
                                continue

                            # If no nieighbors are visible, this block is likely not
                            # visible either.
                            self.__setInvisible(x, y, z)

                iterations += 1

                if not changedSomething:
                    break

        def filterOccluded(self):
            """ Filters out all occluded blocks that the agent cannot see. """

            # Setup the visibility matrix, and do coarse filtering
            self.__setupVisibilityMatrix()
            self.__setupVisibleBlockList()
            self.__filterCoarse()
            self.__applyVisibility()
