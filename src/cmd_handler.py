__doc__     = "cmd_handler"
__brief__   = "gets commands from external interface, parse it and execute is directly or via 'cmd_execute_[command name]' "
__author__  = "Alessandro Maryni"
import ext_interface
import global_state
from http_interface import http_fetch_request
from time           import sleep

from modules_handlers.dome_handler import *

# ================================================== cmd_parser loop ==================================================#
#                              main cmd_loop must be initialized within a daemon thread                                #
# ==================================================================================================================== #
def cmd_parser():
    while True:
        try:
            cmd = ext_interface.get_cmd()
            print(f"DEBUG: {cmd}")
            if cmd == None:
                continue
            elif cmd == "YIELD":
                print("[ INFO ] cmd yield")
                continue
            # ----- emergency stop ------ #
            elif cmd.startswith("STOP"):
                cmd_execute_stop()
                continue
            # ----- debug command ----- #
            elif cmd.startswith("ECHO "):
                echo = cmd.removeprefix("ECHO ")
                ext_interface.send_response(echo)
                continue
            # ----- global status commands ----- #
            elif cmd == "STATUS":
                global_state.print_all()
            elif cmd.startswith("GET "):
                cmd_execute_get(cmd)
                continue
            # ----- modules commands----- #
            elif cmd.startswith("GOTO "):
                cmd_execute_goto(cmd)
                continue
            elif cmd.startswith("MOVE "):
                cmd_execute_move(cmd)
                continue
            # ----- help command ----- #
            elif cmd == "HELP":
                cmd_execute_help()
                continue 
            # ----- exit command ----- #
            elif cmd == "EXIT":
                # TODO: send to all modules a shut-off message
                # dome_handle_HOME_command();
                #kill web interface
                from main import server_ip
                try :
                    ok, body = http_fetch_request(f"{server_ip}:5000", "POST", "/shutdown", {})
                    if not ok:
                        print(f"Impossibile arrestare Flask via HTTP: {body}")
                except Exception as e:
                    print(f"Impossibile arrestare Flask via HTTP: {e}")

                break
            else:
                ext_interface.send_response(f"[ WARNING ] invalid command: {cmd}")
                sleep(3)
        except Exception as e:
            print( f"ERROR: {e}" )

# ============================================ single cmd_execute functions ===========================================#
#                                       a set of functions that execute a given command                                #
# ==================================================================================================================== #

# --------------------------------- CAN OPEN command [INTERNAL][SYSTEM] ---------------------------------------------- #
# checks all time and meteo condition to open the system                                                               #
# ---------------------------------------------------------------------------------------------------------------------#
# TODO: i do not know if this function should be in this file
def can_system_open() -> bool: 
    # TODO: add all the check here: time, meteo, ?
    return True

# ---------------------------------------------- STOP command [MODULES] ---------------------------------------------- #
#  stops all modules from running                                                                                      #
# ---------------------------------------------------------------------------------------------------------------------#
def cmd_execute_stop() -> None:
    ok, _ = http_fetch_request(global_state.get_IP("dome"), "PUT", "/operations/emergency-stop")
    if(not ok):
        ext_interface.send_response("[ ERROR ] could not stop DOME module")


# ----------------------------------------------- GET command [STATUS] ----------------------------------------------- #
#  GET is the command to obtain some of the modules status, in case not all global state is needed                     #
#  Syntax is -> GET module_1:Key_1,key_2,...,key_n module2:Key_1,...,Key_n  .... module_n:....                         #
#  Example  -> GET dome:status,currentPositionInTicks,targetPositionInTicks slit:status,isOpen                         #
# ---------------------------------------------------------------------------------------------------------------------#
def cmd_execute_get(cmd : str) -> None:
    response = {}
    raw_data = cmd.removeprefix("GET ")
    #splitting command in all "module_i:Key_1,...,Key_n"
    blocks = raw_data.split()
    for block in blocks:
        if ":" in block:
            #for each block we get the module name and all the keys
            module_name,key_str = block.split(":", 1)
            #check if module exists in the state
            if global_state.is_module_present(module_name):
                response.setdefault(module_name, {})
                #getting all the keys
                keys = key_str.split(",")
                if "all" in keys:
                    keys = global_state.get_all_module_keys(module=module_name)
                    #check if module has any keys
                    if keys is None:
                        print(f"[ WARNING ] {module_name} has no keys ")
                        continue
                    #iterating and adding key and value to response
                    for Key , Value in keys.items():
                        response[module_name][Key] = Value
                    continue
                else:
                    for Key in keys:
                        #updating response with all values
                        response[module_name][Key] = global_state.get(module=module_name, key=Key)
        else:
            response["error"] = "no ':' char in command"
    if response:
        #finally we send response back
        ext_interface.send_response(response)

