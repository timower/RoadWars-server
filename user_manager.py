import random
import hashlib
import sqlite3


class UserManager:
    def __init__(self, db, gmaps):
        self.gmaps = gmaps
        self.db = db
        self.keys = {}
        self._online_users = {}
        self._delayed_responses = {}
        self.minigames = []
        # reset online users:
        self.db.execute("DELETE FROM online_users")
        self.db.commit()

    def online_user(self, user, protocol):
        if user not in self._online_users:
            t = (user,)
            self.db.execute("INSERT INTO online_users (userId) SELECT id FROM users WHERE name=?", t)
        if user in self._delayed_responses:
            protocol.respond(self._delayed_responses[user])
            del self._delayed_responses[user]
        self._online_users[user] = protocol
        print("user " + user + " is online")
       #self.db.commit()

    def offline_user(self, user):
        del self._online_users[user]
        t = (user,)
        self.db.execute("DELETE FROM online_users WHERE userId=(SELECT id FROM users WHERE name=?)", t)
        print("user " + user + " is offline")
        #self.db.commit()

    def create_user(self, user, pasw, email, color=None):
        if color is None:
            color = -1
        hashpass = hashlib.sha1(pasw.encode()).hexdigest()
        t = (user, hashpass, email, color)
        try:
            self.db.execute("INSERT INTO users (name, password, email, color) VALUES (?, ?, ?, ?)", t)
            self.db.commit()
        except sqlite3.IntegrityError as _:
            return False
        return True

    def login(self, user, pasw):
        passhash = hashlib.sha1(pasw.encode()).hexdigest()
        t = (user,)
        c = self.db.execute("SELECT password FROM users WHERE name=?", t)
        l = c.fetchall()
        print(l)
        if len(l) != 1 or l[0][0] != passhash:
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

    def get_info(self, user, user_info):
        ret = {}
        t = (user_info,)
        c = self.db.execute("SELECT email, color, id FROM users WHERE name=?", t)
        l = c.fetchall()
        if len(l) != 1:
            return None
        ret["email"] = l[0][0]
        ret["color"] = l[0][1]
        # get number of streets the user owns:
        t = (l[0][2],)
        c = self.db.execute("SELECT COUNT(id) FROM streets WHERE userId=?", t)
        l = c.fetchall()
        ret["n-streets"] = l[0][0]

        ret["friend"] = False
        ret["friend-req"] = False
        ret["sent-friend-req"] = False
        if user != user_info:
            t = (user, user_info)
            c = self.db.execute("SELECT status FROM friends WHERE receiverId =(SELECT id FROM users WHERE name = ?) AND senderId =(SELECT id FROM users WHERE name = ?)", t)
            l = c.fetchall()
            if len(l) != 0:
                if l[0][0] == 1:
                    ret["friend"] = True
                else:
                    ret["friend-req"] = True
            else:
                t = (user, user_info)
                c = self.db.execute("SELECT status FROM friends WHERE senderId =(SELECT id FROM users WHERE name = ?) AND receiverId =(SELECT id FROM users WHERE name = ?)", t)
                l = c.fetchall()
                if len(l) != 0:
                    ret["sent-friend-req"] = True
        return ret

    def get_points(self, user, street):
        t = (user, street)
        c = self.db.execute("SELECT points.points FROM points INNER JOIN streets ON points.streetId=streets.id "
                            "INNER JOIN users ON points.userId=users.id WHERE users.name=? AND streets.name=?", t)
        l = c.fetchall()
        if len(l) != 1:
            return 0
        return l[0][0]

    def add_street(self, street):
        """
        adds the street if it doesn't exist already
        :param street: the name of the street
        :return the id of the street / new street
        """
        # lookup street id
        t = (street,)
        c = self.db.execute("SELECT id FROM streets WHERE name=?", t)
        l = c.fetchall()
        if len(l) != 1:
            lookup = self.gmaps.geocode(street)
            lat = None
            lng = None
            if len(lookup) > 0:
                lat = lookup[0]["geometry"]["location"]["lat"]
                lng = lookup[0]["geometry"]["location"]["lng"]
            t = (street, lat, lng, 0)
            c = self.db.execute("INSERT INTO streets (name, lat, long, userId) VALUES (?, ?, ?, ?)", t)
            return c.lastrowid
        return l[0][0]

    def add_points(self, street, user, points):
        street_id = self.add_street(street)

        # try update
        t = (points, street_id, user)
        self.db.execute("UPDATE OR IGNORE points SET points=points+? WHERE streetId=? AND"
                        " userId=(SELECT id FROM users WHERE name=?)", t)
        # try insert
        t = (street_id, points, user)
        self.db.execute("INSERT OR IGNORE INTO points (userId, streetId, points) SELECT"
                        " users.id, ?, ? FROM users WHERE users.name=?", t)

        # update street owner
        t = (street_id, street_id)
        self.db.execute("UPDATE streets SET userId=(SELECT users.id FROM users INNER JOIN points ON"
                        " points.userId=users.id WHERE points.streetId=? ORDER BY points.points DESC LIMIT 1) "
                        "WHERE id=?", t)
        self.db.commit()
        return True

    def get_rank(self, street):
        t = (street,)
        c = self.db.execute("SELECT users.name, points.points FROM points INNER JOIN streets ON "
                            "points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE "
                            "streets.name=? ORDER BY points.points DESC LIMIT 10", t)
        return c.fetchall()

    def get_top_points(self, street):
        t = (street,)
        c = self.db.execute("SELECT points.points, users.name, users.color FROM points INNER JOIN streets "
                            "ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE "
                            "streets.userId=users.id AND streets.name=?", t)
        l = c.fetchall()
        if len(l) != 1:
            return None
        return l[0]

    def get_all_points(self, user):
        t = (user,)
        c = self.db.execute("SELECT streets.name, points.points FROM points INNER JOIN streets ON"
                            " points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE "
                            "users.name=? ORDER BY points.points DESC", t)
        l = c.fetchall()
        return l

    def get_all_streets(self, neLat, neLong, swLat, swLong):
        t = (neLat, neLong, swLat, swLong)
        c = self.db.execute("SELECT streets.name, streets.lat, streets.long, users.color FROM streets INNER JOIN users "
                            "ON streets.userId=users.id INNER JOIN points ON streets.id=points.streetId AND"
                            " users.id=points.userId WHERE streets.lat < ? AND streets.long < ? AND streets.lat > ? AND"
                            " streets.long > ? ORDER BY points.points DESC LIMIT 10", t)
        l = c.fetchall()
        return l

    def get_friends(self, user):
        t = (user,)
        c = self.db.execute("SELECT users.name, users.color FROM users INNER JOIN friends ON friends.receiverId=users.id "
                            "WHERE friends.senderId=(SELECT id FROM users WHERE name = ?) AND friends.status=1", t)
        return c.fetchall()

    def add_friend(self, user, name):
        t = (user, name)
        c = self.db.execute("INSERT INTO friends (senderId, receiverId, status) VALUES ((SELECT id FROM users WHERE name=?), "
                            "(SELECT id FROM users WHERE name=?), 0)", t)
        self.db.commit()
        return True

    def get_all_users(self):
        c = self.db.execute("SELECT name, color FROM users")
        return c.fetchall()

    def get_friend_reqs(self, user):
        t = (user,)
        c = self.db.execute("SELECT users.name, users.color FROM users INNER JOIN friends ON friends.senderId=users.id WHERE"
                            " friends.receiverId=(SELECT id FROM users WHERE name=?) AND friends.status=0", t)
        return c.fetchall()

    def accept_friend(self, user, name):
        t = (user, name)
        c = self.db.execute("UPDATE friends SET status = 1 WHERE friends.receiverId=(SELECT users.id FROM users WHERE "
                            "users.name = ?) AND friends.senderId=(SELECT users.id FROM users WHERE users.name=?)", t)
        t = (user, name)
        c = self.db.execute("INSERT INTO friends (senderId, receiverId, status) VALUES ((SELECT id FROM users WHERE name=?), "
                            "(SELECT id FROM users WHERE name=?), 1)", t)
        self.db.commit()
        return True

    def remove_friend(self, user, name):
        t = (user, name)
        c = self.db.execute("DELETE FROM friends WHERE senderId=(SELECT users.id FROM users WHERE name = ?) AND "
                            "receiverId =(SELECT users.id FROM users WHERE name = ?)", t)
        c = self.db.execute("DELETE FROM friends WHERE receiverId=(SELECT users.id FROM users WHERE name = ?) AND "
                            "senderId =(SELECT users.id FROM users WHERE name = ?)", t)
        self.db.commit()
        return True

    def remove_friend_req(self, user, name):
        t = (user, name)
        c = self.db.execute("DELETE FROM friends WHERE receiverId=(SELECT id FROM users WHERE name = ?) AND "
                            "senderId = (SELECT id FROM users WHERE name = ?)", t)
        self.db.commit()
        return True

    def get_unknown_users(self, user):
        t = (user,)
        c = self.db.execute("SELECT name, color FROM users WHERE id NOT IN (SELECT receiverId FROM friends WHERE senderId= (SELECT id FROM users WHERE name=?))", t)
        return c.fetchall()

    def nfc_friend(self, user, name):
        t = (user, name)
        c = self.db.execute("DELETE FROM friends WHERE senderId = (SELECT id FROM users WHERE name=?) AND receiverId = (SELECT id FROM users WHERE name=?)", t)
        c = self.db.execute("INSERT INTO friends (senderId, receiverId, status) VALUES ((SELECT id FROM users WHERE name=?), (SELECT id FROM users WHERE name=?), 1)", t)
        t = (name, user)
        c = self.db.execute("DELETE FROM friends WHERE senderId = (SELECT id FROM users WHERE name=?) AND receiverId = (SELECT id FROM users WHERE name=?)", t)
        c = self.db.execute("INSERT INTO friends (senderId, receiverId, status) VALUES ((SELECT id FROM users WHERE name=?), (SELECT id FROM users WHERE name=?), 1)", t)
        self.db.commit()
        return True

    def start_minigame(self, user, name, street):
        if name not in self._online_users:
            return False
        # check if user or name is already in minigame:
        if any(e[0] == user or e[1] == user or e[0] == name or e[1] == name for e in self.minigames):
            return False
        # start minigame
        self.minigames.append([user, name, street])
        print(self.minigames)
        # send response to name
        self._online_users[name].respond({"req": "started-minigame", "name": user, "res": True, "street": street})
        return True

    def finished_minigame(self, user, name, street):
        if [user, name, street] in self.minigames:
            self.minigames.remove([user, name, street])
            return True
        elif [name, user, street] in self.minigames:
            self.minigames.remove([name, user, street])
            return True
        else:
            return False

    def stop_minigame(self, user, name, street):
        if [user, name, street] in self.minigames:
            self.minigames.remove([user, name, street])
        elif [name, user, street] in self.minigames:
            self.minigames.remove([name, user, street])
        # Other user might be in on pause() ?
        resp = {"req": "stopped-minigame", "name": user, "res": True, "street": street }
        if name in self._online_users:
            self._online_users[name].respond(resp)
        else:
            # stop minigame next time user connects:
            self._delayed_responses[name] = resp
        return True

    def get_online_users(self):
        c = self.db.execute("SELECT users.name, users.color FROM online_users INNER JOIN users ON online_users.userId=users.id")
        return c.fetchall()

    def get_world_ranking(self):
        c = self.db.execute("SELECT COUNT(streets.id) AS c, users.name, users.color FROM streets INNER JOIN users ON "
                            "streets.userId=users.id GROUP BY streets.userId ORDER BY c DESC")
        l = c.fetchall()
        return l

    def change_user_info(self, user, name, passw, email, color):
        try:
            if passw == "":
                t = (name, email, color, user)
                c = self.db.execute("UPDATE users SET name=?, email=?, color=? WHERE name=?", t) 
            else:
                passhash = hashlib.sha1(passw.encode()).hexdigest()
                t = (name, passhash, email, color, user)
                c = self.db.execute("UPDATE users SET name=?, password=?, email=?, color=? WHERE name=?", t) 
            self.db.commit()
            if user in self.keys:
                key = self.keys[user]
                del self.keys[user]
                self.keys[name] = key
            return True
        except sqlite3.IntegrityError as _:
            return False
