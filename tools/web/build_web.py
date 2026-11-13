#!/usr/bin/env python3
"""Builds the browser version of the game from a release's Mac download.

The Mac app carries the game pack (.pck) that every platform runs. Godot's official web engine (the "nothreads" web
template for the same engine version, so it works on iPhone and any host without special headers) runs that same pack
in the browser. Nothing in the game is rebuilt or changed; the output is uploaded to the same GitHub release as web-*.

usage: build_web.py <tag> <mac.zip> <out_dir>
"""
import io
import json
import os
import re
import struct
import sys
import urllib.request
import zipfile

TEMPLATES = "https://github.com/godotengine/godot/releases/download/{v}-stable/Godot_v{v}-stable_export_templates.tpz"
WEB_FILES = ["godot.js", "godot.wasm", "godot.audio.worklet.js", "godot.audio.position.worklet.js"]


class RemoteFile(io.RawIOBase):
    """Seekable read-only view of a URL, so one ~1 GB template archive yields its 10 MB web template via ranges."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as r:
            self.size = int(r.headers["Content-Length"])

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def readinto(self, b):
        if self.pos >= self.size:
            return 0
        end = min(self.pos + len(b), self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        b[: len(data)] = data
        self.pos += len(data)
        return len(data)


def main(tag, mac_zip, out):
    os.makedirs(out, exist_ok=True)
    with zipfile.ZipFile(mac_zip) as z:
        pcks = [n for n in z.namelist() if n.endswith(".pck")]
        if len(pcks) != 1:
            sys.exit(f"expected one .pck in {mac_zip}, found {pcks}")
        pck = z.read(pcks[0])
    magic, _fmt, major, minor, patch = struct.unpack("<4s4I", pck[:20])
    if magic != b"GDPC":
        sys.exit("not a Godot pack")
    engine = f"{major}.{minor}" + (f".{patch}" if patch else "")
    print(f"pack {pcks[0]}: {len(pck)} bytes, Godot {engine}")

    cache = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), f"godot-web-{engine}.zip")
    if not os.path.exists(cache):
        tpz = zipfile.ZipFile(io.BufferedReader(RemoteFile(TEMPLATES.format(v=engine)), buffer_size=1 << 20))
        with open(cache, "wb") as f:
            f.write(tpz.read("templates/web_nothreads_release.zip"))
    sizes = {}
    with zipfile.ZipFile(cache) as web:
        for name in WEB_FILES:
            data = web.read(name)
            with open(os.path.join(out, "web-" + name), "wb") as f:
                f.write(data)
            sizes[name] = len(data)
    with open(os.path.join(out, "web-game.pck"), "wb") as f:
        f.write(pck)
    sizes["game.pck"] = len(pck)
    version = re.sub(r"^[^0-9]*", "", tag)
    build = {"tag": tag, "version": version, "engine": engine, "files": {k: sizes[k] for k in ("godot.wasm", "game.pck")}}
    with open(os.path.join(out, "web-build.json"), "w") as f:
        json.dump(build, f)
    print(json.dumps(build))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