# ---------------------------------------------- GOTO command [MODULES] ---------------------------------------------- #
#  GOTO is the command to reach a certain position in horizontal_angle and vertical_angle                              #
#  Syntax is -> GOTO horizontal_angle vertical_angle                                                                   #
#  Example   -> GOTO 120 39                                                                                            #
#  TODO: it would be cool if we could evaluate astronomical angle, not relative angle                                  #
#        because we do not know reference point: goto 120 39 with respect to what angle?                               #
# ---------------------------------------------------------------------------------------------------------------------#
def cmd_execute_goto(cmd : str) -> None:
    response = ""
    #getting the two angles
    blocks = cmd.removeprefix("GOTO ").split()
    # ============ Control on arguments ================== #
    # 1. number of arguments
    if len(blocks) != 2:
        response = "[ ERROR ] invalid goto command: invalid numbers of arguments - GOTO horizontal_angle vertical_angle"
        ext_interface.send_response(response)
        return
    
    horizontal_angle = None
    vertical_angle = None
    try:
        #2. values of arguments 
        horizontal_angle    = int(blocks[0])
        vertical_angle      = int(blocks[1])
    except ValueError:
        ext_interface.send_response("[ ERROR ] invalid goto command: Angles must be integers")
        return
    if 0 <= horizontal_angle <= 360 and 0 <= vertical_angle <= 180:
        # ============ Executing command  ================== #
        #1. rotate the dome to horizontal_angle
        true_angle = horizontal_angle + int(global_state.get("dome", "offset_with_telescope"))
        ok , _ = http_fetch_request(global_state.get_IP("dome"),"PUT","/position", {"value":true_angle} )
        if(not ok):
            print("dome Http request failed")
            response = "[ ERROR ] http_failed in dome GOTO"

        #TODO 2. rotate telescope to horizontal_angle and vertical_angle
        else :
            response = "ok"
    else:
        response = "horizontal_angle or vertical_angle are not valid angles"
    ext_interface.send_response(response)

# ---------------------------------------------- MOVE command [MODULES] ---------------------------------------------- #
#  MOVE command allows to send specific position commands to some modules                                              #
#  Syntax is -> MOVE [module]:<pos1,pos2,(param,param)> [module]:...                                                   #
#  Example   -> MOVE "dome":45,"ticks","absolute" "telescope":45,12                                                    #
#  TODO: it would be cool if we could evaluate astronomical angle, not relative angle                                  #
#        because we do not know reference point: goto 120 39 with respect to what angle?                               #
# ---------------------------------------------------------------------------------------------------------------------#
def cmd_execute_move(cmd : str) -> None:
    response = ""
    raw_data = cmd.removeprefix("MOVE ")
    blocks = raw_data.split()
    for block in blocks:
        if ":" in block:
            #for each block we get the module name and all the params
            module_name,param_str = block.split(":", 1)
            #check if module exists in the state
            if global_state.is_module_present(module_name):
                #getting all the params
                Params = param_str.split(",")
                if module_name == "dome":
                    #in modules_handler/dome
                    ok , err_msg = dome_handle_MOVE_command(params=Params)
                    if not ok:
                        response += f"[ ERROR ] in dome_handle_MOVE_command : {err_msg}"
                else:
                    response += f"[ ERROR ] {module_name} is still in development"
            else:
                response += f"[ ERROR ] {module_name} is not a valid module"
    if response:
        #finally we send response back
        ext_interface.send_response(response)

# ------------------------------------- HELP command [INTERNAL][SYSTEM] ---------------------------------------------- #
# print list of commands with instruction                                                                              #
# ---------------------------------------------------------------------------------------------------------------------#
def cmd_execute_help() -> None:
    response = "\n\n===========LIST OF COMMANDS=========== \n"
    response += "HELP    - \n    prints this message\n"
    response += "STATUS  - \n    prints to terminal full status\n"
    response += "GET     [module]:<Key_1,...,Key_n> [module]:all\n    print only selected status Keys or all module Keys\n"
    response += "MOVE    [module]:<pos1,pos2> [module]:...\n    like GOTO but for specific modules\n"
    response += "GOTO    [horizontal_angle] [vertical_angle]\n    make system goto position\n"
    response += "STOP    - \n    stops all modules from moving\n"
    response += "ECHO    [string]\n    print [string] to terminal\n"   
    response += "EXIT    - \n    close program on LISA Raspberry Pi\n"
    response += "=========================================\n" 
    ext_interface.send_response(response)
    