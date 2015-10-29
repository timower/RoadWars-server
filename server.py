import asyncio
import json
import sqlite3
import random
import googlemaps
    
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
            elif request == "user-info" and "user" in obj and "key" in obj and "info-user" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    info = usermgr.get_info(obj["info-user"])
                    if info is not None:
                        response["res"] = True
                        response["email"] = info["email"]
                        response["color"] = info["color"]
                        response["user"] = obj["info-user"]
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
            elif request == "get-all-points" and "user" in obj and "key" in obj and "info-user" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    response["res"] = True
                    response["points"] = usermgr.get_all_points(obj["info-user"])
            # add points
            elif request == "add-points" and "street" in obj and "points" in obj and "user" in obj and "key" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    if obj["points"] != 0:
                        response["res"] = usermgr.add_points(obj["street"], obj["user"], obj["points"])
                    else:
                        response["res"] = True
            # check login
            elif request == "check-login" and "key" in obj and "user" in obj:
                response = {"res": usermgr.check(obj["user"], obj["key"]), "req": "check-login"}
            elif request == "get-street" and "key" in obj and "user" in obj and "street" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    info = usermgr.get_top_points(obj["street"])
                    if info is not None:
                        response["res"] = True
                        response["street"] = obj["street"]
                        response["info"] = info
            elif request == "get-all-streets" and "key" in obj and "user" in obj and "neLat" in obj and "neLong" in obj and "swLat" in obj and "swLong" in obj:
                if usermgr.check(obj["user"], obj["key"]):
                    response["streets"] = usermgr.get_all_streets(obj["neLat"], obj["neLong"], obj["swLat"], obj["swLong"])
                    response["res"] = True
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
        #key: AIzaSyCnMTd5Ni48syP8OHe_Q3iQuDcnoESMErQ
        changed_points = False
        t = (street,)
        c = db.execute("SELECT id, points FROM streets WHERE name=?", t)
        l = c.fetchall()
        streetId = None
        old_points = 0
        if (len(l) != 1):
            # street doesn't exist
            lookup = gmaps.geocode(street + ", Leuven")
            lat = None
            lng = None
            neLat = None
            neLong = None
            swLat = None
            swLong = None
            if (len(lookup) > 0):
                lat = lookup[0]["geometry"]["location"]["lat"]
                lng = lookup[0]["geometry"]["location"]["lng"]

                neLat = lookup[0]["geometry"]["viewport"]["northeast"]["lat"]
                neLong = lookup[0]["geometry"]["viewport"]["northeast"]["lng"]

                swLat = lookup[0]["geometry"]["viewport"]["southwest"]["lat"]
                swLong = lookup[0]["geometry"]["viewport"]["southwest"]["lng"]
            # TODO: add user color
            t = (street, lat, lng, neLat, neLong, swLat, swLong, points, user)
            c = db.execute("INSERT INTO streets (name, lat, long, neLat, neLong, swLat, swLong, points, color) SELECT ?, ?, ?, ?, ?, ?, ?, ?, users.color FROM users WHERE users.name=?", t)
            streetId = c.lastrowid
            changed_points = True
        else:
            # street does exist
            streetId = l[0][0]
            old_points = l[0][1]
        t = (user, streetId)
        c = db.execute("SELECT points.id, points.points FROM points INNER JOIN users ON points.userId=users.id WHERE users.name=? AND points.streetId=?", t)
        l = c.fetchall()
        new_points = None
        if (len(l) != 1):
            # user has no points in street
            t = (streetId, points, user)
            c = db.execute("INSERT INTO points (userId, streetId, points) SELECT users.id, ?, ? FROM users WHERE users.name=?", t)
            if not changed_points:
                # check if new_points > old_points
                new_points = points
        else:
            # user has points in street
            new_points = points + l[0][1]
            t = (points + l[0][1], l[0][0])
            c = db.execute("UPDATE points SET points=? WHERE id=?", t)
        if new_points is not None:
            print("old points: " + str(old_points))
            print("new points: " + str(new_points))
            if new_points > old_points:
                print("updateing points")
                t = (new_points, user, streetId)
                c = db.execute("UPDATE streets SET points=?, color=(SELECT users.color FROM users WHERE users.name=?) WHERE id=?", t)

        db.commit()
        return True

    def get_rank(self, street):
        # SELECT users.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name='naamsestraat' ORDER BY points.points DESC LIMIT 10
        t = (street,)
        c = db.execute("SELECT users.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name=? ORDER BY points.points DESC LIMIT 10", t)
        return c.fetchall()

    def get_top_points(self, street):
        t = (street,)
        c = db.execute("SELECT points.points, users.name, users.color FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name=? ORDER BY points.points DESC LIMIT 1", t)
        l = c.fetchall()
        if (len(l) != 1):
            return None
        return l[0]

    def get_all_points(self, user):
        # SELECT streets.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name="test" ORDER BY points.points DESC
        t = (user,)
        c = db.execute("SELECT streets.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name=? ORDER BY points.points DESC", t)
        l = c.fetchall()
        return l

    def get_street(self, street):
        t = (street,)
        c = db.execute("SELECT points, color FROM streets WHERE name=?", t)
        l = c.fetchall()
        if (len(l) != 1):
            return None
        return l

    def get_street_location(self, street):
        t = (street,)
        c = db.execute("SELECT neLat, neLong, swLat, swLong FROM streets WHERE name=?", t)
        l = c.fetchall()
        if (len(l) != 1):
            return None
        return l[0]
    def get_all_streets(self, neLat, neLong, swLat, swLong):
        t = (neLat, neLong, swLat, swLong)
        c = db.execute("SELECT name, lat, long, color FROM streets WHERE lat < ? AND long < ? AND lat > ? AND long > ? ORDER BY points DESC LIMIT 10", t)
        l = c.fetchall()
        return l

db = sqlite3.connect('test.db')
gmaps = googlemaps.Client(key="AIzaSyCnMTd5Ni48syP8OHe_Q3iQuDcnoESMErQ")
usermgr = UserManager(db)

loop = asyncio.get_event_loop()
server = ChatServer(loop, "0.0.0.0", 4444)
server.run()
db.close()
