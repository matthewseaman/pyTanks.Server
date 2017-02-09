import asyncio
import websockets
import datetime
import random
import config

# The websocket server and asyncio functions
#   This takes care of managing the io for the clients and calling the given functions in gameMaster.py at the set rate

# Used to store the info for active clients
class client:
    def __init__(self, clientSocket, type):
        self.socket = clientSocket  # The client's websocket
        self.type = type            # The type of client (valid types defined in config.serverSettings.clientTypes)
        self.outgoing = list()      # The outgoing message queue for this client
        self.incoming = list()      # The incoming message queue for this client

# Each entry is one active client
clients = dict()

# Appends a message to the outgoing queues for the indicated client(s)
#   recipient must be a valid int clientID or a type in config.serverSettings.clientTypes
def send(recipient, message):
    if isinstance(recipient, int):
        clients[recipient].outgoing.append(message)
    else:
        for clientID in clients:
            if clients[clientID].type == recipient:
                clients[clientID].outgoing.append(message)

    if config.serverSettings.logLevel >= 2:
        print("Message added to send queue for " + str(recipient) + ": " + message)

# Starts the sever and asyncio loop
#    frameCallback:    The function to call every frame
#    updateCallback:   The function to call every client game state update
def runServer(frameCallback, updateCallback):
    # --- Internal websocket server functions: ---

    # Handles printing of debug info
    def logPrint(message, minLevel):
        if config.serverSettings.logLevel >= minLevel:
            print(message)

    # Gets the delta between now and a given datetime in seconds
    def timeDelta(aTime):
        diff = datetime.datetime.now() - aTime
        return diff.seconds + (diff.microseconds / 1000000)

    # Sends queued messages to a client
    async def sendTask(clientID):
        while clientID in clients:
            if len(clients[clientID].outgoing) != 0:
                await clients[clientID].socket.send(clients[clientID].outgoing.pop(0))
            else:
                await asyncio.sleep(0.05)

        logPrint("sendTask for " + str(clientID) + " exited", 1)

    # Registers a client, starts sendTask for it, and watches for incoming messages
    async def clientHandler(websocket, path):
        # Check the client's connection path and set API type
        if path == config.serverSettings.apiPaths.viewer:
            clientType = config.serverSettings.clientTypes.viewer
        elif path == config.serverSettings.apiPaths.player:
            clientType = config.serverSettings.clientTypes.player
        else:
            # Invalid client
            logPrint("A client tried to connect using an invalid API path - connection refused", 1)
            await websocket.send("Invalid API path - Check that your client config is up to date")
            return  # Returning from this function disconnects the client

        # Generate a clientID
        while True:
            if clientType == config.serverSettings.clientTypes.player:
                # If it's a player the id needs to map to a name in the list
                clientID = random.randint(0, len(config.serverSettings.tankNames) - 1)
            else:
                clientID = random.randint(1000, 9999)

            if clientID not in clients:
                break

        # Add the client to the dictionary of active clients
        clients[clientID] = client(websocket, clientType)

        logPrint("Client (clientID: " + str(clientID) + ", type: " + clients[clientID].type + ") connected at " + path, 1)

        # Start the sendTask for this socket
        asyncio.get_event_loop().create_task(sendTask(clientID))

        # Handles incoming messages from a client
        try:
            while clientID in clients:
                message = await websocket.recv()
                clients[clientID].incoming.append(message)

                logPrint("Got message from " + str(clientID) + ": " + message, 2)
        except websockets.exceptions.ConnectionClosed:
            # The socket closed so remove the client
            clients.pop(clientID)

        logPrint("Handler/receiveTask for " + str(clientID) + " exited", 1)

        # (When this function returns the socket dies)

    # Runs frameCallback every frame and aims to hold the given frame rate
    #   Also runs updateCallback at the set rate
    async def frameLoop():
        # For frame rate targeting
        lastFrameTime = datetime.datetime.now()
        baseDelay = 1 / config.serverSettings.framesPerSecond
        delay = baseDelay
        deltas = list()

        # For timing game state updates
        timeSinceLastUpdate = 1 / config.serverSettings.updatesPerSecond

        # For calculating the FPS for logging
        lastFSPLog = datetime.datetime.now()
        frameCount = 0

        while True:
            # Calculate the time passed in seconds and adds it to the list of deltas
            frameDelta = timeDelta(lastFrameTime)
            lastFrameTime = datetime.datetime.now()
            deltas.append(frameDelta)
            if len(deltas) > 15:
                deltas.pop(0)

            # Adjust delay to try to keep the actual frame rate within 5% of the target
            avgDelta = sum(deltas) / float(len(deltas))
            if avgDelta * config.serverSettings.framesPerSecond < 0.95:      # Too fast
                delay += baseDelay * 0.01
            elif avgDelta * config.serverSettings.framesPerSecond > 1.05:    # Too slow
                delay -= baseDelay * 0.01

            if delay < 1 / 250:
                delay = 1 / 250

            # Log FPS if server logging is enabled
            if config.serverSettings.logLevel >= 1:
                frameCount += 1

                if timeDelta(lastFSPLog) >= 5:
                    print("FPS: " + str(frameCount / 5))
                    frameCount = 0
                    lastFSPLog = datetime.datetime.now()

            # Run frameCallback each frame
            frameCallback(frameDelta)

            # Run updateCallback at the rate set in config.py
            timeSinceLastUpdate += frameDelta
            if timeSinceLastUpdate >= 1 / config.serverSettings.updatesPerSecond:
                timeSinceLastUpdate = 0
                updateCallback()

            # Sleep until the next frame
            await asyncio.sleep(delay)      # (If this doesn't sleep then the other tasks can never be completed.)

    # --- Websocket server startup code: ---

    # Configure websocket server logging
    if config.serverSettings.logLevel >= 3:
        import logging
        logger = logging.getLogger("websockets")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())
        asyncio.get_event_loop().set_debug(True)

    # Start the sever and asyncio loop
    start_server = websockets.serve(clientHandler, config.serverSettings.ip, config.serverSettings.port)
    asyncio.get_event_loop().run_until_complete(start_server)
    print("Server started")
    asyncio.get_event_loop().run_until_complete(frameLoop())