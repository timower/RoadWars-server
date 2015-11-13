import random
import sqlite3


class UserManager:
    def __init__(self, db, gmaps):
        self.gmaps = gmaps
        self.db = db
        self.keys = {}

    def create_user(self, user, pasw, email, color=None):
        if color is None:
            color = -1

        t = (user, pasw, email, color)
        try:
            self.db.execute("INSERT INTO users (name, password, email, color) VALUES (?, ?, ?, ?)", t)
            self.db.commit()
        except sqlite3.IntegrityError as _:
            return False
        return True

    def login(self, user, pasw):
        t = (user,)
        c = self.db.execute("SELECT password FROM users WHERE name=?", t)
        l = c.fetchall()
        print(l)
        if len(l) != 1 or l[0][0] != pasw:
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
        c = self.db.execute("SELECT email, color FROM users WHERE name=?", t)
        l = c.fetchall()
        if len(l) != 1:
            return None
        ret["email"] = l[0][0]
        ret["color"] = l[0][1]
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
            lookup = self.gmaps.geocode(street + ", Leuven")
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
