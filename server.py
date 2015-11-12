import asyncio
import sqlite3
import googlemaps
from user_manager import UserManager
import protocol

if __name__ == '__main__':
    db = sqlite3.connect('test.db')
    gmaps = googlemaps.Client(key="AIzaSyCnMTd5Ni48syP8OHe_Q3iQuDcnoESMErQ")
    protocol.usermgr = UserManager(db, gmaps)

    loop = asyncio.get_event_loop()
    coro = loop.create_server(protocol.RoadWarsProtocol, '0.0.0.0', 4444)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

    db.close()
