# management-material
Management Material downloads (Visora VGS)

## Browser version

Every published release also gets a browser version, built by `.github/workflows/web-build.yml`: it takes the game pack
from the release's Mac download, pairs it with Godot's official web engine for the same engine version
(`tools/web/build_web.py`) and attaches the result to the release as `web-*` files. The Windows and Mac downloads are
untouched. visoravgs.com serves the latest one at `/play/<game>/`, with touch controls on phones and an
Add to Home Screen install.
