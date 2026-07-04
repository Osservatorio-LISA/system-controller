# ======================================================================================================================================= #
#                                               LISA MAIN CONTROLLER | Version 1.1.0                                                      #
#                                           Coordination hub for the LISA Observatory modules.                                            #
# ======================================================================================================================================= #
#                                                   Interaction with modules
# --------------------------------------------------------------------------------------------------------------------------------------- #
#  - sending commands : The controller sends requests to modules using http requests with RESTfull API system. (more in http_interface.py)
#  - receiving data   : Modules connects to an internal TCP server to send JSON status updates,
#                       NOTE: the server should provide each module with his IP and port in order to have less hard coded IPs and Ports.
#                       Each module must have a specific tcp_handler function (more in TCPServer.py and modules_handler folder)
#  - local sync       : A real-time copy of modules status is kept in a dictionary within global_state.py for quick access.
#                       (more in global_state.py)
#  - heartbeat        : A 'keep-alive' signal used to monitor system health and detect failures. (more in tcpHandler.py)
#                       
# --------------------------------------------------------------------------------------------------------------------------------------- #
#                                                       Commands Handling 
# --------------------------------------------------------------------------------------------------------------------------------------- #
# commands are obtained via en external interface (more in ext_interface.py) but elaboration is in a thread that waits for a command, 
# parses it and executes it (more in cmd_handler.py) the controller can differentiate two kind of commands.
#
# - Status Queries    : If a command asks for information we pull it directly from global_status.
# - Action            : if command requires an action, we send a request to a module and  immediately returns to listening mode.
#                       upon completion a module must send back an "ok" status along updated status in a JSON format. In case of an
#                       error a module specific error routine is called to handle the situation. 
# ======================================================================================================================================= #
__doc__ = "main"
__brief__ = "Coordination hub for the LISA Observatory modules"
__author__ = "Alessandro Maryni"

# built-in libraries
import threading
import logging
from os      import environ
# installed libraries
from flask import Flask
# custom libraries
import ext_interface
import global_state

from utility           import get_real_ip
from cmd_handler       import cmd_parser
from web_gui_interface import gui_bp
# module custom handler libraries
from modules_handlers.dome_handler import dome_tcp_handler

environ["FLASK_ENV"] = "production"
#flask is really verbose, this prints only error messages
flask_logger = logging.getLogger("werkzeug")
flask_logger.setLevel(logging.ERROR)
#setup of flask
app = Flask(__name__)
app.register_blueprint(gui_bp)

threading.Thread(target=ext_interface.wait_for_input, daemon=True).start() #terminal input daemon

# in src on Windows : .venv\Scripts\activate
# in src on Linux   : source .venv/bin/acrivate
# anywhere          : deactivate

# ======================================================================================== #
#                                           ENTRY_POINT                                    #
# ======================================================================================== #
if __name__ == "__main__":
    # print IP address of the machine
    global_state.set_IP("self", get_real_ip())
    global_state.set_port("self", 5000)
    print(f"SERVER IP : {global_state.get_IP('self')}") #debug

    
    # ----------------- TCP SERVER INITIALIZATIONS -----------------------
    print("\n======= INITIALIZING MODULES =======\n")
    # --- dome ---
    print("--- DOME ---\n")
    dome = dome_tcp_handler()
    dome.config_dome_tcp_socket()
    dome.start()
    dome.check()
    print("--- SLIT --- \n")
    print("--- LX200 --- \n")
    # ---------------- CMD_PARSING INITIALIZATION -----------------------
    print("\n======= INITIALIZING INPUT =======\n")
    input_thread = threading.Thread(target=cmd_parser, daemon=True)
    input_thread.start()
#    try:
#        while input_thread.is_alive():
#            input_thread.join(timeout=1.0)
#    except KeyboardInterrupt:
#        print("Shutdown requested via Ctrl+C")
#    
    #------------------ Web interface ------------------------------------
    #NOTE: app.run is blocking()
    print("\n======= INITIALIZING WEB INTERFACE =======\n")
    print(f"[ INFO ] WEB interface at http://{global_state.get_IP('self')}:{global_state.get_port("self")}/")
    app.run(host=global_state.get_IP("self"), port=global_state.get_port("self"), debug=False, use_reloader=False)

    print("[ INFO ] Cleaning up and exiting...")

