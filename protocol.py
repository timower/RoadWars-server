import asyncio
import json

usermgr = None

# {"req": "login", "user": "<user name>", "pass": "password"}
class RoadWarsProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(self.peername))
        self.transport = transport

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

    def respond(self, obj):
        st = json.dumps(obj)
        self.transport.write(st.encode())
        self.transport.write("\n".encode())
