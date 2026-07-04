from baseTcpHandler import BaseTcpModuleHandler
from time           import sleep, time
from re             import match


from http_interface import http_fetch_request
import global_state
import ext_interface
import json


# ================================== DOME GLOBAL STATE KEYS ================================== #
# status & error keys#
DOME_STATUS 			        = "status"
DOME_ERROR_REASON 		    	= "reason"
DOME_ERROR_CODE			 		= "code"
# dome status #
DOME_CURRENT_POSITION_TKS       = "currentPosInTicks"
DOME_CURRENT_POSITION_DEG       = "currentPosInDegrees"
DOME_FULL_ROTATION_TKS          = "numberOfTicksPerFullRotation"
DOME_TARGET_POSITION_TKS        = "targetPosInTicks"
DOME_TARGET_POSITION_DEG        = "targetPosInDegrees"
DOME_TIME_SINCE_MOVE			= "timeSinceLastMove"
DOME_DIRECTION                  = "domeDirection"
DOME_SPINNING		            = "isDomeSpinning"

# dome micro controller status & info #
DOME_FIRMWARE_VERSION 		    = "firmware"
DOME_UPTIME				        = "uptime"
DOME_ESP_MODEL				 	= "esp-model"
DOME_ESP_CORE_COUNT		 		= "esp-core-counts"

DOME_INFO = [DOME_FIRMWARE_VERSION, DOME_UPTIME, DOME_ESP_MODEL, DOME_ESP_CORE_COUNT]
# ============================================================================================ #

DOME_EXPECTED_MAJOR_FIRMWARE_VERSION = 4 # 4.x.x MUST BE AN INTEGER

class dome_tcp_handler(BaseTcpModuleHandler):
    #-----------------------------------------------------------------------
    def __init__(self):
        """call constructor of BaseTcpModuleHandler"""
        super().__init__("dome")
    #-----------------------------------------------------------------------
    def check(self):
        # we first ask dome to send all it's status
        ok, why = http_fetch_request(global_state.get_IP("dome"), "GET", "/status")
        if(not ok):
            ext_interface.send_response(f"[ ERROR ] could not get status : {why["error"]}")
        
        ok, why = http_fetch_request(global_state.get_IP("dome"), "GET", "/status/system")
        if(not ok):
            ext_interface.send_response(f"[ ERROR ] could not get dome system information: {why["error"]}")
            return

        timeout = 5.0  # secondi
        start_time = time()
        while global_state.get("dome", DOME_FIRMWARE_VERSION) == "Unknown":
            if time() - start_time > timeout:
                ext_interface.send_response("[ ERROR ] Timeout: could not get status version")
                return  # Interrompiamo il setup per evitare crash successivi
                
        sleep(0.1)  # Rilascia la CPU per 100ms
        version_pattern = rf"^{DOME_EXPECTED_MAJOR_FIRMWARE_VERSION}\.\d+\.\d+"
        current_version = global_state.get("dome", DOME_FIRMWARE_VERSION)
        if not match(version_pattern, current_version):
            ext_interface.send_response(f"[ WARNING ] Dome version is {current_version}, expected {DOME_EXPECTED_MAJOR_FIRMWARE_VERSION}.x.x, some calls could fail")

    #-----------------------------------------------------------------------
    def handle_tcp_data(self, j_data : dict):
        """handle json data from dome module"""
        #if status is ok, update global status
        response = ""
        for k in j_data:
            if global_state.is_key_in_module(module=self.name, key=k):
                global_state.set(module="dome", key=k, new_value=j_data[k])
            elif  k in DOME_INFO:
                response = response + "DOME SYSTEM DATA: \n"
                response = response + f"{k} : {j_data[k]}\n"
        if response:
            ext_interface.send_response(response)
    #-----------------------------------------------------------------------
    def handle_tcp_error(self, j_data : dict):
        """Handle errors from dome module"""

        # getting error and reason from j_data
        reason = j_data.get(DOME_ERROR_REASON, "No reason provided by module")
        code   = j_data.get(DOME_ERROR_CODE,   "No code provided by module")
        global_state.set(module="dome", key="status", new_value="error")

        if code == -1: # dome has crashed

            ext_interface.send_response(f"[ CRITICAL ERROR ] Dome has crashed : {reason},\nDome is now in standby until 'ok' to homing is given")
            ext_interface.send_response("[ INFO ] can dome return to home position ? [Y/N]")
            ok_to_home = None
            while True:
                # NOTE: ext.get print ("HELP to help or EXIT to exit") while here we want Y/N
                ext_interface.put_cmd("YIELD")
                ok_to_home = ext_interface.get_cmd().upper()
                if ok_to_home == 'Y' or ok_to_home == 'N':
                    ext_interface.send_response(f"[ INFO ] got '{ok_to_home}'  ")
                    break

            homing = "no"
            target_pos_recovery = None

            if ok_to_home and ok_to_home == "Y":
                homing = "ok"
                target_pos_recovery = global_state.get("dome", DOME_TARGET_POSITION_DEG)
            response = {
                DOME_ERROR_REASON : "recovery",
                "homing" : homing,
                DOME_TARGET_POSITION_DEG :  target_pos_recovery if target_pos_recovery != -1 else 0
            }
            self.server.SendData(json.dumps(response))
            sleep(1)
            return

        error_msg = f"error in Dome\nstatus = {j_data['status']}\nreason = {reason}\ncode={code}\n\n"
        ext_interface.send_response(error_msg)

        return
    #-----------------------------------------------------------------------
    def handle_heartbeat_timeout(self):
        """handle heartbeat timeout """
        ok , body  = http_fetch_request(global_state.get_IP("dome"),"GET","/diagnostic/heartbeat")
        if ok:
            self.reset_heartbeat()
            return
        elif("status" in body and body["status"] == 449):
            ext_interface.send_response("[WARNING] dome tcp socket not configured!")
            if not self.config_dome_tcp_socket():
                global_state.set("dome", DOME_STATUS, "error")
        else:
            ext_interface.send_response("[ ERROR ] dome didn't respond to heartbeat")
            global_state.set("dome", DOME_STATUS, "error")
        self.reset_heartbeat()
    #-----------------------------------------------------------------------
    def config_dome_tcp_socket(self) -> bool:
        """configure dome's tcp socket"""
        from utility import get_real_ip
        ok, body  = http_fetch_request(global_state.get_IP("dome"), "PUT", "/network/tcp-socket", {"IP": get_real_ip(), "port" : global_state.get_port("dome")})
            
        if(not ok): 
            ext_interface.send_response(f"[ WARNING ] could not set dome tcp socket : {body}")
            return False
        return True


