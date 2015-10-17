import asyncio
import json
import sqlite3
import random
    
# {"req": "login", "user": "<user name>", "pass": "password"}

class EchoServerClientProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(self.peername))
        self.transport = transport
        server.add_client(transport)

    def data_received(self, data):
        message = data.decode()
        print("received: " + message)
        obj = json.loads(message)

        response = {"res": False}

        if "req" in obj:

            request = obj['req']
            response["req"] = request

            # login:
            if request == "login" and "user" in obj and "pass" in obj:
                key = usermgr.login(obj["user"], obj["pass"])
                if key is None:
                    response = {"res":  False, "req": "login"}
                else:
                    response = {"res": True, "req": "login", "key": key}
            # logout:
            elif request == "logout" and "user" in obj and "key" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    usermgr.logout(obj["user"])
                    response["res"] = True
            # create user:
            elif request == "create-user" and "user" in obj and "pass" in obj and "email" in obj and "color" in obj:
                response["res"] = usermgr.create_user(obj["user"], obj["pass"], obj["email"], obj["color"])
            # user info:
            elif request == "user-info" and "user" in obj and "key" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    info = usermgr.get_info(obj["user"])
                    if info is not None:
                        response["res"] = True
                        response["email"] = info["email"]
                        response["color"] = info["color"]
                        response["user"] = obj["user"]
            # street rank
            elif request == "street-rank" and "street" in obj and "user" in obj and "key" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    response["res"] = True
                    response["rank"] = usermgr.get_rank(obj["street"])
            # get points
            elif request == "get-points" and "street" in obj and "user" in obj and "key" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    response["res"] = True
                    response["points"] = usermgr.get_points(obj["user"], obj["street"])
            # get all points (of user)
            elif request == "get-all-points" and "user" in obj and "key" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    response["res"] = True
                    response["points"] = usermgr.get_all_points(obj["user"])
            # add points
            elif request == "add-points" and "street" in obj and "points" in obj and "user" in obj and "key" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    response["res"] = usermgr.add_points(obj["street"], obj["user"], obj["points"])
            # check login
            elif request == "check-login" and "key" in obj and "user" in obj:
                response = {"res": usermgr.check(obj["user"], obj["key"]), "req": "check-login"}
        self.respond(response)

    def connection_lost(self, exc):
        print('Connection lost from {}'.format(self.peername))
        server.remove_client(self.transport)

    def respond(self, obj):
        st = json.dumps(obj)
        self.transport.write(st.encode())
        self.transport.write("\n".encode())

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
        coro = loop.create_server(EchoServerClientProtocol, self.host, self.port)
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

    def create_user(self, user, pasw, email, color=None):
        if color is None:
            color = -1
        #INSERT INTO `users`(`id`,`name`,`password`,`email`) VALUES (3,'','','');
        t = (user, pasw, email, color)
        try:
            db.execute("INSERT INTO users (name, password, email, color) VALUES (?, ?, ?, ?)", t)
            db.commit()
        except sqlite3.IntegrityError as e:
            return False
        return True

    def login(self, user, pasw):
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
        
    def check(self, user, key):
        # get key from keys
        if user not in self.keys:
            return False
        return self.keys[user] == key

    def get_info(self, user):
        ret = {}
        t = (user,)
        c = db.execute("SELECT email, color FROM users WHERE name=?", t)
        l = c.fetchall()
        if len(l) != 1:
            return None
        ret["email"] = l[0][0]
        ret["color"] = l[0][1]
        return ret

    def get_points(self, user, street):
        # SELECT points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name="test" AND streets.name="naamsestraat"
        t = (user, street)
        c = db.execute("SELECT points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name=? AND streets.name=?", t)
        l = c.fetchall()
        if (len(l) != 1):
            return 0
        return l[0][0]

    def add_points(self, street, user, points):
        return False
    # key: AIzaSyBngfWtrJwDsdORmB5jCFb3AMe9lrtqUHw
        # get street id
        # if not exists -> create -> gmaps api c.lastrowid
        # get points (join with users)
        # if not exists:
        #   insert
        # else:
        #   update
        print("in add")
        t = (street, user)
        c = db.execute("SELECT street.id, street.points FROM street INNER JOIN users ON street.userId=users.id WHERE street.street=? AND users.name=?", t)
        l = c.fetchall()
        # INSERT INTO street (userId, street, points) SELECT users.id, 'niewestraat', 10 FROM users WHERE users.name='timo'
        if (len(l) == 0):
            t = (street, points, user)
            c = db.execute("INSERT INTO street (userId, street, points) SELECT users.id, ?, ? FROM users WHERE users.name=?", t)
            db.commit()
        # UPDATE `street` SET `points`=? WHERE id=l[0][0];
        else:
            t = (points + l[0][1], l[0][0])
            c = db.execute("UPDATE street SET points=? WHERE id=?", t)
        return True

    def get_rank(self, street):
        # SELECT users.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name='naamsestraat' ORDER BY points.points DESC LIMIT 10
        t = (street,)
        c = db.execute("SELECT users.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name=? ORDER BY points.points DESC LIMIT 10", t)
        return c.fetchall()

    def get_all_points(self, user):
        # SELECT streets.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name="test" ORDER BY points.points DESC
        t = (user,)
        c = db.execute("SELECT streets.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name=? ORDER BY points.points DESC", t)
        l = c.fetchall()
        return l

db = sqlite3.connect('test.db')
usermgr = UserManager(db)

loop = asyncio.get_event_loop()
server = ChatServer(loop, "0.0.0.0", 4444)
server.run()
db.close()
