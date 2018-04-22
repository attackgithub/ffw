#!/usr/bin/env python2

import socket
import threading
import select
import pickle
import logging
import os
import time

from target import simpleservermanager
from network import networkmanager
from common.corpusdata import CorpusData
from common.networkdata import NetworkData

"""
Interceptor.py, standalone binary

it perform a man-in-the-middle attack
the client has to connect to the specific port of this tool
all data will be forwarded to the server, and vice-versa

interceptor will also record all transmitted data, split up between
read()'s, and split between server and client

It will store the data in files with the name data_<connid>.pickle,
serialized python objects as pickle

This can be used later to fuzz server (or client) with ffw interceptor mode,
which excpects pickle file recorded here.

A recorded connection can be replayed to test it.
"""


# based on: https://gist.github.com/sivachandran/1969859 (no license)

terminateAll = False


class ClientTcpThread(threading.Thread):
    def createDataEntry(self, frm, data, index):
        #data = {
        #    "from": frm,
        #    "data": data,
        #    'index': index,
        #}
        #
        #return data
        return NetworkData.createNetworkMessage(frm, data, index)


    def __init__(self, config, clientSocket, targetHost, targetPort, threadId):
        threading.Thread.__init__(self)
        self.config = config
        self.__clientSocket = clientSocket
        self.__targetHost = targetHost
        self.__targetPort = targetPort
        self.__threadId = threadId
        self.data = []


    def run(self):
        print("Client Thread" + str(self.__threadId) + " started")

        self.__clientSocket.setblocking(0)

        logging.info('Logging into: %s:%i' % (self.__targetHost, self.__targetPort) )
        targetHostSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            targetHostSocket.connect((self.__targetHost, self.__targetPort))
        except Exception as e:
            print("connect() exception: " + str(e))
            print("  while connecting to: " + self.__targetHost + ":" + str(self.__targetPort))
            return
        targetHostSocket.setblocking(0)

        clientData = ""
        targetHostData = ""
        terminate = False
        n = 0
        while not terminate and not terminateAll:
            inputs = [self.__clientSocket, targetHostSocket]
            outputs = []

            if len(clientData) > 0:
                outputs.append(self.__clientSocket)

            if len(targetHostData) > 0:
                outputs.append(targetHostSocket)

            try:
                inputsReady, outputsReady, errorsReady = select.select(inputs, outputs, [], 1.0)
            except Exception as e:
                print(e)
                break

            for inp in inputsReady:
                if inp == self.__clientSocket:
                    try:
                        data = self.__clientSocket.recv(4096)
                    except Exception as e:
                        print(e)

                    if data is not None:
                        if len(data) > 0:
                            print("Received from client: " + str(self.__threadId) + ": " + str(len(data)))
                            targetHostData += data
                            self.data.append( self.createDataEntry("cli", data, n) )
                            n += 1
                        else:
                            terminate = True
                elif inp == targetHostSocket:
                    data = None
                    try:
                        data = targetHostSocket.recv(4096)
                        print("target: recv data")
                    except Exception as e:
                        print("target recv Exception: " + str(e))
                        break

                    if data is not None:
                        if len(data) > 0:
                            print("Received from server: " + str(self.__threadId) + ": " + str(len(data)))
                            clientData += data
                            self.data.append( self.createDataEntry("srv", data, n) )
                            n += 1
                        else:
                            terminate = True

            for out in outputsReady:
                if out == self.__clientSocket and len(clientData) > 0:
                    bytesWritten = self.__clientSocket.send(clientData)
                    if bytesWritten > 0:
                        clientData = clientData[bytesWritten:]
                elif out == targetHostSocket and len(targetHostData) > 0:
                    bytesWritten = targetHostSocket.send(targetHostData)
                    if bytesWritten > 0:
                        targetHostData = targetHostData[bytesWritten:]

        self.__clientSocket.close()
        targetHostSocket.close()
        print("ClientTcpThread terminating")

        # store all the stuff
        print("Got " + str(len(self.data)) + " packets")
        fileName = self.getDataFilename()

        print("Storing into file: " + fileName)
        networkData = NetworkData(self.config, self.data)
        corpusData = CorpusData(self.config, fileName, networkData)
        corpusData.writeToFile()


    def getDataFilename(self):
        n = 0
        filename = "data_" + str(n) + ".pickle"
        while os.path.isfile(filename):
            n += 1
            filename = "data_" + str(n) + ".pickle"

        return filename


