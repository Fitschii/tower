"""Small, ephemeral public lobby directory. Gameplay stays with the ENet host."""
import ipaddress
import json
import os
import secrets
import threading
import time
from http import HTTPStatus
from wsgiref.simple_server import make_server

PROTOCOL = "tower-coop-3"
MAPS = {"emerald", "gorge", "frosthold", "glacier", "undercroft"}
DIFFICULTIES = {"easy", "normal", "hard", "nightmare"}
TTL = 65


class Directory:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.rooms = {}
        self.rates = {}
        self.lock = threading.Lock()

    def __call__(self, env, start_response):
        try:
            with self.lock:
                status, result = self.handle(env)
        except (ValueError, UnicodeError, json.JSONDecodeError):
            status, result = 400, {"error": "Invalid request"}
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        start_response(f"{status} {HTTPStatus(status).phrase}", [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))), ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [body]

    def source_ip(self, env):
        address = env.get("REMOTE_ADDR", "127.0.0.1")
        # Enable only when deployed behind the Render ingress, not on a public bare server.
        if os.getenv("TRUST_RENDER_PROXY") == "1":
            forwarded = env.get("HTTP_X_FORWARDED_FOR", "").split(",")
            if forwarded[0].strip():
                address = forwarded[0].strip()
        return str(ipaddress.ip_address(address))

    def handle(self, env):
        now = self.clock()
        self.rooms = {k: v for k, v in self.rooms.items() if now - v["seen"] < TTL}
        self.rates = {k: v for k, v in self.rates.items() if now - v[0] < 60}
        method, path = env["REQUEST_METHOD"], env["PATH_INFO"]
        if method == "GET" and path in ("/", "/health"):
            return 200, {"ok": True, "service": "Tower Ascension Server List", "protocol": PROTOCOL}
        # Rate-limit by transport peer as well, so forged forwarding headers cannot bypass it.
        key = env.get("REMOTE_ADDR", "unknown")
        start, count = self.rates.get(key, (now, 0))
        if count >= 2400 or (key not in self.rates and len(self.rates) >= 4096):
            return 429, {"error": "Please retry later"}
        self.rates[key] = (start, count + 1)
        if method == "GET" and path == "/v1/rooms":
            return 200, {"rooms": [v["public"] for v in self.rooms.values() if v["public"]["players"] < 4], "ttl": TTL}
        room_id = path.removeprefix("/v1/rooms/") if path.startswith("/v1/rooms/") else ""
        if room_id:
            room = self.rooms.get(room_id)
            if room is None:
                return 404, {"error": "Room expired"}
            token = env.get("HTTP_AUTHORIZATION", "").removeprefix("Bearer ")
            if not token.isascii() or not secrets.compare_digest(room["token"], token):
                return 403, {"error": "Not your room"}
            if method == "DELETE":
                del self.rooms[room_id]
                return 200, {"ok": True}
        if (method == "POST" and path == "/v1/rooms") or (method == "PATCH" and room_id):
            length = int(env.get("CONTENT_LENGTH") or "0")
            if length < 1 or length > 2048:
                return 413, {"error": "Body too large or missing"}
            data = json.loads(env["wsgi.input"].read(length))
            if not isinstance(data, dict):
                raise ValueError()
            if data.get("protocol") != PROTOCOL:
                return 409, {"error": "Different game version"}
            name = data.get("name")
            port, players = data.get("port"), data.get("players")
            if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 24
                    or any(ord(c) < 32 for c in name) or type(port) is not int
                    or not 1024 <= port <= 65535 or type(players) is not int
                    or not 1 <= players <= 4 or not isinstance(data.get("map"), str)
                    or not isinstance(data.get("difficulty"), str) or data.get("map") not in MAPS
                    or data.get("difficulty") not in DIFFICULTIES):
                raise ValueError()
            ip = self.source_ip(env)
            if method == "POST":
                if len(self.rooms) >= 256 or sum(v["owner"] == ip for v in self.rooms.values()) >= 8:
                    return 429, {"error": "Room limit reached"}
                room_id = secrets.token_urlsafe(18)
                room = {"token": secrets.token_urlsafe(32), "owner": ip}
                self.rooms[room_id] = room
            room["seen"] = now
            room["public"] = {k: data[k] for k in ("protocol", "name", "port", "players", "map", "difficulty")}
            room["public"].update(room=room_id, ip=ip)
            return 200, {"room": room_id, "token": room["token"], "ttl": TTL}
        return 404, {"error": "Not found"}


app = Directory()

if __name__ == "__main__":
    # Local development only. Render uses Gunicorn with exactly one worker.
    port = int(os.getenv("PORT", "8765"))
    with make_server("127.0.0.1", port, app) as server:
        print(f"Test directory: http://127.0.0.1:{port}", flush=True)
        server.serve_forever()
