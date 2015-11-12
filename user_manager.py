import json
import random
import googlemaps

class UserManager:
    def __init__(self, db, gmaps):
        self.gmaps = gmaps
        self.db = db
        self.keys = {}

    def create_user(self, user, pasw, email, color=None):
        if color is None:
            color = -1
        #INSERT INTO `users`(`id`,`name`,`password`,`email`) VALUES (3,'','','');
        t = (user, pasw, email, color)
        try:
            self.db.execute("INSERT INTO users (name, password, email, color) VALUES (?, ?, ?, ?)", t)
            self.db.commit()
        except sqlite3.IntegrityError as e:
            return False
        return True

    def login(self, user, pasw):
        t = (user,)
        c = self.db.execute("SELECT password FROM users WHERE name=?", t)
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
        c = self.db.execute("SELECT email, color FROM users WHERE name=?", t)
        l = c.fetchall()
        if len(l) != 1:
            return None
        ret["email"] = l[0][0]
        ret["color"] = l[0][1]
        return ret

    def get_points(self, user, street):
        # SELECT points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name="test" AND streets.name="naamsestraat"
        t = (user, street)
        c = self.db.execute("SELECT points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name=? AND streets.name=?", t)
        l = c.fetchall()
        if (len(l) != 1):
            return 0
        return l[0][0]

    def add_points(self, street, user, points):
        #key: AIzaSyCnMTd5Ni48syP8OHe_Q3iQuDcnoESMErQ
        changed_points = False
        t = (street,)
        c = self.db.execute("SELECT id, userId FROM streets WHERE name=?", t)
        l = c.fetchall()
        streetId = None
        # userId of owner of street
        userId = None
        old_points = 0

        if (len(l) != 1):
            # street doesn't exist
            lookup = gmaps.geocode(street + ", Leuven")
            lat = None
            lng = None
            if (len(lookup) > 0):
                lat = lookup[0]["geometry"]["location"]["lat"]
                lng = lookup[0]["geometry"]["location"]["lng"]

            # lookup userId
            t = (user,)
            c = self.db.execute("SELECT id FROM users WHERE name=?", t)
            l = c.fetchall()
            userId = l[0][0]

            t = (street, lat, lng, userId)
            c = self.db.execute("INSERT INTO streets (name, lat, long, userId) VALUES (?, ?, ?, ?)", t)
            streetId = c.lastrowid
            changed_points = True
        else:
            # street does exist
            streetId = l[0][0]
            userId = l[0][1]
            # get old_points:
            t= (userId, streetId)
            c = self.db.execute("SELECT points FROM points WHERE userId=? AND streetId=?", t)
            l = c.fetchall()
            old_points = l[0][0]

        t = (user, streetId)
        c = self.db.execute("SELECT points.id, points.points FROM points INNER JOIN users ON points.userId=users.id WHERE users.name=? AND points.streetId=?", t)
        l = c.fetchall()
        new_points = None
        if (len(l) != 1):
            # user has no points in street
            t = (streetId, points, user)
            c = self.db.execute("INSERT INTO points (userId, streetId, points) SELECT users.id, ?, ? FROM users WHERE users.name=?", t)
            if not changed_points:
                # check if new_points > old_points
                new_points = points
        else:
            # user has points in street
            new_points = points + l[0][1]
            t = (new_points, l[0][0])
            c = self.db.execute("UPDATE points SET points=? WHERE id=?", t)

        if new_points is not None:
            print("old points: " + str(old_points))
            print("new points: " + str(new_points))
            if new_points > old_points:
                print("updating userId in streets")
                t = (user, streetId)
                c = self.db.execute("UPDATE streets SET userId=(SELECT id FROM users WHERE name=?) WHERE id=?", t)

        self.db.commit()
        return True

    def get_rank(self, street):
        # SELECT users.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name='naamsestraat' ORDER BY points.points DESC LIMIT 10
        t = (street,)
        c = self.db.execute("SELECT users.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name=? ORDER BY points.points DESC LIMIT 10", t)
        return c.fetchall()

    def get_top_points(self, street):
        t = (street,)
        # TODO: optimize to use userId in street table
        c = self.db.execute("SELECT points.points, users.name, users.color FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE streets.name=? ORDER BY points.points DESC LIMIT 1", t)
        l = c.fetchall()
        if (len(l) != 1):
            return None
        return l[0]

    def get_all_points(self, user):
        # SELECT streets.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name="test" ORDER BY points.points DESC
        t = (user,)
        c = self.db.execute("SELECT streets.name, points.points FROM points INNER JOIN streets ON points.streetId=streets.id INNER JOIN users ON points.userId=users.id WHERE users.name=? ORDER BY points.points DESC", t)
        l = c.fetchall()
        return l

    # def get_street(self, street):
    #     t = (street,)
    #     c = self.db.execute("SELECT points.points, users.color FROM streets INNER JOIN users ON streets.userId=users.id INNER JOIN points ON users.id=points.userId AND streets.id=points.streetId WHERE streets.name=?", t)
    #     l = c.fetchall()
    #     if (len(l) != 1):
    #         return None
    #     return l

    def get_all_streets(self, neLat, neLong, swLat, swLong):
        t = (neLat, neLong, swLat, swLong)
        c = self.db.execute("SELECT streets.name, streets.lat, streets.long, users.color FROM streets INNER JOIN users ON streets.userId=users.id INNER JOIN points ON streets.id=points.streetId AND users.id=points.userId WHERE streets.lat < ? AND streets.long < ? AND streets.lat > ? AND streets.long > ? ORDER BY points.points DESC LIMIT 10", t)
        l = c.fetchall()
        return l


