# ///////////////////////////////////////////////////////////////
#
#		   Class that implements a shared (thread-safe) memory area 
#		   between multiple threads
#
# ///////////////////////////////////////////////////////////////

from threading import Thread, Lock

#==========================================================================

class SharedTCPbuffer:
	"""Provides a shared, thread-safe memory area 
	   where TCP data are received from remote Server
		 Implements a producer/consumer pattern

		 Also provides a comm device (via stopFlag) to exit listener thread
	"""

	#-----------------------------------------------------------------------
	# Funzione di Inizializzazione
	def __init__(self):
		"""Uses Lock object to ensure synchronization"""

		self.lock			= Lock()	# Synchro device
		self.localData		= bytes()	# data buffer
		self.dataPresent	= False		# informs consumer thread that new data have arrived
		self.stopFlag		= False		# instructs listener thread to exit

	#------------------------------------------------------------------------
	# Erases any memory contents
	def ClearData(self):
		"""Erases any memory contents"""
		with self.lock:
			self.localData = bytes()
			self.dataPresent= False

	#------------------------------------------------------------------------
	# Access function to internal flag
	def IsDataPresent(self):
		"""Thread-safe access to status variable"""
		retVal = False
		with self.lock:
			retVal = self.dataPresent
		return retVal 

	#------------------------------------------------------------------------
	# Access function to internal flag
	def GetStopFlag(self):
		"""Thread-safe access to status variable"""
		with self.lock:
			retVal = self.stopFlag
		return retVal

	#------------------------------------------------------------------------
	# Access function to internal flag
	def SetStopFlag(self, value):
		"""Thread-safe access to status variable"""
		with self.lock:
			self.stopFlag = value

	#------------------------------------------------------------------------
	# funzione ad uso del consumer
	def Read(self):
		"""Implements thread-safe access to shared contents"""
		
		retData = bytes()
		with self.lock:
			retData = self.localData
			self.localData = bytes()
			self.dataPresent= False
		return retData

	#------------------------------------------------------------------------
	# Funzione ad uso del producer
	def Write(self, inputData):
		"""Implements thread-safe update of shared contents"""
		
		with self.lock:
			self.localData		= self.localData + inputData
			self.dataPresent	= True

