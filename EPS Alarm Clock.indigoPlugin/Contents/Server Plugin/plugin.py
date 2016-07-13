#! /usr/bin/env python
# -*- coding: utf-8 -*-

import indigo

import os
import sys
import time
import datetime

from eps.cache import cache
from eps import ui
from eps import dtutil
from eps import eps
from eps import devutil

################################################################################
class Plugin(indigo.PluginBase):
	
	#
	# Init
	#
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		
		# EPS common startup
		try:
			self.debug = pluginPrefs["debugMode"]
			pollingMode = pluginPrefs["pollingMode"]
			pollingInterval = int(pluginPrefs["pollingInterval"])
			pollingFrequency = pluginPrefs["pollingFrequency"]
			self.monitor = pluginPrefs["monitorChanges"]
		except:
			indigo.server.log ("Preference options may have changed or are corrupt,\n\tgo to Plugins -> %s -> Configure to reconfigure %s and then reload the plugin.\n\tUsing defaults for now, the plugin should operate normally." % (pluginDisplayName, pluginDisplayName), isError = True)
			self.debug = False
			pollingMode = "realTime"
			pollingInterval = 1
			pollingFrequency = "s"
			self.monitor = False
			
		# EPS common variables and classes
		self.reload = False
		self.cache = cache (self, pluginId, pollingMode, pollingInterval, pollingFrequency)
		devutil.parent = self
				
		# EPS plugin specific variables and classes
		
			
	################################################################################
	# EPS ROUTINES
	################################################################################
	
	#
	# Plugin menu: Performance options
	#
	def performanceOptions (self, valuesDict, typeId):
		self.debugLog(u"Saving performance options")
		errorsDict = indigo.Dict()
		
		# Save the performance options into plugin prefs
		self.pluginPrefs["pollingMode"] = valuesDict["pollingMode"]
		self.pluginPrefs["pollingInterval"] = valuesDict["pollingInterval"]
		self.pluginPrefs["pollingFrequency"] = valuesDict["pollingFrequency"]
		
		self.cache.setPollingOptions (valuesDict["pollingMode"], valuesDict["pollingInterval"], valuesDict["pollingFrequency"])
		
		return (True, valuesDict, errorsDict)
		
	#
	# Plugin menu: Library versions
	#
	def showLibraryVersions (self, forceDebug = False):
		s =  eps.debugHeader("LIBRARY VERSIONS")
		s += eps.debugLine (self.pluginDisplayName + " - v" + self.pluginVersion)
		s += eps.debugHeaderEx ()
		s += eps.debugLine ("Cache %s" % self.cache.version)
		s += eps.debugLine ("UI %s" % ui.libVersion(True))
		s += eps.debugLine ("DateTime %s" % dtutil.libVersion(True))
		s += eps.debugLine ("Core %s" % eps.libVersion(True))
		s += eps.debugHeaderEx ()
		
		if forceDebug:
			self.debugLog (s)
			return
			
		indigo.server.log (s)
		
	#
	# Device action: Update
	#
	def updateDevice (self, devAction):
		dev = indigo.devices[devAction.deviceId]
		self.updateAlarmInfo(dev)
			
		return
	
		
		
		children = self.cache.getSubDevices (dev)
		for devId in children:
			subDev = indigo.devices[int(devId)]	
			self.updateDeviceStates (dev, subDev)	
		
		return
		
	
				
	#
	# Device action: Generic
	#
	def deviceActions (self, devAction):
		#self.debugLog(unicode(devAction))
		
		dev = indigo.devices[devAction.deviceId]
		
		if devAction.pluginTypeId == "increaseHour": self.setAlarmTime (dev)	
		if devAction.pluginTypeId == "decreaseHour": self.setAlarmTime (dev, True)
		if devAction.pluginTypeId == "increaseMinute": self.setAlarmTime (dev, False, "minutes")
		if devAction.pluginTypeId == "decreaseMinute": self.setAlarmTime (dev, True, "minutes")
		
		if devAction.pluginTypeId == "increaseDuration": 
			i = dev.states["durationMinutes"] + int(dev.pluginProps["stepIncrement"])
			if i > 1400: i = 1400
			dev.updateStateOnServer("durationMinutes", i)
			self.validateAlarmTimes (dev)
			
		if devAction.pluginTypeId == "decreaseDuration": 
			i = dev.states["durationMinutes"] - int(dev.pluginProps["stepIncrement"])
			if i < int(dev.pluginProps["stepIncrement"]): i = int(dev.pluginProps["stepIncrement"])
			dev.updateStateOnServer("durationMinutes", i)
			self.validateAlarmTimes (dev)
			
		
		if devAction.pluginTypeId == "turnOn": self.enableAlarm (dev)
		if devAction.pluginTypeId == "turnOff": 
			dev.updateStateOnServer("isOn", False)
			dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOff)
			dev.updateStateOnServer("timeUntilOn", "00:00")
			dev.updateStateOnServer("timeUntilOff", "00:00") 
			dev.updateStateOnServer("statedisplay", "Off")
			
		if devAction.pluginTypeId == "toggle":
			if dev.states["isOn"]:
				dev.updateStateOnServer("isOn", False)
				dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOff)
				dev.updateStateOnServer("timeUntilOn", "00:00")
				dev.updateStateOnServer("timeUntilOff", "00:00") 
				dev.updateStateOnServer("statedisplay", "Off")
			else:
				self.enableAlarm (dev)
				
		if devAction.pluginTypeId == "resetAlarm":
			d = indigo.server.getTime()
			dev.updateStateOnServer("lastCalc", d.strftime("%Y-%m-%d %H:%M:%S"))
			dev.updateStateOnServer("timeUntilOn", "00:00")
			dev.updateStateOnServer("timeUntilOff", "00:00")
			dev.updateStateOnServer ("isActive", False)
			dev.updateStateOnServer ("isOn", False)
			indigo.device.turnOff(int(dev.pluginProps["device"]))
			
		if devAction.pluginTypeId == "toggleMonday": self.toggleDayOfWeek (dev, "Monday")
		if devAction.pluginTypeId == "toggleTuesday": self.toggleDayOfWeek (dev, "Tuesday")
		if devAction.pluginTypeId == "toggleWednesday": self.toggleDayOfWeek (dev, "Wednesday")
		if devAction.pluginTypeId == "toggleThursday": self.toggleDayOfWeek (dev, "Thursday")
		if devAction.pluginTypeId == "toggleFriday": self.toggleDayOfWeek (dev, "Friday")
		if devAction.pluginTypeId == "toggleSaturday": self.toggleDayOfWeek (dev, "Saturday")
		if devAction.pluginTypeId == "toggleSunday": self.toggleDayOfWeek (dev, "Sunday")
		
		if devAction.pluginTypeId == "manualOff" and dev.states["isActive"]:
			d = indigo.server.getTime()
			if dev.pluginProps["manualOff"] != "0":
				# Force a new stop time into the device
				newStopTime = dtutil.DateAdd("minutes", int(dev.pluginProps["manualOff"]), d)
				dev.updateStateOnServer("endTime", newStopTime.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(newStopTime, dev.pluginProps["militaryTime"]))
				
				# Force counters to run immediately
				newCalc = dtutil.DateAdd("days", -1, d) 
				dev.updateStateOnServer("lastCalc", newCalc.strftime("%Y-%m-%d %H:%M:%S"))
				
				return # we do NOT want updateAlarmInfo to run at the end of this routine, otherwise our stop time gets recalculated
			else:
				self.deactivateAlarm (dev)
				
				# The following for failsafes
				indigo.device.turnOff(int(dev.pluginProps["device"]))
				dev.updateStateOnServer("lastCalc", d.strftime("%Y-%m-%d %H:%M:%S"))
				dev.updateStateOnServer("timeUntilOn", "00:00")
				dev.updateStateOnServer("timeUntilOff", "00:00")
				dev.updateStateOnServer ("isActive", False)	
				
				
		# Always update the alarm for UI purposes after any action
		self.updateAlarmInfo(dev)
			
		return
		
		
	#
	# Update device
	#
	def updateDeviceStates (self, parentDev, childDev = None):
		stateChanges = self.cache.deviceUpdate (parentDev)
		
		return
		
	#
	# Add watched states
	#
	def addWatchedStates (self, subDevId = "*", deviceTypeId = "*", mainDevId = "*"):
		
		self.cache.addWatchState ("onOffState", subDevId, "epsalarmclock")
		self.cache.addWatchState ("brightnessLevel", subDevId, "epsalarmclock")
		
		#self.cache.addWatchState (848833485, "onOffState", 1089978714)
		
		#self.cache.addWatchState ("onOffState", subDevId, deviceTypeId, mainDevId) # All devices, pass vars
		#self.cache.addWatchState ("onOffState") # All devices, all subdevices, all types
		#self.cache.addWatchState ("onOffState", 848833485) # All devices, this subdevice, all types
		#self.cache.addWatchState ("onOffState", subDevId, "epslcdth") # All devices, all subdevices of this type
		#self.cache.addWatchState ("onOffState", 848833485, "*", 1089978714) # This device, this subdevice of all types
		
		return
	
	
	################################################################################
	# EPS HANDLERS
	################################################################################
		
	#
	# Device menu selection changed
	#
	def onDeviceSelectionChange (self, valuesDict, typeId, devId):
		# Just here so we can refresh the states for dynamic UI
		return valuesDict
		
	#
	# Return option array of device states to (filter is the device to query)
	#
	def getStatesForDevice(self, filter="", valuesDict=None, typeId="", targetId=0):
		return ui.getStatesForDevice (filter, valuesDict, typeId, targetId)
		
	#
	# Return option array of devices with filter in states (filter is the state(s) to query)
	#
	def getDevicesWithStates(self, filter="onOffState", valuesDict=None, typeId="", targetId=0):
		return ui.getDevicesWithStates (filter, valuesDict, typeId, targetId)
		
	#
	# Return option array of device plugin props to (filter is the device to query)
	#
	def getPropsForDevice(self, filter="", valuesDict=None, typeId="", targetId=0):
		return ui.getPropsForDevice (filter, valuesDict, typeId, targetId)
		
	#
	# Return option array of plugin devices props to (filter is the plugin(s) to query)
	#
	def getPluginDevices(self, filter="", valuesDict=None, typeId="", targetId=0):
		return ui.getPluginDevices (filter, valuesDict, typeId, targetId)
				
	#
	# Handle ui button click
	#
	def uiButtonClicked (self, valuesDict, typeId, devId):
		if valuesDict["alarmSpeech"] != "":
			self.speakRepeat (None, valuesDict["alarmSpeech"], valuesDict["nagTimes"], valuesDict["speechRepeat"])
			
		return valuesDict
		
	#
	# Concurrent thread process fired
	#
	def onRunConcurrentThread (self):
		# Go through all of our devices and find any enabled alarms
		self.updateAlarms()
		return
		
		
	################################################################################
	# EPS ROUTINES TO BE PUT INTO THEIR OWN CLASSES / METHODS
	################################################################################
		
	
	################################################################################
	# INDIGO DEVICE EVENTS
	################################################################################
	
	#
	# Device starts communication
	#
	def deviceStartComm(self, dev):
		self.debugLog(u"%s starting communication" % dev.name)
		dev.stateListOrDisplayStateIdChanged() # Force plugin to refresh states from devices.xml
		if self.cache is None: return
		
		if "lastreset" in dev.states:
			d = indigo.server.getTime()
			if dev.states["lastreset"] == "": dev.updateStateOnServer("lastreset", d.strftime("%Y-%m-%d "))
			
		if "lastCalc" in dev.states:
			d = indigo.server.getTime()
			if dev.states["lastCalc"] == "": dev.updateStateOnServer("lastCalc", d.strftime("%Y-%m-%d %H:%M:%S"))
			
		if eps.valueValid (dev.states, "statedisplay", True):
			self.debugLog("Device doesn't have a valid device state, setting the state now")
			
			# There is no state display, set it now - 1.1.1
			if dev.states["isOn"]:
				dev.updateStateOnServer("statedisplay", "On")
				dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)
			else:
				dev.updateStateOnServer("statedisplay", "Off")
				dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOff)
			
		if eps.stateValid (dev, "startTime", True) == False: 
			self.debugLog("Device doesn't have a start time, creating a default alarm for 8:00 AM")
			
			# added in 1.1.1 or creating the start date will fail because there are no days
			self.auditDays (dev)
			resetday = dev.states["isSaturday"]
			dev.updateStateOnServer ("isSaturday", True) # failsafe			
			
			d = indigo.server.getTime()
			t = datetime.datetime.strptime(d.strftime("%Y-%m-%d") + " 08:00:00", "%Y-%m-%d %H:%M:%S")
			#t = self.proposedFutureTime (t, dev)
			t = self.getNextStartTime (dev, t) # 1.1.1
			
			dev.updateStateOnServer("startTime", t.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(t, dev.pluginProps["militaryTime"]))		
			
			dev.updateStateOnServer ("isSaturday", resetday) # failsafe	
			
		if eps.stateValid (dev, "endTime", True) == False: 
			self.debugLog("Device doesn't have an end time, calculating the next available end time from the start time")
			d = datetime.datetime.strptime (dev.states["startTime"], "%Y-%m-%d %H:%M:%S")
			#t = dtutil.DateAdd("minutes", int(dev.pluginProps["defaultDuration"]), d)			
			#t = self.proposedFutureTime (t, dev, t.strftime("%Y-%m-%d %H:%M:%S"))
			t = self.setAlarmEndTime (dev, d) # 1.1.1
			
			dev.updateStateOnServer("endTime", t.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(t, dev.pluginProps["militaryTime"]))	
			
		if "durationMinutes" in dev.states:
			if dev.states["durationMinutes"] == 0: dev.updateStateOnServer("durationMinutes", int(dev.pluginProps["defaultDuration"]))	
				
		if self.cache.deviceInCache (dev.id) == False:
			self.debugLog(u"%s not in cache, appears to be a new device or plugin was just started" % dev.name)
			self.cache.cacheDevices() # Failsafe
		
		
		
		#dev.updateStateOnServer("startTime", "2016-06-08 17:00:00") # Debug testing
		self.validateAlarmTimes(dev)
			
		self.addWatchedStates("*", dev.deviceTypeId, dev.id) # Failsafe
		#self.cache.dictDump (self.cache.devices[dev.id])
		#indigo.server.log(unicode(dev.states))
		X = 1 # placeholder
			
		return
	
	#
	# Device stops communication
	#
	def deviceStopComm(self, dev):
		self.debugLog(u"%s stopping communication" % dev.name)
		
	#
	# Device property changed
	#
	def didDeviceCommPropertyChange(self, origDev, newDev):
		self.debugLog(u"%s property changed" % origDev.name)
		return True	
	
	#
	# Device property changed
	#
	def deviceUpdated(self, origDev, newDev):
		if self.cache is None: return
		
		if origDev.pluginId == self.pluginId:
			self.debugLog(u"Plugin device %s was updated" % origDev.name)
			
			if eps.isNewDevice(origDev, newDev):
				self.debugLog("New device '%s' detected, restarting device communication" % newDev.name)
				self.deviceStartComm (newDev)
				return							
						
			# Re-cache the device and it's subdevices and states
			if eps.propsChanged (origDev, newDev):
				# Assume that the properties now allow the alarm to be a different day, including today, so set the alarm to today and validate it
				startTime = datetime.datetime.strptime (newDev.states["startTime"], "%Y-%m-%d %H:%M:%S")
				d = indigo.server.getTime()
				newStartTime = datetime.datetime.strptime(d.strftime("%Y-%m-%d") + startTime.strftime(" %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
				
				# Write the new start time to the device, when startComm runs again it will re-validate it so this should be fine
				newDev.updateStateOnServer("startTime", newStartTime.strftime ("%Y-%m-%d %H:%M:%S"))
			
				self.debugLog(u"Plugin device %s settings changed, rebuilding watched states" % origDev.name)
				self.cache.removeDevice (origDev.id)
				self.deviceStartComm (newDev)
				
		else:
			changedStates = self.cache.watchedStateChanged (origDev, newDev)
			if changedStates:
				self.debugLog(u"The monitored device %s had a watched state change" % origDev.name)
				# Send parent device array and changed states array to function to disseminate
				#indigo.server.log(unicode(changedStates))
				X = 1 # placeholder
			
		return
		
	#
	# Device deleted
	#
	def deviceDeleted(self, dev):
		if dev.pluginId == self.pluginId:
			self.debugLog("%s was deleted" % dev.name)
			self.cache.removeDevice (dev.id)
		
	
	################################################################################
	# INDIGO DEVICE UI EVENTS
	################################################################################	
	
		
	#
	# Device pre-save event
	#
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		dev = indigo.devices[devId]
		self.debugLog(u"%s is validating device configuration UI" % dev.name)
		return (True, valuesDict)
		
	#
	# Device config button clicked event
	#
	def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
		dev = indigo.devices[devId]
		self.debugLog(u"%s is closing device configuration UI" % dev.name)
		
		if userCancelled == False: 
			self.debugLog(u"%s configuration UI was not cancelled" % dev.name)
			
		#self.cache.dictDump (self.cache.devices[dev.id])
			
		return
		
	#
	# Event pre-save event
	#
	def validateEventConfigUi(self, valuesDict, typeId, eventId):
		self.debugLog(u"Validating event configuration UI")
		return (True, valuesDict)
		
	#
	# Event config button clicked event
	#
	def closedEventConfigUi(self, valuesDict, userCancelled, typeId, eventId):
		self.debugLog(u"Closing event configuration UI")
		return
		
	#
	# Action pre-save event
	#
	def validateActionConfigUi(self, valuesDict, typeId, actionId):
		self.debugLog(u"Validating event configuration UI")
		return (True, valuesDict)
		
	#
	# Action config button clicked event
	#
	def closedActionConfigUi(self, valuesDict, userCancelled, typeId, actionId):
		self.debugLog(u"Closing action configuration UI")
		return
		
		
	################################################################################
	# INDIGO PLUGIN EVENTS
	################################################################################	
	
	#
	# Plugin startup
	#
	def startup(self):
		self.debugLog(u"Starting plugin")
		if self.cache is None: return
		
		if self.monitor: 
			if self.cache.pollingMode == "realTime": indigo.devices.subscribeToChanges()
		
		# Add all sub device variables that our plugin links to, reloading only on the last one
		#self.cache.addSubDeviceVar ("weathersnoop", False) # Add variable, don't reload cache
		#self.cache.addSubDeviceVar ("irrigation") # Add variable, reload cache
		
		# Not adding any sub device variables, reload the cache manually
		self.cache.cacheDevices()
		
		#self.cache.dictDump (self.cache.devices)
		
		return
		
	#	
	# Plugin shutdown
	#
	def shutdown(self):
		self.debugLog(u"Plugin shut down")	
	
	#
	# Concurrent thread
	#
	def runConcurrentThread(self):
		if self.cache is None:
			try:
				while True:
					self.sleep(1)
					if self.reload: break
			except self.StopThread:
				pass
			
			# Only happens if we break out due to a restart command
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)
				
			return
		
		try:
			while True:
				if self.cache.pollingMode == "realTime" or self.cache.pollingMode == "pollDevice":
					self.onRunConcurrentThread()
					self.sleep(1)
					if self.reload: break
				else:
					self.onRunConcurrentThread()
					self.sleep(self.cache.pollingInterval)
					if self.reload: break
					
				# Only happens if we break out due to a restart command
				serverPlugin = indigo.server.getPlugin(self.pluginId)
         		serverPlugin.restart(waitUntilDone=False)
		
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.
	
	
	################################################################################
	# INDIGO PLUGIN UI EVENTS
	################################################################################	
	
	#
	# Plugin config pre-save event
	#
	def validatePrefsConfigUi(self, valuesDict):
		self.debugLog(u"%s is validating plugin config UI" % self.pluginDisplayName)
		return (True, valuesDict)
		
	#
	# Plugin config button clicked event
	#
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		self.debugLog(u"%s is closing plugin config UI" % self.pluginDisplayName)
		
		if userCancelled == False:
			if "debugMode" in valuesDict:
				self.debug = valuesDict["debugMode"]
		
		return
			
	#
	# Stop concurrent thread
	#
	def stopConcurrentThread(self):
		self.debugLog(u"Plugin stopping concurrent threads")	
		self.stopThread = True
		
	#
	# Delete
	#
	def __del__(self):
		self.debugLog(u"Plugin delete")	
		indigo.PluginBase.__del__(self)
		
	
	################################################################################
	# PLUGIN SPECIFIC ROUTINES
	################################################################################	
	
	#
	# Validate and set alarm's start and end dates
	#
	def validateAlarmTimes (self, dev, startTime = None, endTime = None):
		if dev.states["isActive"]: 
			dev.updateStateOnServer("statedisplay", "Active")	
			self.debugLog(u"%s is currently in an active state, skipping calculation" % dev.name)
			return # If the alarm is active don't recalc anything, it'll throw off the stop time (like if they reload the plugin)
	
		if startTime is None: startTime = datetime.datetime.strptime (dev.states["startTime"], "%Y-%m-%d %H:%M:%S")
		if endTime is None: endTime = datetime.datetime.strptime (dev.states["endTime"], "%Y-%m-%d %H:%M:%S")
		
		self.debugLog (u"Checking if the alarm %s to %s is valid" % (unicode(startTime), unicode(endTime)))
		
		d = indigo.server.getTime()
		minutesUntilStart = dtutil.DateDiff ("minutes", startTime, d)
		lastCalc = dtutil.DateAdd ("days", -1, d) # if we update anything roll back lastcalc to force it to update immediately
		
		self.auditDays (dev)
		
		if eps.stateValid (dev, "isOn"):
			if dev.states["isOn"]:
				dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOn)
				
				if minutesUntilStart > 0:
					self.debugLog(u"\tthe alarm is currently enabled and in the future, verifying validity")
					if self.dayIsValid (dev, startTime):
						self.debugLog(u"\t\tthe alarm is valid")
						
						# Set the end time for good measure and to be safe
						endTime = self.setAlarmEndTime (dev, startTime)
						dev.updateStateOnServer("startTime", startTime.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(startTime, dev.pluginProps["militaryTime"]))
						dev.updateStateOnServer("endTime", endTime.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(endTime, dev.pluginProps["militaryTime"]))
						dev.updateStateOnServer("lastCalc", lastCalc.strftime("%Y-%m-%d %H:%M:%S"))
						return
						
					else:
						self.debugLog(u"\t\tthe alarm is not valid, recalculating alarm start date/time")
						startTime = self.getNextStartTime (dev, startTime)
						
				else:
					# The alarm is in the past, at best it cannot happen again until tomorrow, so try that
					self.debugLog(u"\tthe alarm is in the past, validating for tomorrow")
					self.validateAlarmTimes (dev, dtutil.DateAdd("days", 1, startTime))
					return

			else:
				dev.updateStateImageOnServer(indigo.kStateImageSel.TimerOff)
				dev.updateStateOnServer("timeUntilOn", "00:00") # Failsafe
				dev.updateStateOnServer("timeUntilOff", "00:00") # Failsafe
				dev.updateStateOnServer("statedisplay", "Off") # Failsafe
				dev.updateStateOnServer("startTime", startTime.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(startTime, dev.pluginProps["militaryTime"]))
				dev.updateStateOnServer("endTime", endTime.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(endTime, dev.pluginProps["militaryTime"]))	
				
				self.debugLog(u"\tthe alarm is currently not enabled, not verifying since it will be verified when it is turned on")
				return

		else:
			self.debugLog(u"\tthe isOn state is missing, this could be a new device")		
			return
						
					
		# If we get here then we are ready to finish up, start with adding our end time
		endTime = self.setAlarmEndTime (dev, startTime)
		self.debugLog (u"\tthe alarm will now be %s to %s" % (unicode(startTime), unicode(endTime)))
		
		# Write all of our settings to the device and set the last check time to yesterday to insure an immediate update
		dev.updateStateOnServer("startTime", startTime.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(startTime, dev.pluginProps["militaryTime"]))
		dev.updateStateOnServer("endTime", endTime.strftime ("%Y-%m-%d %H:%M:%S"), uiValue=self.dtToString(endTime, dev.pluginProps["militaryTime"]))
		
		dev.updateStateOnServer("lastCalc", lastCalc.strftime("%Y-%m-%d %H:%M:%S"))
		
		return
		
	#
	# Calculate the alarm end time
	#
	def setAlarmEndTime (self, dev, startTime):
		origEndTime = "" # 1.1.1
		
		if eps.valueValid(dev.states, "endTime", True): # 1.1.1
			origEndTime = datetime.datetime.strptime (dev.states["endTime"], "%Y-%m-%d %H:%M:%S")
		
		if dev.states["durationMinutes"] == 0:
			# Save our default duration to the duration state
			dev.updateStateOnServer("durationMinutes", int(dev.pluginProps["defaultDuration"]))
			
		endTime = dtutil.DateAdd("minutes", int(dev.states["durationMinutes"]), startTime)
		
		if origEndTime != endTime: self.debugLog(u"\t\tend time recalculated, new alarm time is %s to %s" % (unicode(startTime), unicode(endTime)))
		
		return endTime

	# 
	# Calculate next valid start time for an alarm (we get here because the time is already invalid)
	#
	def getNextStartTime (self, dev, startTime):
		# Start from today and work our way up by a week to find the next good day
		for y in range(0, 8):
			newdate = dtutil.DateAdd ("days", y, startTime)
			
			self.debugLog(u"\t\t\tchecking if %s is a valid start time" % unicode(newdate))
			
			if self.dayIsValid (dev, newdate):
				self.debugLog(u"\t\t\tit's permitted")
				return newdate
			else:
				self.debugLog(u"\t\t\tit's not permitted")
				
				
	#
	# Audit days of week for user based versus device based
	#
	def auditDays (self, dev):
		if dev.pluginProps["enableDOW"] == False and len(dev.pluginProps["daysOfWeek"]) > 0:
			self.debugLog (u"\tforcing days of the week to comply with device configuration")
			
			isOn = {}
			
			for i in range (0, 8):
				for w in dev.pluginProps["daysOfWeek"]:
					if int(w) == i: isOn[i] = True
			
			if len(isOn) > 0:
				if 0 in isOn:
					dev.updateStateOnServer("isSunday", True)
				else:
					dev.updateStateOnServer("isSunday", False)
					
				if 1 in isOn:
					dev.updateStateOnServer("isMonday", True)
				else:
					dev.updateStateOnServer("isMonday", False)
					
				if 2 in isOn:
					dev.updateStateOnServer("isTuesday", True)
				else:
					dev.updateStateOnServer("isTuesday", False)
					
				if 3 in isOn:
					dev.updateStateOnServer("isWednesday", True)
				else:
					dev.updateStateOnServer("isWednesday", False)
					
				if 4 in isOn:
					dev.updateStateOnServer("isThursday", True)
				else:
					dev.updateStateOnServer("isThursday", False)
					
				if 5 in isOn:
					dev.updateStateOnServer("isFriday", True)
				else:
					dev.updateStateOnServer("isFriday", False)
					
				if 6 in isOn:
					dev.updateStateOnServer("isSaturday", True)
				else:
					dev.updateStateOnServer("isSaturday", False)
					
				
				
	#
	# See if we have only permitted certain days for this date/time
	#
	def dayIsValid (self, dev, value):
		dow = int(value.strftime("%w"))
		dname = "Sunday"
		
		if dow == 1: dname = "Monday"
		if dow == 2: dname = "Tuesday"
		if dow == 3: dname = "Wednesday"
		if dow == 4: dname = "Thursday"
		if dow == 5: dname = "Friday"
		if dow == 6: dname = "Saturday"
		
		self.debugLog(u"\t\t\tconfiguration says %s is %s" % ("is" + dname, unicode(dev.states["is" + dname])))
		
		return dev.states["is" + dname]
		
		
	#
	# Change alarm date/time
	#
	def setAlarmTime (self, dev, subtract = False, method = "hours"):
		method = method.lower()
		
		# Assume today as the alarm date always
		d = indigo.server.getTime()
		today = d.strftime ("%Y-%m-%d ")
		
		startTime = datetime.datetime.strptime (dev.states["startTime"], "%Y-%m-%d %H:%M:%S")
		startTime = today + startTime.strftime ("%H:%M:%S")
		startTime = datetime.datetime.strptime (startTime, "%Y-%m-%d %H:%M:%S")
		
		if method == "hours":		
			if subtract:
				startTime = dtutil.DateAdd ("hours", -1, startTime)
			else:
				startTime = dtutil.DateAdd ("hours", 1, startTime)
		else:
			if subtract:
				startTime = dtutil.DateAdd ("minutes", int(dev.pluginProps["stepIncrement"]) * -1, startTime)
			else:
				startTime = dtutil.DateAdd ("minutes", int(dev.pluginProps["stepIncrement"]), startTime)
		
		
		self.validateAlarmTimes (dev, startTime)
		
	#
	# Derive time string from datetime value
	#
	def dtToString (self, value, military = False):
		if military == False:
			H = int(value.strftime("%H"))
		
			if H >= 12:
				if H > 12: H = H - 12
				return value.strftime("%02d" % (H,) + ":%M.")
			if H == 0:
				return value.strftime("12:%M")
			else:
				return value.strftime("%H:%M")
				
		else:
			return value.strftime("%H:%M")
			
			
	#
	# Activate the alarm
	#
	def activateAlarm (self, dev):
		d = indigo.server.getTime()
		dev.updateStateOnServer ("isActive", True)
		dev.updateStateOnServer("timeUntilOn", "00:00")
		dev.updateStateOnServer("lastCalc", d.strftime("%Y-%m-%d %H:%M:%S"))
	
		if int(dev.pluginProps["blinkLights"]) > 0:
			self.debugLog (u"\tblinking %s times" % dev.pluginProps["blinkLights"])
			for i in range(1, int(dev.pluginProps["blinkLights"]) + 1):
				indigo.device.turnOn(int(dev.pluginProps["device"]))
				self.sleep(1)
				indigo.device.turnOff(int(dev.pluginProps["device"]))
				self.sleep(1)
				
		indigo.device.turnOn(int(dev.pluginProps["device"]))
				
		if dev.pluginProps["alarmSpeech"] != "":
			self.speakRepeat (dev)
			
		if dev.pluginProps["onAlarmOn"] != "":
			indigo.actionGroup.execute(int(dev.pluginProps["onAlarmOn"]))
		
		dev.updateStateOnServer("statedisplay", "Active")	
			
		# Calculate the auto off time
		self.alarmCountdown(dev, "endTime")
		
		
		
	#
	# Deactivate the alarm
	#
	def deactivateAlarm (self, dev):
		d = indigo.server.getTime()
		
		indigo.device.turnOff(int(dev.pluginProps["device"]))
		dev.updateStateOnServer ("isOn", False)
		dev.updateStateOnServer ("isActive", False)
		dev.updateStateOnServer("lastCalc", d.strftime("%Y-%m-%d %H:%M:%S"))
		dev.updateStateOnServer("timeUntilOff", "00:00")
		
		if dev.pluginProps["onAlarmOff"] != "":
			indigo.actionGroup.execute(int(dev.pluginProps["onAlarmOff"]))
		
		# If we have auto recurring on then re-enable and calculate
		if dev.pluginProps["autoRecurring"]:
			self.enableAlarm (dev)
			
		else:
			dev.updateStateOnServer("timeUntilOn", "00:00")
			
			
	#
	# Enable the alarm (turn it on)
	#
	def enableAlarm (self, dev):
		dev.updateStateOnServer("isOn", True)
		self.validateAlarmTimes (dev)	
					
	#
	# Calculate alarm countdown
	#
	def alarmCountdown (self, dev, calcState="startTime"):
		d = indigo.server.getTime()
		startTime = datetime.datetime.strptime (dev.states[calcState], "%Y-%m-%d %H:%M:%S")
				
		td = startTime - d
		hours, remainder = divmod(td.seconds, 3600)
		minutes, seconds = divmod(remainder, 60)
		
		if seconds >= 1: minutes = minutes + 1 # We don't report seconds, round up
		
		if td.days > 0:
			if dev.pluginProps["uiOption"]:
				countdown = u"+%02dD" % (td.days)
			else:
				countdown = u"%02d:%02d:%02d" % (td.days, hours, minutes)
		else:
			countdown = u"%02d:%02d" % (hours, minutes)
		
		dev.updateStateOnServer("lastCalc", d.strftime("%Y-%m-%d %H:%M:%S"))
		
		# Update the countdown state
		if calcState == "startTime":
			self.debugLog (u"\ttime until alarm comes on: %s" % countdown)
			dev.updateStateOnServer("timeUntilOn", countdown)	
			dev.updateStateOnServer("statedisplay", countdown)	
		elif calcState == "endTime":
			self.debugLog (u"\ttime until alarm turns off: %s" % countdown)
			dev.updateStateOnServer("timeUntilOff", countdown)
						
	#
	# Process alarms
	#
	def updateAlarms (self):
		# Find all enabled alarms
		for dev in indigo.devices.iter("com.eps.indigoplugin.alarm-clock.epsalarmclock"):
			self.updateAlarmInfo (dev)
			
	#
	# Process single alarm
	#
	def updateAlarmInfo (self, dev):
		# Alarm is turned on but has not yet triggered
		d = indigo.server.getTime()
		
		if dev.states["isOn"]:
			startTime = datetime.datetime.strptime (dev.states["startTime"], "%Y-%m-%d %H:%M:%S")
			if dev.states["isActive"]: startTime = datetime.datetime.strptime (dev.states["endTime"], "%Y-%m-%d %H:%M:%S")
			
			lastCalc = datetime.datetime.strptime (dev.states["lastCalc"], "%Y-%m-%d %H:%M:%S")
			lastCalcMinutes = dtutil.DateDiff ("minutes", d, lastCalc)
			
			hours = dtutil.DateDiff ("hours", startTime, d)
							
			if hours > 23 and lastCalcMinutes > 480:
				# Alarms more than a day away update every 8 hours
				self.debugLog (u"\tit has been %i hours since the last calculation, calculating now" % (lastCalcMinutes / 60))
				if dev.states["isActive"]:
					self.alarmCountdown(dev, "endTime")
				else:
					self.alarmCountdown(dev)
					
				return
			
			if hours <= 24 and hours >= 1 and lastCalcMinutes > 1:
				# Calculate every 1 minute for todays alarms
				self.debugLog (u"\tit has been %i minutes since the last calculation, calculating now" % lastCalcMinutes)
				if dev.states["isActive"]:
					self.alarmCountdown(dev, "endTime")
				else:
					self.alarmCountdown(dev)
					
				return
				
			if hours < 1:
				# Last hour we calculate every 20 seconds for better accuracy
				seconds = dtutil.DateDiff ("seconds", startTime, d)
				lastCalcSeconds = dtutil.DateDiff ("seconds", d, lastCalc)
				
				if seconds > 0 and lastCalcSeconds >= 20:
					self.debugLog (u"\tit has been %i seconds since the last calculation, calculating now" % lastCalcSeconds)
				
					if dev.states["isActive"]:
						self.alarmCountdown(dev, "endTime")
					else:
						self.alarmCountdown(dev)

					return	
					
				if seconds <= 0 and dev.states["isActive"] == False:
					self.debugLog (u"\talarm is happening now")
					self.activateAlarm (dev)
					return
					
				if seconds <= 0 and dev.states["isActive"]:
					dev.updateStateOnServer ("isOn", False)
					dev.updateStateOnServer ("isActive", False)
					self.debugLog (u"\talarm is turning off now")
					self.deactivateAlarm (dev)
					return
						
	#
	# Toggle day of week schedule
	#
	def toggleDayOfWeek (self, dev, value):
		if dev.pluginProps["enableDOW"] == False: return # no sense bothering if it's not allowed in device config
		
		# Make sure they aren't trying to turn off the last day
		dayCnt = 0
		
		if dev.states["isMonday"]: dayCnt = dayCnt + 1
		if dev.states["isTuesday"]: dayCnt = dayCnt + 1
		if dev.states["isWednesday"]: dayCnt = dayCnt + 1
		if dev.states["isThursday"]: dayCnt = dayCnt + 1
		if dev.states["isFriday"]: dayCnt = dayCnt + 1
		if dev.states["isSaturday"]: dayCnt = dayCnt + 1
		if dev.states["isSunday"]: dayCnt = dayCnt + 1
	
		if dev.states["is" + value]:
			if dayCnt < 2:
				indigo.server.log (u"Control page attempted to turn off every day of the week, this isn't possible.  It's easier to just turn off the alarm!", isError=True)
				return

			dev.updateStateOnServer("is" + value, False)
		else:
			dev.updateStateOnServer("is" + value, True)
			
		# Since this changes things, force the alarm to revalidate starting at today
		startTime = datetime.datetime.strptime (dev.states["startTime"], "%Y-%m-%d %H:%M:%S")
		d = indigo.server.getTime()
		newStartTime = datetime.datetime.strptime(d.strftime("%Y-%m-%d") + startTime.strftime(" %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
		self.validateAlarmTimes (dev, newStartTime)
		
	#
	# Speak and repeat
	#
	def speakRepeat (self, dev=None, value="Test 1 2 3", repeat="5", interval="5"):
		# If we got a device we use those values, otherwise use the ones passed (allows for testing)
		if dev is None:
			self.debugLog(u"No device passed to speech processor, using parameters passed")
		else:
			self.debugLog(u"Using device props to facilitate speech")
			value = dev.pluginProps["alarmSpeech"]
			repeat = dev.pluginProps["nagTimes"]
			interval = dev.pluginProps["speechRepeat"]
		
		# For now repeat just three times with 2 second intervals
		for i in range(0,int(repeat)):	
			indigo.server.speak(value, waitUntilDone=False)
			self.sleep(2)
			
		return
	
		# Below is experimental, once working properly we'll enable in the plugin
		
		# Figure out how often to repeat based on the repeat count and interval
		sleeptime = int(interval) / int(repeat)
		
		for i in range(1, (int(repeat) + 1)):
			indigo.server.speak(value, waitUntilDone=False)
			self.sleep(sleeptime)
			
	################################################################################
	# SUPPORT DEBUG ROUTINE - 1.1.1
	################################################################################	
	
	#
	# Plugin menu: Support log
	#
	def supportLog (self):
		self.showLibraryVersions ()
		
		s = eps.debugHeader("SUPPORT LOG")
		
		# Get plugin prefs
		s += eps.debugHeader ("PLUGIN PREFRENCES", "=")
		for k, v in self.pluginPrefs.iteritems():
			s += eps.debugLine(k + " = " + unicode(v), "=")
			
		s += eps.debugHeaderEx ("=")
		
		# Report on cache
		s += eps.debugHeader ("DEVICE CACHE", "=")
		
		for devId, devProps in self.cache.devices.iteritems():
			s += eps.debugHeaderEx ("*")
			s += eps.debugLine(devProps["name"] + ": " + str(devId) + " - " + devProps["deviceTypeId"], "*")
			s += eps.debugHeaderEx ("*")
			
			s += eps.debugHeaderEx ("-")
			s += eps.debugLine("SUBDEVICES", "-")
			s += eps.debugHeaderEx ("-")
			
			for subDevId, subDevProps in devProps["subDevices"].iteritems():
				s += eps.debugHeaderEx ("+")
				s += eps.debugLine(subDevProps["name"] + ": " + str(devId) + " - " + subDevProps["deviceTypeId"] + " (Var: " + subDevProps["varName"] + ")", "+")
				s += eps.debugHeaderEx ("+")
				
				s += eps.debugLine("WATCHING:", "+")
				
				for z in subDevProps["watchStates"]:
					s += eps.debugLine("     " + z, "+")
					
				if subDevId in indigo.devices:
					d = indigo.devices[subDevId]
					if d.pluginId != self.pluginId:
						s += eps.debugHeaderEx ("!")
						s += eps.debugLine(d.name + ": " + str(d.id) + " - " + d.deviceTypeId, "!")
						s += eps.debugHeaderEx ("!")
					
						s += eps.debugHeaderEx ("-")
						s += eps.debugLine("PREFERENCES", "-")
						s += eps.debugHeaderEx ("-")
			
						for k, v in d.pluginProps.iteritems():
							s += eps.debugLine(k + " = " + unicode(v), "-")
				
						s += eps.debugHeaderEx ("-")
						s += eps.debugLine("STATES", "-")
						s += eps.debugHeaderEx ("-")
			
						for k, v in d.states.iteritems():
							s += eps.debugLine(k + " = " + unicode(v), "-")
						
						s += eps.debugHeaderEx ("-")
						s += eps.debugLine("RAW DUMP", "-")
						s += eps.debugHeaderEx ("-")
						s += unicode(d) + "\n"
				
						s += eps.debugHeaderEx ("-")
					else:
						s += eps.debugHeaderEx ("!")
						s += eps.debugLine("Plugin Device Already Summarized", "+")
						s += eps.debugHeaderEx ("!")
				else:
					s += eps.debugHeaderEx ("!")
					s += eps.debugLine("!!!!!!!!!!!!!!! DEVICE DOES NOT EXIST IN INDIGO !!!!!!!!!!!!!!!", "+")
					s += eps.debugHeaderEx ("!")
				
			s += eps.debugHeaderEx ("-")
		
		
		s += eps.debugHeaderEx ("=")
		
		# Loop through all devices for this plugin and report
		s += eps.debugHeader ("PLUGIN DEVICES", "=")
		
		for dev in indigo.devices.iter(self.pluginId):
			s += eps.debugHeaderEx ("*")
			s += eps.debugLine(dev.name + ": " + str(dev.id) + " - " + dev.deviceTypeId, "*")
			s += eps.debugHeaderEx ("*")
			
			s += eps.debugHeaderEx ("-")
			s += eps.debugLine("PREFERENCES", "-")
			s += eps.debugHeaderEx ("-")
			
			for k, v in dev.pluginProps.iteritems():
				s += eps.debugLine(k + " = " + unicode(v), "-")
				
			s += eps.debugHeaderEx ("-")
			s += eps.debugLine("STATES", "-")
			s += eps.debugHeaderEx ("-")
			
			for k, v in dev.states.iteritems():
				s += eps.debugLine(k + " = " + unicode(v), "-")
				
			s += eps.debugHeaderEx ("-")
			
		s += eps.debugHeaderEx ("=")
		
		
		
		
		indigo.server.log(s)
			
	################################################################################
	# LEGACY MIGRATED ROUTINES
	################################################################################
		
	
	


	

	
