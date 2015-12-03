from flask import Flask, redirect, url_for, request, render_template, make_response
import json
import socket
import sys
app = Flask(__name__)

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect(("127.0.0.1", 4444))
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
        response.set_cookie("user", user, max_age=60)
        response.set_cookie("key", key, max_age=60)
        return response
    return redirect(url_for("main"))

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
    return "main page"

if __name__ == "__main__":
    app.run(debug=True)
