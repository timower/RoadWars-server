import asyncio
import json

usermgr = None


# {"req": "login", "user": "<user name>", "pass": "password"}
class RoadWarsProtocol(asyncio.Protocol):

    TIMEOUT = 60.0

    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(self.peername))
        self.transport = transport
        self.user_name = None
        self.request_table = {
            # request           check key?   requirements                            func
            "login":            [False,     ["user", "pass"],                           self.login],
            "logout":           [True,      ["user"],                                   self.logout],
            "check-login":      [True,      [],                                         self.check_login],
            "create-user":      [False,     ["user", "pass", "email", "color"],         self.create_user],
            "user-info":        [True,      ["user", "info-user"],                      self.user_info],
            "street-rank":      [True,      ["street"],                                 self.street_rank],
            "get-points":       [True,      ["street", "user"],                         self.get_points], # unused ?
            "get-all-points":   [True,      ["info-user"],                              self.get_all_points],
            "get-all-points2":  [True,      ["info-user"],                              self.get_all_points_new],
            "add-points":       [True,      ["user", "street", "points"],               self.add_points],
            "get-street":       [True,      ["street"],                                 self.get_street],
            "get-all-streets":  [True,      ["neLat", "neLong", "swLat", "swLong"],     self.get_all_streets],
            "get-friends":      [True,      ["user"],                                   self.get_friends],
            "add-friend":       [True,      ["user", "name"],                           self.add_friend],
            "get-all-users":    [True,      [],                                         self.get_all_users],
            "get-friend-reqs":  [True,      ["user"],                                   self.get_friend_reqs],
            "accept-friend":    [True,      ["user", "name"],                           self.accept_friend],
            "remove-friend":    [True,      ["user", "name"],                           self.remove_friend],
            "remove-friend-req":[True,      ["user", "name"],                           self.remove_friend_req],
            "get-unknown-users":[True,      ["user"],                                   self.get_unknown_users],
            "nfc-friend":       [True,      ["user", "name"],                           self.nfc_friend],
            "start-minigame":   [True,      ["user", "name", "street"],                 self.start_minigame],
            "finish-minigame":  [True,      ["user", "name", "street"],                 self.finished_minigame],
            "stop-minigame":    [True,      ["user", "name", "street"],                 self.stop_minigame],
            "ping":             [False,     [],                                         self.ping],
            "get-online-users": [True,      [],                                         self.get_online_users],
            "get-world-ranking":[True,      [],                                         self.get_world_ranking],
            "change-user-info": [True,      ["user", "name", "pass", "email", "color"], self.change_user_info],
        }

        self.h_timeout = asyncio.get_event_loop().call_later(self.TIMEOUT, self.timeout)

    def data_received(self, data):

        self.h_timeout.cancel()
        self.h_timeout = asyncio.get_event_loop().call_later(self.TIMEOUT, self.timeout)

        message = data.decode()
        obj = json.loads(message)
        print("received: " + str({k: v if k != 'pass' else '****' for k, v in obj.items()}))

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
                    if self.user_name is None:
                        self.user_name = obj["user"]
                        usermgr.online_user(self.user_name, self)
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
        if self.user_name is not None:
            usermgr.offline_user(self.user_name)
        self.h_timeout.cancel()
        print('Connection lost from {}, {}'.format(self.user_name, self.peername))
        self.user_name = None

    def timeout(self):
        self.transport.write_eof()
        # calls connection_lost(None):
        self.transport.close()
        print('User: {} timed out'.format(self.user_name))

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
            self.user_name = user
            usermgr.online_user(user, self)

    def logout(self, response, user):
        usermgr.logout(user)
        response["res"] = True

    def check_login(self, response):
        response["res"] = True

    def create_user(self, response, user, passw, email, color):
        response["res"] = usermgr.create_user(user, passw, email, color)

    def user_info(self, response, user, info_user):
        info = usermgr.get_info(user, info_user)
        if info is not None:
            response["res"] = True
            response["friend"] = info["friend"]
            response["friend-req"] = info["friend-req"]
            response["sent-friend-req"] = info["sent-friend-req"]
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

    def get_all_points_new(self, response, info_user):
        response["res"] = True
        response["points"] = usermgr.get_all_points_new(info_user)

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
        response["streets"] = usermgr.get_all_streets(float(neLat), float(neLong), float(swLat), float(swLong))
        response["res"] = True

    def get_friends(self, response, user):
        response["friends"] = usermgr.get_friends(user)
        response["res"] = True

    def add_friend(self, response, user, name):
        response["res"] = usermgr.add_friend(user, name)

    def get_friend_reqs(self, response, user):
        response["friend-reqs"] = usermgr.get_friend_reqs(user)
        response["res"] = True

    def get_all_users(self, response):
        response["users"] = usermgr.get_all_users()
        response["res"] = True

    def accept_friend(self, response, user, name):
        response["res"] = usermgr.accept_friend(user, name)

    def remove_friend(self, response, user, name):
        response["res"] = usermgr.remove_friend(user, name)

    def remove_friend_req(self, response, user, name):
        response["res"] = usermgr.remove_friend_req(user, name)

    def get_unknown_users(self, response, user):
        response["users"] = usermgr.get_unknown_users(user)
        response["res"] = True

    def nfc_friend(self, response, user, name):
        response["res"] = usermgr.nfc_friend(user, name)

    def start_minigame(self, response, user, name, street):
        response["res"] = usermgr.start_minigame(user, name, street)

    def finished_minigame(self, response, user, name, street):
        response["res"] = usermgr.finished_minigame(user, name, street)
        response["street"] = street

    def stop_minigame(self, response, user, name, street):
        response["res"] = usermgr.stop_minigame(user, name, street)

    def ping(self, response):
        response["res"] = True

    def get_online_users(self, response):
        response["res"] = True
        response["users"] = usermgr.get_online_users()

    def get_world_ranking(self,response):
        response["res"] = True
        response["rank"] = usermgr.get_world_ranking()

    def change_user_info(self, response, user, name, passw, email, color):
        response["name"] = name
        response["res"] = usermgr.change_user_info(user, name, passw, email, color)
        if response["res"]:
            usermgr.offline_user(user)
            self.user_name = name
            usermgr.online_user(name, self)
