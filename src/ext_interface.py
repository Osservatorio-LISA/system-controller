__doc__    = "ext_interface"
__brief__  = "for now a rudimentary way of obtaining command via terminal, next should be a remote way"
__author__ = "Alessandro Maryni"

import queue
from time import sleep
from json import dumps
global_buffer   = queue.Queue( maxsize=10 ) #Queue is thread safe so it should be ok
response_buffer = queue.Queue( maxsize=20 )

def wait_for_input() -> None:
    while True:
        sleep(.5)
        cmd = input(" >> Type 'EXIT' to end or 'HELP' for info: \n")
        if cmd == 'EXIT':
            global_buffer.put("EXIT")
            break
        global_buffer.put(cmd)
   
def get_cmd() -> str | None: 
    cmd = global_buffer.get()
    return cmd 

def put_cmd( cmd : str ) -> None:
    global_buffer.put(cmd)
    return

def send_response( response : str | dict ) -> None:
    if isinstance(response, dict):
        response = dumps(response)
    response_buffer.put(response)
    print(f"response: '{response}'")
    return

def get_last_response() -> str:
    return response_buffer.get()

def get_last_response_noWait() -> str | None:
    try:
        return response_buffer.get_nowait()
    except queue.Empty:
        return None

def get_response_buff() -> list[str]:
    results = []
    while True:
        try:
            results.append(response_buffer.get_nowait())
        except queue.Empty:
            break
    return results