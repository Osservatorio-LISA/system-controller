__doc__ = "http_interface"
__brief__ = "used to make safe and simple http requests to an http server using RESTfull API system"
__author__ = "Alessandro Maryni"

import http.client
from urllib.parse import urlencode
from socket import gaierror #invalid IP / server non existing error
import json

# ===================================================== http_fetch =================================================== #
#                                           execute a BLOCKING http fetch to a module                                  #
# ==================================================================================================================== #
# example of usage:
# response_code, response_body = http_fetch_request("192.168.xxx.xxx", "GET", "some_url", {"name":"value", "name_2":"value_2"}, {"body_arg" : "value"})
#
# -------------------------------------------------------------------------------------------------------------------- #
def http_fetch_request(http_host : str, http_method : str, http_url : str, params : dict = {}, body : dict = {}) -> tuple[bool, dict]:
    "" "make an http request """
    server = None
    try:
        
        # handle body if present
        headers , body_bytes = _http_parse_body(body=body)
        #handle query params if present
        path_with_params = _http_parse_query_param(http_path=http_url, http_params=params)

        # ------- set up connection ------- #
        server = http.client.HTTPConnection(http_host, timeout=5)
        print(f"sending: {path_with_params}")
        server.request(http_method, path_with_params, headers=headers , body=body_bytes)

        response = server.getresponse()
        status = response.status
        data   = response.read().decode()

        if 200 <= status < 300: # there is a class of informal response code "1xx" but we ignore it
            print(f"Success: {http_method} on {http_url} (Status: {status})")
            return True, {"status" : status, "data": data}
        else:
            print(f"Server failed: {http_method} on {http_url} (Status: {status})")
            return False, {"error": "status_fail", "status" : status, "data" : data }

    except TimeoutError:
        return False, {"error" : "timeout" }
    
    except gaierror:
        return False, {"error" : "invalid IP"}

    except http.client.HTTPException:
        return False, {"error" : "invalid http protocol"}
    
    except Exception as e:
        return False, {"error" : "unexpected" , "details": str(e) }
    
    finally:
        if server:
            server.close()


# ===================================================== _http_parse_body ============================================= #
#                                           parse body in http_fetch_request                                           #
# ==================================================================================================================== #
#  returns headers as a dict and body in bytes
#  example of usage:
#   headers, parsed_body = _http_parse_body({"message":""hello world"});
#
# -------------------------------------------------------------------------------------------------------------------- #
def _http_parse_body(body : dict ) -> tuple[dict , bytes | None]:
    body_bytes = None
    headers = {}
    if body:
        try:
            body_bytes = json.dumps(body).encode('utf-8')
            # aggiungiamo gli headers
            # dichiariamo che stiamo inviando un dato in formato json
            # dichiariamo quanto è lungo il body
            headers = {
                'Content-Type': 'application/json',
                'Content-Length': str(len(body_bytes))
            }
        except Exception as e:
            print(f"Unexpected error in _http_parse_body : {e}")
    
    return headers, body_bytes

# ================================================= _http_parse_query_param ========================================== #
#                                           parse query params in http_fetch_request                                   #
# ==================================================================================================================== #
#  encode http_params in http_path with query params syntax
#  example of usage:
#     path_with_params = _http_parse_query_param("/your/url/here", {"message":"hello world"})
#  will return:
#     /your/url/here?message=hello%20world
#
# -------------------------------------------------------------------------------------------------------------------- #
def _http_parse_query_param(http_path : str , http_params : dict) -> str:
    # handle query params ex: http:/url?name=value&name_2=value_2
    #                                  ^          ^
    #                               start query  concatenation of queries
    path_with_params = http_path
    if http_params:
        param_string = urlencode(http_params)
        separator = "&" if "?" in http_path else "?"
        path_with_params = f"{http_path}{separator}{param_string}"
    
    return path_with_params
