# Main code for handling inventory

import MalmoPython
import numpy as np

from util import *
from math import *


# Key names used for inventory and hotbar
NAME_KEY = u"name"
AMOUNT_KEY = u"amount"

# How many slots hotbar and inventory have
INVENTORY_SLOTS = 40
HOTBAR_SLOTS = 9



class InventoryHotbar(object):
	"""
	Class used for handling agent inventory and hotbar.

	The inventory and hotbar are internally kept track of as 2 dictionairies:
	For both, the first one is the fully detailed inventory, e.g.:
		{
			"0": 								# Corresponds to slot 0
				{
					"name": "diamond_axe",
					"amount": 1					# How many are in the stack
				}, 								# etc
		}

	For both, the second in is just a dictionary with total amounts of how
	much is in the inventory/hotbar, e.g.:
		{
			"seeds": 1234,						# etc
		}
	"""

	def __init__(self):
		self.hotbarFull = {}
		self.hotbarAmount = {}
		self.inventoryFull = {}
		self.inventoryAmount = {}


	def __readSlotEntry(self, observation, slot, inventoryMode):
		"""
		Helper function that extracts item name and amount for the given slot
		from either the inventory or hotbar, and returns those 2 values.
		Returns "", 0  if there is nothing in that slot.
		"""
		method = "Inventory" if inventoryMode else "Hotbar"
		name = observation.get(u"{}_{}_item".format(method, slot), "")
		amount = int(observation.get(u"{}_{}_size".format(method, slot), 0))
		return name, amount


	def updateFromObservation(self, observation):
		""" Updates agent inventory and hotbar from observation. """
		self.inventoryFull = {}
		self.inventoryAmount = {}
		self.hotbarFull = {}
		self.hotbarAmount = {}

		if observation is not None:
			# Update inventory dicts first
			for i in range(0, INVENTORY_SLOTS):
				itemName, itemAmount = self.__readSlotEntry(observation, i, True)

				if itemName != "" and itemAmount != 0:
					self.inventoryFull[str(i)] = {
						NAME_KEY: itemName,
						AMOUNT_KEY: itemAmount
					}

					self.inventoryAmount[itemName] = itemAmount + \
						self.inventoryAmount.get(itemName, 0)

			# Then update hotbar dicts
			for i in range(0, HOTBAR_SLOTS):
				itemName, itemAmount = self.__readSlotEntry(observation, i, False)

				if itemName != "" and itemAmount != 0:
					self.hotbarFull[str(i)] = {
						NAME_KEY: itemName,
						AMOUNT_KEY: itemAmount
					}

					self.hotbarAmount[itemName] = itemAmount + \
						self.hotbarAmount.get(itemName, 0)



	def hasItemInInventory(self, itemName):
		""" Returns True/False if the given item is in the inventory. """
		return itemName in self.inventoryAmount


	def hasItemInHotbar(self, itemName):
		""" Returns True/False if the given item is in the hotbar. """
		return itemName in self.hotbarAmount



	def getItemInventoryAmount(self, itemName):
		""" Returns the amount of items in the inventory with the given name. """
		return self.inventoryAmount.get(itemName, 0)


	def getItemHotbarAmount(self, itemName):
		""" Returns the amount of items in the hotbar with the given name. """
		return self.hotbarAmount.get(itemName, 0)



	def getInventorySlot(self, itemName):
		"""
		Returns the first slot for the inventory in which the given item is, or
		-1 if the item is not in the inventory.
		"""
		for i in range(0, INVENTORY_SLOTS):
			# Check if there is something in this inventory slot
			if str(i) in self.inventoryFull:
				tempDict = self.inventoryFull[str(i)]

				if tempDict[NAME_KEY] == itemName:
					return i

		return -1


	def getHotbarSlot(self, itemName):
		"""
		Returns the first slot for the hotbar in which the given item is, or
		-1 if the item is not in the hotbar.
		"""
		for i in range(0, HOTBAR_SLOTS):
			# Check if there is something in this hotbar slot
			if str(i) in self.hotbarFull:
				tempDict = self.hotbarFull[str(i)]

				if tempDict[NAME_KEY] == itemName:
					return i

		return -1


