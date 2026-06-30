"""
	Support class to implement a simple 1 client TCP server
"""

#-----------------------------------------------------------------------
import socket

import		SharedTCPbuffer as SharedTCPbuffer
from		SharedTCPbuffer import SharedTCPbuffer #import class only
from		threading import Thread, Lock, Event

MESSAGE_END_CHAR    =  '$'

#=============================================================================
class TcpServer():
    """implements a simple tcp server"""
    #--------------------------------------------------------------------
    def __init__(self, end_char = MESSAGE_END_CHAR):
        """initializes network services and vars"""
        self.serverSocket         = None
        # --- client data --- #
        self.clientSocket         = None
        self.clientAddress        = None
        # --- buffer --- #
        self.tcpBuffer            = SharedTCPbuffer()
        self.endChar              = end_char
        # --- accept thread --- #
        self.connectionThread     = None
        self.killConnectionThread = Event() #thread safe flag
        # --- mutex --- #
        self.lock                 = Lock()
        # === initializing event ===
        self.killConnectionThread.clear()
    
    #--------------------------------------------------------------------
    def StartServer( self , serverPort : int ) -> bool:
        """Starts a TCP/IP server on address 0.0.0.0"""
        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.serverSocket.bind(('0.0.0.0', serverPort))
            self.serverSocket.settimeout(1.0)
            self.serverSocket.listen()
            print(f"[ INFO ] server started at port {serverPort}")
        except Exception as e:
            print(f"[ ERROR ] unexpected error : {e}")
            return False
        
        return True
    #--------------------------------------------------------------------
    def StartConnectionListener( self ) -> bool:
        """ starts listening for connections """
        if self.serverSocket is None:
            print("[ ERROR ] serverSocket is None")
            return False
        else:
            self.connectionThread = Thread(target=self.ConnectionListener, args=(), name="TCP connection listener", daemon=True)
            self.connectionThread.start()
            return True 
    #--------------------------------------------------------------------
    def EndConnectionListener( self ) -> bool:
        """ end listening for connections """
        if self.serverSocket is None:
            print("[ ERROR ] serverSocket is None")
            return False
        elif self.connectionThread == None or not self.connectionThread.is_alive():
            print("[ ERROR ] ConnectionListener thread is not alive")
            return False
        else:
            
            self.killConnectionThread.set()
            self.connectionThread.join()
            return True
    #--------------------------------------------------------------------
    def GetData( self ) -> bytes | None :
        """Returns received bytes from TCP connection"""
        if self.tcpBuffer.IsDataPresent():
            return self.tcpBuffer.Read()
        else:
            return None
    
    #--------------------------------------------------------------------
    def SendData(self, data ) -> bool:
        """send string data over TCP connection"""
        if self.clientSocket is None:
            return False
        else:
            try:
                bytesData = data.encode('utf-8') if isinstance(data, str) else bytes(data)
                with self.lock:
                    client_socket = self.clientSocket
                if client_socket is None:
                    print("[ ERROR ] in SendData clientSocket is None")
                    return False
                #send all is atomic at SO level, this is just a request for kernel to send data
                client_socket.sendall(bytesData)
            except Exception as e:
                print(f"[ ERROR ] with {self.clientAddress} unexpected error: {e}")
                return False
        return True
    #--------------------------------------------------------------------
    def CloseConnection( self ) -> bool:
        """Service function to close WiFi(TCP) connection"""
        if self.serverSocket is None:
            return False
        if self.clientSocket:
            self.EndConnectionListener()
        # Clean up the connection
        try:
            self.serverSocket.shutdown(socket.SHUT_RDWR)
            self.serverSocket.close()
        except Exception as e:
            print(f"[ ERROR ] unexpected error in CloseConnection : {e}")
            return False
        return True

#=============================================================================
    def ConnectionListener( self ):
        """Starts a daemon thread that listen for TCP connections"""
        if self.serverSocket == None:
            print("[ ERROR ] in ConnectionListener serverSocket is None")
            return
        while True:
            # ---- checks if KillConnectionThread is set ---- #
            if self.killConnectionThread.is_set():
                break
            # ---- waits for a connection ---- #
            try:
                self.clientSocket , self.clientAddress = self.serverSocket.accept()
                self.clientSocket.settimeout(1)
            except socket.timeout:
                continue
            except Exception as e:
                if not self.killConnectionThread.is_set():
                        print(f"[ ERROR ] Accept error: {e}")
                break   
            print(f"[ INFO ] new connection from {self.clientAddress}")

            # ---- waits for a data ---- #
            inputData = bytes()
            while True:
                # we get the socket atomically and check if valid
                with self.lock:
                    client_sock = self.clientSocket
                if client_sock is None:
                    print("[ ERROR ] in ConnectionListener clientSocket is None")
                    break

                try :
                    # recv is atomic at SO level, we do not need to put it in mutex
                    inputData : bytes = client_sock.recv(4096)
                    if len(inputData) == 0:
                        print(f"[ INFO ] Client {self.clientAddress} has disconnected")
                        break
                    else:
                        self.tcpBuffer.Write(inputData)
                        # if the message contains the END_MESSAGE_CHAR we should stop listening
                        if MESSAGE_END_CHAR.encode() in inputData:
                            self.tcpBuffer.SetStopFlag(True)
                        inputData = bytes() # clears received data after copying to shared mem buffer

                    # External users will trigger thread finish by setting proper flag in shared obj
                    if self.tcpBuffer.GetStopFlag():
                        break
                except socket.timeout:
                    pass
                except Exception as e:
                    print(f"[ ERROR ] with {self.clientAddress} unexpected exception: {e}, closing ConnectionListener")
                    break
                
            if self.clientSocket:
                with self.lock:
                    self.clientSocket.close()
                    self.clientSocket = None
                    self.clientAddress = None
            self.tcpBuffer.SetStopFlag(False) # Reset for next client
            print("[ INFO ] Listening thread finished\n")
        # once we end connection Listener we close tcpBuffer
        self.tcpBuffer.SetStopFlag(True)




