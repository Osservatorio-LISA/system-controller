import json

# time definition
FIVE_MINUTES = 300
TEN_MINUTES  = 600

# utility function that finds a json object in a string and returns it.
def get_json_data(raw_data : str | bytes | memoryview):
    """ utility function that finds and extract json in a string """
    # converting raw data in string
    try:
        if isinstance(raw_data, bytes | bytearray):
            raw_data = raw_data.decode('utf-8')
        elif isinstance(raw_data, memoryview):
            raw_data = raw_data.tobytes().decode('utf-8')
    except Exception as e:
        print(f"Unexpected error in 'get_json_data' : {e}")
    
    if not isinstance(raw_data, str):
        print("Error in 'get_json_data' : could not convert raw_data to string")
        return None

    try:
        # finding JSON object { ... }
        start = raw_data.rfind('{') #if there are two message we just get the last one
        end = raw_data.rfind('}')

        if start == -1 or end == -1:
            print("Error in 'get_json_data' : '{' or '}' not present in raw_data")
            return None
        jStr = raw_data[start : end + 1]
        # return json object
        return json.loads(jStr)
    except Exception as e:
        print(f"Error in json string {raw_data} : {e}")
        return None
    
# =============================================================================================== #
#                               Angle conversions   #    NOT USED AS FOR NOW                      #
# =============================================================================================== #

    
def rightAscensionAngle2Degrees(hours : float, minutes : float, seconds : float) -> float :
    """conversion from hours, minutes, seconds to degrees"""
    return (hours + minutes/60 + seconds/3600) * 15

def declinationAngle2Degrees(arc_degrees: float, arc_minutes: float, arc_seconds: float) -> float :
    """conversion from arc_degrees, arc minutes and arc seconds to degrees"""
    sign = -1 if arc_degrees < 0 else 1
    return arc_degrees + (sign * arc_minutes/60) + (sign * arc_seconds/3600) 

def Degrees2RightAscensionAngle(degrees : float ) -> tuple [int,  int , float] :
    """conversion from Right Ascension Angle to degrees"""
    degrees = degrees % 360

    temp = degrees / 15.0
    hours   = int(temp)
    temp = (temp - hours) * 60
    minutes = int(temp)
    seconds = (temp - minutes) * 60
    
    return hours, minutes, seconds

def Degrees2DeclinationAngle(degrees : float) -> tuple[int, int, float] :
    """conversion from Declination Angle to degrees"""
    degrees = degrees % 180

    sign = -1 if degrees < 0 else 1
    temp = abs(degrees)
    arc_degrees = int(temp)
    temp = (temp - arc_degrees) * 60
    arc_minutes = int(temp)
    arc_seconds = (temp - arc_minutes) * 60

    return arc_degrees*sign, arc_minutes, arc_seconds 
