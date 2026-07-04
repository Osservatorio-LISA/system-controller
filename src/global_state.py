__doc__ = "global_state"
__brief__ = "A real-time copy of modules status, store in a dictionary format: " \
    ' "module_1":{                  ' \
    '       "key_1": "value_1"      ' \
    '       "key_2": "value_2",     ' \
    '  },                           '
__author__ = "Alessandro Maryni"



import threading
import copy
from ipaddress import ip_address

from ext_interface import send_response

from config import *
from modules_handlers.dome_handler import *
from modules_handlers.slit_handler import *
#--------------------------------------------------------------------------------------------------#
#                                       GLOBAL STATE                                               #
#--------------------------------------------------------------------------------------------------#

MODULES = {
    # All values are in config.py
    "self":{
        "IP"    : "",
        "port"  : 5000 #for flask web server
    },
    "dome":{
        "IP"    : DOME_IP, 
        "port"  : DOME_PORT
    },
    "slit":{
        "IP"    : SLIT_IP, 
        "port"  : SLIT_PORT 
    },
    "telescope" : {
        "IP"    : TELESCOPE_IP,
        "port"  : TELESCOPE_PORT
    },
    #add all modules
}

GLOBAL_STATE = {
    "dome" : {
        # NOTE: offset_with_telescope is the hw offset between the 0 of the telescope and the 0 of dome, for now it is set to 0 in DEGREES
        # if not 0 should not be touched
        "offset_with_telescope"                  : 0,
        #Keys are defined in modules_handlers/dome_handler
        "status"                                 : "offline",
        DOME_CURRENT_POSITION_TKS                : 0,
        DOME_CURRENT_POSITION_DEG                : 0,
        DOME_FULL_ROTATION_TKS                   : 0,
        DOME_TARGET_POSITION_TKS                 : 0,
        DOME_TARGET_POSITION_DEG                 : 0,
        DOME_TIME_SINCE_MOVE                     : 0,
        DOME_DIRECTION                           : 0,
        DOME_SPINNING                            : False,
        DOME_FIRMWARE_VERSION                    : "Unknown",
    },
    "slit" : {
        "status"                : "offline",
        SLIT_IS_OPEN            : False,
        #add all keys
    },
    "telescope" : {
        "status"     : "offline",
        #add all keys
    }
    #add all modules
}

STATE_LOCKS = {
    "self"      : threading.Lock(),
    "dome"      : threading.Lock(),
    "slit"      : threading.Lock(),
    "telescope" : threading.Lock(),
    #add all modules
}

#--------------------------------------------------------------------------------------------------#
#                                         HELPING FUNCTIONS                                        #
#--------------------------------------------------------------------------------------------------#

def print_all() -> None:
    """
    prints all modules with their keys and values
    """
    response = "\n--- Current Global State ---"
    for module, state in GLOBAL_STATE.items():
        response += f"\nmodule: {module}"
        for key, value in state.items():
            response += f"  {key}: {value}\n"
    response += "\n---------------------------"
    send_response(response=response)

def print_all_keys_of_a_module( module : str):
    """
    prints all keys and values of a certain module
    """
    if not is_module_present(module):
        return
    print(f"\nmodule: {module}")
    for key , value in GLOBAL_STATE[module].items():
        print(f"  {key}: {value}")
        
def set_IP( module: str , new_ip : str) -> bool:
    """
    set IP address of a particular module
    """
    if module in MODULES:
        try:
            ip_address(new_ip)
        except ValueError:
            return False
        
        with STATE_LOCKS[module]:
            MODULES[module]["IP"] = new_ip
        return True

def get_IP( module : str ) -> str :
    """
    get IP address of a particular module
    """
    if module in MODULES and "IP" in MODULES[module]:
        with STATE_LOCKS[module]:
            ip =  MODULES[module]["IP"]
        return ip
    else:
        return ""
   
def set_port( module : str, new_port : int ) -> bool:
    """
    set port of a particular module
    """
    if module in MODULES:
        
        if new_port <= 0:
            return False
        
        with STATE_LOCKS[module]:
            MODULES[module]["port"] = new_port
        return True
    
def get_port( module : str ) -> int :
    """
    get port of a particular module
    """
    if module in MODULES and "port" in MODULES[module]:
        return MODULES[module]["port"]
    else:
        return -1


def set( module :str , key : str , new_value ) -> bool:
    """
    set a value to a particular key in a module.
    it also check if the key and the module exists.
    """
    if is_key_in_module(module= module, key= key):
        #print(f"{module} -> {key} = {new_value}") #debug
        with STATE_LOCKS[module]:
            GLOBAL_STATE[module][key] = new_value
            return True
    else:
        return False
    

def get( module : str , key : str ) -> str :
    """
    get a value of a particular key in a module.
    it also check if the key and the module exists.
    """
    if is_key_in_module(module= module, key= key):
        with STATE_LOCKS[module]:
            rv = GLOBAL_STATE[module][key]
        return rv
    else:
        return ""
    
def get_all_module_keys(module: str) -> dict | None:
    """
    gets all keys and values of a module as a dict.
    it also check if the module exists.
    """
    if is_module_present(module= module):
        with STATE_LOCKS[module]:
            rv = copy.deepcopy(GLOBAL_STATE[module])
        return rv
    else:
        return None

def is_module_present( module : str ) -> bool:
    """
    check if a particular module is present in GLOBAL_STATE data
    """
    if module in GLOBAL_STATE:
        return True
    else:
        return False
    
def is_key_in_module( module : str , key : str ) -> bool:
    """
    check if a particular key is present in a module.
    it also check if module is present in GLOBAL_STATE.
    """
    if not is_module_present(module):
        return False
    rv = key in GLOBAL_STATE[module]
    return rv
