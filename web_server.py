from flask import Flask, redirect, url_for, request, render_template, make_response
import json
import socket
import sys
app = Flask(__name__)

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect(("128.199.56.127", 44446))
sfile = socket.makefile()

def send_request(req, obj):
    obj["req"] = req
    string = json.dumps(obj)
    socket.send(string.encode())
    resp = sfile.readline()
    robj = json.loads(resp)
    print(robj)
    return robj

def user_login(user, passw):
    robj = send_request("login", {"user": user, "pass": passw})
    if robj["res"]:
        return robj["key"]
    return None

def check_key(user, key):
    robj = send_request("check-login", {"user": user, "key": key})
    return robj["res"]

@app.route("/login", methods=['GET', 'POST'])
def  login():
    if request.method == 'GET':
        return render_template("login.html")
    # check login
    # if succ -> redirect to main
    # else: redirect to login
    user = request.form["user"]
    passw = request.form["pass"]
    key = user_login(user, passw)
    if key is not None:
        response = make_response(redirect(url_for("main")))
        response.set_cookie("user", user, max_age=6000)
        response.set_cookie("key", key, max_age=6000)
        return response
    return redirect(url_for("main"))

@app.route("/request")
def streeets():
    user = request.cookies.get("user")
    key = request.cookies.get("key")
    if key is not None and user is not None:
        obj = request.args.to_dict()
        obj["user"] = user
        obj["key"] = key
        print(obj)
        return json.dumps(send_request(request.args.get("req"), obj))
    else:
        return "{\"res\": false}"

@app.route("/")
def main():
    # get cookies
    # check key 
    #  -> redirect
    # display main page
    key = request.cookies.get("key")
    user = request.cookies.get("user")
    if key == None or user == None or not check_key(user, key):
        return redirect(url_for("login"))
    return render_template("main.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
