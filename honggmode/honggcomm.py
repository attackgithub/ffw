import socket
import time
import logging
import sys


class HonggComm(object):
    """Provides socket-based communication with honggfuzz."""

    def __init__(self):
        self.sock = None


    def openSocket(self, fuzzerPid):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        isConnected = False

        # try first the socket with pid
        server_address = '/tmp/honggfuzz_socket.' + str(fuzzerPid)
        sys.stdout.write('connecting to honggfuzz socket: %s... ' % server_address)
        tryCount = 0
        while True:
            if tryCount > 4:
                break

            try:
                sock.connect(server_address)
                isConnected = True
                break
            except socket.error as msg:
                logging.info("Honggcomm Error, could not connect to honggfuzz socket: " + str(msg))
                time.sleep(0.5)
            tryCount += 1

        if not isConnected:
            # now try without pid (backwards compatibility)
            server_address = '/tmp/honggfuzz_socket'
            sys.stdout.write('connecting to honggfuzz socket: %s... ' % server_address)
            tryCount = 0
            while True:
                if tryCount > 4:
                    break

                try:
                    sock.connect(server_address)
                    isConnected = True
                    break
                except socket.error as msg:
                    logging.info("Honggcomm Error, could not connect to honggfuzz socket: " + str(msg))
                    time.sleep(0.2)

                tryCount += 1

        self.sock = sock
        return isConnected
        

    def readSocket(self):
        logging.debug("SOCKET: Try to recv")
        recv = self.sock.recv(4).decode()
        logging.debug("SOCKET:   Recieved: " + recv)
        return recv


    def writeSocket(self, data):
        logging.debug("SOCKET: Send: " + data)
        self.sock.sendall( str.encode(data) )


    def closeSocket(self):
        self.sock.close()
