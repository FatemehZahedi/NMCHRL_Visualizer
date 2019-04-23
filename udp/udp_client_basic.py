import socket
import sys
import numpy as np
import threading
import time


class UDPClient:

    _addr = ""
    _port = 0
    _sockfd = None
    _server_addr = None
    _data = np.zeros(2)

    def __init__(self, addr, port):
        # Create udp socket and connect to server
        self._addr = addr
        self._port = port
        self._sockfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._server_addr = (self._addr, self._port)

        message = 'Hi Server'
        # Send data
        print("sending {}".format(message))
        sent = self._sockfd.sendto(bytes(message, 'utf-8'), self._server_addr)
        threading.Thread(target=self.ReceiveForever, name="udp_receive_thread", daemon=False).start()

    def ReceiveForever(self):
        while(True):
            try:
                data, server = self._sockfd.recvfrom(4096)
                self._data = np.frombuffer(data, dtype=np.double)
            except:
                self._sockfd.close()

    def GetData(self):
        return self._data

def main():
    addr = input("Enter IP Address\n")
    port = int(input("Enter Port\n"))
    client = UDPClient(addr, port)

    while(1):
        print(client.GetData())
        time.sleep(.5)

main()