def performTcpIntercept(config, localHost, localPort, targetHost, targetPort):
    global terminateAll
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        serverSocket.bind((localHost, int(localPort)))
        serverSocket.listen(5)
    except Exception as e:
        print("Error binding to: %s:%s: %s" % (localHost, localPort, str(e)))
        return

    print("Forwarding everything to %s:%s" % (targetHost, targetPort))
    print("Waiting for new client on port: " + str(localPort))

    threadId = 0
    while True:
        try:
            clientSocket, address = serverSocket.accept()
        except socket.error as e:
            logging.error("accept() Socket Error: " + str(e))
            logging.error("Try waiting a bit...")

            break
        except KeyboardInterrupt:
            print("\nTerminating all clients...")
            terminateAll = True
            break

        ClientTcpThread(config, clientSocket, targetHost, targetPort, threadId).start()
        threadId += 1

    serverSocket.close()


def performUdpIntercept(config, localHost, localPort, targetHost, targetPort):
    dataArr = []
    n = 0

    # connect to server
    sockTarget = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # listening
    sockListen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Listening on: " + str(localHost) + " : " + str(localPort))
    sockListen.bind((localHost, int(localPort)))
    sockTarget.settimeout(1.0)
    sockListen.settimeout(1.0)

    while True:
        try:
            try:
                # wait for client msg
                print("Waiting for client msg...")
                data, addrCli = sockListen.recvfrom(1024)  # buffer size is 1024 bytes
                print("cli: received message len: ", str(len(data)))
                print("     from: " + str(addrCli))
                sockTarget.sendto(data, (targetHost, targetPort))

                dataArr.append( self.createDataEntry('cli', data, n) )
                n += 1
            except socket.timeout:
                print("cli: recv() timeout from server, continuing...")

            # check if server sends answer
            try:
                data, addrSrv = sockTarget.recvfrom(1024)
                if data is not None:
                    print("srv: Received from server: len: " + str(len(data)))
                    dataArr.append( self.createDataEntry('srv', data, n))

                    print("     Forward data from server to: " + str(addrCli))
                    sockListen.sendto(data, addrCli)

                    n += 1
            except socket.timeout:
                print("srv: recv() timeout from server, continuing...")

        except KeyboardInterrupt:
            print("\nTerminating...")
            break

    # store all the stuff
    print("Got " + str(len(dataArr)) + " packets")
    fileName = "data_0.pickle"
    networkData = NetworkData(self.config, dataArr)
    corpusData = CorpusData(self.config, fileName, networkData)
    corpusData.writeToFile()


# called from ffw
def doIntercept(config, interceptorPort, targetPort):
    localHost = "0.0.0.0"
    targetHost = "localhost"

    config["baseport"] = targetPort

    # run the targetserver, as configured in config
    serverManager = simpleservermanager.SimpleServerManager(config, 0, targetPort)
    isStarted = serverManager.start()
    if not isStarted:
        print("Could not start server, check its output")
        return

    # test connection
    networkManager = networkmanager.NetworkManager(config, targetPort)

    if not networkManager.debugServerConnection():
        return

    # start mitm server
    if config["ipproto"] is "tcp":
        performTcpIntercept(config, localHost, interceptorPort, targetHost, targetPort)
    else:
        performUdpIntercept(config, localHost, interceptorPort, targetHost, targetPort)
