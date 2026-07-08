__doc__    = "tcp_handler"
__brief__  = "Base class to help tcp interaction with modules                " \
             "of this base class each module should implement at least the  "  \
             "three abstract method                                         "
__author__ = "Alessandro Maryni"

from time       import time, sleep
from abc        import ABC, abstractmethod
from threading  import Thread

from    TcpServer      import TcpServer
from    utility        import get_json_data
from    ext_interface  import send_response
import  global_state 

MAX_HEARTBEAT_TIME = 30
#============================================================================== #
#                           BASE TCP HANDLER CLASS                              #
#============================================================================== #
# This class was created to help creating the tcp handler function for each module.
# It handles tcp connection, conversion from raw tcp data to json format and
# heartbeat protocol (see below).
# Because this is an abstract class the three following methods MUST be defined:
# 
#
#  - handle_tcp_data(self, jdata : dict)
#       what do i do with the data?
#  - handle_tcp_error(self, jdata : dict)
#       how do i handle errors in the module?
#  - handle_heartbeat_timeout(self)
#       what do i do if the module does not send heartbeat?
# 
#  
# --------------------------------HEARTBEAT------------------------------------ #
# The heartbeat protocol is a diagnostic protocol that checks if a module is 'alive'.
# If any tcp message is exchanged within MAX_HEARTBEAT_TIME we consider it as an 
# "alive" signal ('piggybacking'), otherwise 'handle_heartbeat_timeout()' function
# is called. 
# This approach allows for the implementation of heartbeat protocol in two ways:
#
# - polling:
#   in 'handle_heartbeat_timeout()' we send a 'are you alive?' http request and 
#   wait for a http status response (timeout for http is currently at 5 seconds.)
#   This approach is useful if the module does not have many network operations or if 
#   it does not have critical tasks that could be compromised by many http requests.
#   NOTE: Race condition could happen if an error message is sent just after the 
#   heartbeat http request is sent by server: we'll receive 2 error message 
#   one after the other. 
#
# - module-driven:
#   the module is responsible for sending a tcp message periodically, if one is not
#   sent within MAX_HEARTBEAT_TIME in 'handle_heartbeat_timeout()' we could still try 
#   either to send an http request (in order to test once more if the system is alive)
#   or to shut off the system.
#   This approach is preferable if too many http requests could compromise the module, 
#   (i.e. if module is single-core with critical tasks like dome module)
# ----------------------------------------------------------------------------- #

class BaseTcpModuleHandler(ABC):
    """Abstract base class to handle tcp connection """
    def __init__(self, module_name : str):
        self.name               = module_name
        self.server             = TcpServer()
        # heartbeat functionalities
        self.last_heartbeat     = time()
        self.heartbeat_watchdog = MAX_HEARTBEAT_TIME
    #-----------------------------------------------------------------------
    def start(self) -> bool: 
        if not self.server.StartServer(serverPort=global_state.get_port(self.name)):
            return False
        if not self.server.StartConnectionListener():
            return False
        send_response(f"[ INFO ] {self.name} server started at port {global_state.get_port(self.name)}")
        Thread(target=self.handle_tcp_connection, daemon=True).start()  # starting dome_tcp_handler function as a daemon thread
    #-----------------------------------------------------------------------
    def handle_tcp_connection(self):
        """listen for data from module"""
        while True:
            # get raw tcp data
            raw_data = self.server.GetData()
            # if data is received reset heartbeat
            if raw_data is not None:
                self.reset_heartbeat()
            # heartbeat watchdog
            if time() - self.last_heartbeat > self.heartbeat_watchdog:
                self.handle_heartbeat_timeout()
                self.reset_heartbeat()
            # no data is received
            if raw_data is None:
                sleep(.1)
                continue 
            
            jdata = get_json_data(raw_data)
            if jdata is None:
                send_response("jdata is None")
                self.server.tcpBuffer.ClearData()
                continue
            if jdata["status"] == "ok":
                self.handle_tcp_data(jdata)
                #if we get a message with status 'ok' there is no reason to send a heartbeat
                #NOTE: response to heartbeat will reset heartbeat timer but it's ok I guess
                self.reset_heartbeat()
            else:
                self.handle_tcp_error(jdata)
    #-----------------------------------------------------------------------
    def reset_heartbeat(self):
        """reset heartbeat time, since time() return in seconds it's ok to call it multiple times"""
        self.last_heartbeat = time()
    #-----------------------------------------------------------------------
    @abstractmethod
    def handle_tcp_data(self, jdata : dict):
        """handle json data from module"""
        # example of handle_tcp_data:
        # NOTE: jdata is valid if it has "status" : "ok" !!
        #
        # for key in jdata:
        #   if global_state.is_key_in_module(module=self.name, key=key):
        #       global_state.set(module=self.name, key=key, new_value=jdata[key])
        #
        #
        # here we just update global state
        raise NotImplementedError
    #-----------------------------------------------------------------------
    @abstractmethod
    def handle_tcp_error(self, jdata : dict):
        """handle json data in case of an error"""
        # example of handle_tcp_error:
        # NOTE: jdata is valid if it has NOT "status" : "ok" !!
        #
        # getting error and reason from j_data
        # reason = j_data.get(DOME_ERROR_REASON, "No reason provided by module")
        # code   = j_data.get(DOME_ERROR_CODE,   "No code provided by module")
        # global_state.set(module="dome", key="status", new_value="error")
        # ...
        raise NotImplementedError
    #-----------------------------------------------------------------------
    @abstractmethod
    def handle_heartbeat_timeout(self):
        """handle heartbeat timeout """
        # example of handle_heartbeat_timeout:
        # 
        # ok, body = http_fetch_request(global_state.IP[self.name], "GET", module/diagnostic/heartbeat)
        #   
        # if not ok:
        #   if body["error"] == "timeout":
        #       ext_interface.send_response(f"[ ERROR ] module {self.name} died, not responding to heartbeat")
        #       close_system()
        #   else:      
        #       ext_interface.send_response(f"[ WARNING ] module {self.name} active but heartbeat http failed {body["error"]}") 
        #       //here call specific module error routine
        #
        raise NotImplementedError
