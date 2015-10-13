import asyncio
import json
import sqlite3
import random

class EchoServerClientProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(self.peername))
        self.transport = transport
        server.add_client(transport)

    def data_received(self, data):
        message = data.decode()
        obj = json.loads(message)
        if "req" in obj:
            request = obj['req']
            if request == "login":
                # TODO: check for user  and pass
                key = usermgr.login(obj["user"], obj["pass"])
                if key is None:
                    response = {"res": "ERR"}
                    self.transport.write(json.dumps(response).encode())
                else:
                    response = {"res": "OK", "key": key}
                    self.transport.write(json.dumps(response).encode())
            elif request == "logout":
                # check key
                # logout
                # return ok / err
                pass
            elif request == "create-user":
                # add user
                # check ret
                # return err / ok
                pass
            elif request == "user-info":
                # check key
                # return info
                pass
            elif request == "street-rank":
                # check key
                # get rank
                # form message
                # return
                pass
            elif request == "add-points":
                # get user
                # get street
                # get key
                # get points
                # check key
                # add points
                # return ok / err
                pass

    def connection_lost(self, exc):
        print('Connection lost from {}'.format(self.peername))
        server.remove_client(self.transport)

class ChatServer:
    def __init__(self, loop, host, port):
        self.loop = loop
        self.host = host
        self.port = port

        self.clients = []
    
    def add_client(self, client):
        self.clients.append(client)

    def remove_client(self, client):
        self.clients.remove(client)

    def broadcast(self, msg, exc=None):
        for c in self.clients:
            if c is not exc:
                c.write(msg)

    def run(self):
        # Each client connection will create a new protocol instance
        coro = loop.create_server(EchoServerClientProtocol, '127.0.0.1', 4444)
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
    
class UserManager:
    def __init__(self, db):
        self.db = db
        self.keys = {}

    def login(self, user, pasw):
        # get user from database
        # check password
        # generate key
        # add key to keys
        # return key
        t = (user,)
        c = db.execute("SELECT password FROM users WHERE name=?", t)
        l = c.fetchall()
        print(l)
        if (len(l) != 1 or l[0][0] != pasw):
            return None
        key = ""
        for i in range(64):
            key += random.choice("0123456789abcdef")
        self.keys[user] = key
        return key

    def logout(self, user):
        # remove user from keys
        self.keys.pop(user)
        pass
        
    def check(self, user, key):
        # get key from keys
        return self.keys[user] == key

    def get_rank(self, street):
        # get rankings in street from database
        # format
        # return
        pass

db = sqlite3.connect('test.db')
usermgr = UserManager(db)

loop = asyncio.get_event_loop()
server = ChatServer(loop, "127.0.0.1", 4444)
server.run()
db.close()
