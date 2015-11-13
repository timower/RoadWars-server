import asyncio
import json

usermgr = None


# {"req": "login", "user": "<user name>", "pass": "password"}
class RoadWarsProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(self.peername))
        self.transport = transport
        self.request_table = {
            # request           check key?   requirements                            func
            "login":            [False,     ["user", "pass"],                       self.login],
            "logout":           [True,      ["user"],                               self.logout],
            "check-login":      [True,      [],                                     self.check_login],
            "create-user":      [False,     ["user", "pass", "email", "color"],     self.create_user],
            "user-info":        [True,      ["info-user"],                          self.user_info],
            "street-rank":      [True,      ["street"],                             self.street_rank],
            "get-points":       [True,      ["street", "user"],                     self.get_points], # unused ?
            "get-all-points":   [True,      ["info-user"],                          self.get_all_points],
            "add-points":       [True,      ["user", "street", "points"],           self.add_points],
            "get-street":       [True,      ["street"],                             self.get_street],
            "get-all-streets":  [True,      ["neLat", "neLong", "swLat", "swLong"], self.get_all_streets],
            "get-friends":      [True,      ["user"],                               self.get_friends],
            "add-friend":   [True,      ["user, name"],                         self.add_friend],
        }

    def data_received(self, data):
        message = data.decode()
        print("received: " + message)
        obj = json.loads(message)

        response = {"res": False}

        if "req" in obj:
            request = obj["req"]
            response["req"] = request

            if request in self.request_table:
                row = self.request_table[request]
                # check key:
                if row[0]:
                    if not ("user" in obj and "key" in obj):
                        response["err"] = "Need a user and key"
                        self.respond(response)
                        return
                    if not usermgr.check(obj["user"], obj["key"]):
                        response["err"] = "Invalid key"
                        self.respond(response)
                        return
                # check requirements:
                requirements = row[1]
                if any(x not in obj for x in requirements):
                    response["err"] = "request needs more values"
                    self.respond(response)
                    return
                # call func:
                argument_list = [obj[x] for x in requirements]
                row[2](response, *argument_list)
            else:
                response["err"] = "Unknown request"
        self.respond(response)

    def connection_lost(self, exc):
        print('Connection lost from {}'.format(self.peername))

    def respond(self, obj):
        st = json.dumps(obj)
        self.transport.write(st.encode())
        self.transport.write("\n".encode())

    # request functions:

    def login(self, response, user, passw):
        key = usermgr.login(user, passw)
        if key is None:
            response["res"] = False
            response["err"] = "error logging in"
        else:
            response["res"] = True
            response["key"] = key

    def logout(self, response, user):
        usermgr.logout(user)
        response["res"] = True

    def check_login(self, response):
        response["res"] = True

    def create_user(self, response, user, passw, email, color):
        response["res"] = usermgr.create_user(user, passw, email, color)

    def user_info(self, response, info_user):
        info = usermgr.get_info(info_user)
        if info is not None:
            response["res"] = True
            response["email"] = info["email"]
            response["color"] = info["color"]
            response["n-streets"] = info["n-streets"]
            response["user"] = info_user

    def street_rank(self, response, street):
        response["res"] = True
        response["rank"] = usermgr.get_rank(street)

    def get_points(self, response, street, user):
        response["res"] = True
        response["points"] = usermgr.get_points(user, street)

    def get_all_points(self, response, info_user):
        response["res"] = True
        response["points"] = usermgr.get_all_points(info_user)

    def add_points(self, response, user, street, points):
        if points != 0:
            response["res"] = usermgr.add_points(street, user, points)
        else:
            response["res"] = True

    def get_street(self, response, street):
        info = usermgr.get_top_points(street)
        if info is not None:
            response["res"] = True
            response["street"] = street
            response["info"] = info

    def get_all_streets(self, response, neLat, neLong, swLat, swLong):
        response["streets"] = usermgr.get_all_streets(neLat, neLong, swLat, swLong)
        response["res"] = True

    def get_friends(self, response, user):
        response["friends"] = usermgr.get_friends(user)
        response["res"] = True

    def add_friend(self, response, user, name):
        response["requests"] = usermgr.add_friend(user, name)
        response["res"] = True
