import io
import json
import unittest
from app import Directory, PROTOCOL


class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.app = Directory(lambda: self.now)
        self.data = dict(protocol=PROTOCOL, name="Test Host", port=24567,
                         players=1, map="emerald", difficulty="normal")

    def call(self, method, path, data=None, token=""):
        body = json.dumps(data).encode() if data is not None else b""
        env = {"REQUEST_METHOD": method, "PATH_INFO": path, "REMOTE_ADDR": "127.0.0.1",
               "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body),
               "HTTP_AUTHORIZATION": "Bearer " + token}
        status = []
        result = b"".join(self.app(env, lambda s, h: status.append(int(s[:3]))))
        return status[0], json.loads(result)

    def test_lifecycle_and_owner(self):
        code, room = self.call("POST", "/v1/rooms", self.data)
        self.assertEqual(code, 200)
        path = "/v1/rooms/" + room["room"]
        listing = self.call("GET", "/v1/rooms")[1]["rooms"]
        self.assertEqual(listing[0]["ip"], "127.0.0.1")
        self.assertNotIn("token", listing[0])
        self.assertEqual(self.call("DELETE", path, token="wrong")[0], 403)
        self.assertEqual(self.call("DELETE", path, token="ä")[0], 403)
        self.data["players"] = 4
        self.assertEqual(self.call("PATCH", path, self.data, room["token"])[0], 200)
        self.assertEqual(self.call("GET", "/v1/rooms")[1]["rooms"], [])
        self.assertEqual(self.call("DELETE", path, token=room["token"])[0], 200)

    def test_expiry_and_heartbeat(self):
        _, room = self.call("POST", "/v1/rooms", self.data)
        path = "/v1/rooms/" + room["room"]
        self.now = 60
        self.call("PATCH", path, self.data, room["token"])
        self.now = 70
        self.assertEqual(len(self.call("GET", "/v1/rooms")[1]["rooms"]), 1)
        self.now = 126
        self.assertEqual(self.call("GET", "/v1/rooms")[1]["rooms"], [])

    def test_validation_and_limits(self):
        for key, value in [("port", -1), ("players", True), ("map", []),
                           ("difficulty", {}), ("name", "x" * 25)]:
            data = dict(self.data, **{key: value})
            self.assertEqual(self.call("POST", "/v1/rooms", data)[0], 400)
        self.assertEqual(self.call("POST", "/v1/rooms", dict(self.data, protocol="old"))[0], 409)
        for _ in range(8):
            self.assertEqual(self.call("POST", "/v1/rooms", self.data)[0], 200)
        self.assertEqual(self.call("POST", "/v1/rooms", self.data)[0], 429)
        self.assertEqual(self.call("GET", "/health")[0], 200)


if __name__ == "__main__":
    unittest.main()