# =================================================================================================================== #
#                                                cmd MOVE handler                                                     #
# =================================================================================================================== #
# handle a MOVE command, for dome you must specify 3 arguments: target position, unit, if position is absolute or relative
# syntax is: "dome":dict
def dome_handle_MOVE_command(params : list[str]) -> tuple[bool , str]:
    if not params:
        return False, "[ ERROR ] no param in MOVE dome"
    
    if len(params) > 3:
        return False, "[ ERROR ] too many parameters\n MOVE dome:pos(,mode)(,unit) (...)=optional"
    #position is always at the start
    try:
        position = int(params[0])
    except ValueError:
        return False, "[ ERROR ] invalid MOVE syntax: fist argument of MOVE dome: must be the position as a Int"
    
    #getting optional params
    
    #default args
    move_mode = "abs"
    unit      = "deg"

    #checking for syntax mistakes
    TOKEN_MODE = {
        "abs": "abs", "absolute": "abs", "assoluta": "abs",
        "rel": "rel", "relative": "rel", "relativa": "rel"
    }
    TOKEN_UNIT = {
        "deg": "deg", "degrees": "deg", "gradi": "deg",
        "tks": "tks", "ticks": "tks",
    }

    #parsing the params
    for param in params[1:]:
        token = param.lower()
        
        if token in TOKEN_MODE:
            move_mode = TOKEN_MODE[token]
        elif token in TOKEN_UNIT:
            unit = TOKEN_UNIT[token]
        else:
            return False, f"[ ERROR ]: param '{param}' not recognized. Use 'abs'/'rel' or 'deg'/'tks'."

    query_params = {"value":position,"unit":unit,"mode":move_mode}

    ok, body = http_fetch_request(global_state.get_IP("dome"), "PUT", "/position", params=query_params)
    return ok, body

# =================================================================================================================== #
#                                                cmd Home handler                                                     #
# =================================================================================================================== #
# handle homing operation
def dome_handle_HOME_command() -> bool:
    ok, _ = http_fetch_request(global_state.get_IP("dome"), "POST", "/operations/homing")
    return ok


    