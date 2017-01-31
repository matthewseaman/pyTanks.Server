# Configuration settings for both the game and the server

class gameSettings:
    class mapSize:
        # (0, 0) is the upper left corner with +x going to the right and +y going down
        x = 500                         # In pixels
        y = 500                         # In pixels

    class tankProps:
        speed = 25                       # In pixels per second

class serverSettings:
    ip = "127.0.0.1"                # IP address to run the websocket server on
    port = 5678                     # Port to run the websocket server on
    framesPerSecond = 60            # The target frame rate for the frameCallback function
    updatesPerSecond = 15           # How many game state updates should be sent to clients each second

    # Level of debugging logging for the websocket server
    logLevel = 1  # 0 for none, 1 for FPS and connect/disconnect, 2 for all server status logs, 3 for all websocket logs

    class apiPaths:
        viewer = "/pyTanksAPI/viewer"    # Path that viewer clients connect on
        player = "/pyTanksAPI/player"    # Path that player clients connect on

    class clientTypes:
        viewer = "viewer"               # A javascript game viewing client
        player = "player"               # A python AI player client