r"""
-- MegaHack Crack Script --

Tested for the following MH versions: v9.0.3, v9.0.7, v9.0.9, v9.0.11, v9.1.0-beta.2, v9.1.0-beta.7
"""

import platform
import argparse
import ctypes
import uuid
import os
import re
import zipfile
import io
import json
import time
import base64
import functools
import shutil
import winreg  # <-- THÊM: để đọc registry Steam
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from textwrap import dedent
from contextlib import contextmanager

err = lambda msg: print(f"[ERROR] {msg}") or exit(1)
warn = lambda msg: print(f"[WARNING] {msg}")

if platform.system().lower() != 'windows':
    err(f"This crack is meant for windows versions of Mega Hack. {platform.system()} is not supported.")

# ---------- Command line arguments ----------
def parse_version(version_str: str):
    version_str, _, _ = version_str.partition(" ")
    pattern = r'^v(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta)\.(\d+))?$'
    match = re.match(pattern, version_str)
    if not match:
        raise ValueError(f"Invalid version string: {version_str}")
    major, minor, patch, pre_type, pre_num = match.groups()
    pre_version = {'alpha': 0, 'beta': 1}.get(pre_type, 2)
    return tuple(map(int, (major, minor, patch, pre_version, pre_num or 0)))

parser = argparse.ArgumentParser()
parser.add_argument('--mh-version', default='latest', help='Specify version (default: latest)')
parser.add_argument('--standalone', action='store_true', help='Set if selected version should be a standalone version')
parser.add_argument('--gd-path', help='Manually specify Geometry Dash installation path (bypasses auto-detection)')

args = parser.parse_args()
MH_VERSION = args.mh_version
USE_GEODE = not args.standalone
MANUAL_PATH = args.gd_path

# ---------- Auto-detection of Geometry Dash path ----------
def find_steam_game(app_id):
    """Find game via Steam libraries (returns Path or None)"""
    steam_path = None
    for key_path in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            steam_path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
            break
        except FileNotFoundError:
            continue
    if not steam_path:
        return None

    libraries = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    if vdf_path.exists():
        content = vdf_path.read_text(encoding='utf-8')
        paths = re.findall(r'"path"\s+"([^"]+)"', content)
        libraries.extend(map(Path, paths))

    for lib in libraries:
        manifest = lib / "steamapps" / f"appmanifest_{app_id}.acf"
        if manifest.exists():
            content = manifest.read_text(encoding='utf-8')
            match = re.search(r'"installdir"\s+"([^"]+)"', content)
            if match:
                return lib / "steamapps" / "common" / match.group(1)
    return None

def find_geometry_dash():
    """Try to locate Geometry Dash installation."""
    # 1. If user provided manual path, use it
    if MANUAL_PATH:
        path = Path(MANUAL_PATH)
        if path.joinpath("GeometryDash.exe").exists():
            return path
        else:
            err(f"Provided path does not contain GeometryDash.exe: {path}")

    # 2. Check Steam installation
    steam_path = find_steam_game("322170")
    if steam_path and steam_path.joinpath("GeometryDash.exe").exists():
        return steam_path

    # 3. Check common custom locations
    common_locations = [
        Path("D:/Geometry Dash"),
        Path("C:/Program Files/Geometry Dash"),
        Path("C:/Program Files (x86)/Geometry Dash"),
        Path("C:/Games/Geometry Dash"),
        Path("D:/Games/Geometry Dash"),
        Path.home() / "Desktop/Geometry Dash",
        Path.home() / "Documents/Geometry Dash",
    ]
    for loc in common_locations:
        if loc.joinpath("GeometryDash.exe").exists():
            return loc

    # 4. If still not found, ask user
    print("Geometry Dash installation not found automatically.")
    while True:
        user_input = input("Please enter the full path to your Geometry Dash folder: ").strip()
        if user_input:
            path = Path(user_input)
            if path.joinpath("GeometryDash.exe").exists():
                return path
            else:
                print("That folder does not contain GeometryDash.exe. Try again.")
        else:
            err("No path provided. Exiting.")

# Lấy đường dẫn
GD_PATH = find_geometry_dash()
print(f"Found Geometry Dash installation at '{GD_PATH}'")

# ---------- AppData directory ----------
FOLDERID_LocalAppData = uuid.UUID("{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}").bytes_le
appdata_dir_buf = ctypes.c_wchar_p()

if ctypes.windll.shell32.SHGetKnownFolderPath(
    ctypes.byref(ctypes.create_string_buffer(FOLDERID_LocalAppData, 16)),
    0, 0,
    ctypes.byref(appdata_dir_buf)
):
    warn("Failed to find local appdata using SHGetKnownFolderPath. Trying %LOCALAPPDATA%.")
    LOCALAPPDATA = os.getenv("LOCALAPPDATA")
    if not LOCALAPPDATA:
        err("Unable to find local AppData directory.")
else:
    LOCALAPPDATA = appdata_dir_buf.value

LOCALAPPDATA = Path(LOCALAPPDATA)
print(f"Found local appdata directory at '{LOCALAPPDATA}'")

# ---------- Download & patch ----------
CWD = Path(__file__).parent
os.chdir(str(CWD))
print = functools.partial(print, flush=True)

@contextmanager
def progress_log(msg: str):
    print(msg, end="... ")
    success = False
    try:
        yield
        success = True
    finally:
        print("Done!" if success else "Failed.")

INSTALL_JSON_URL = "https://absolllute.com/api/mega_hack/v9/install.json"
USER_AGENT = ""

r = urlopen(Request(INSTALL_JSON_URL, headers={"User-Agent": USER_AGENT}))
if r.status != 200:
    err(f"Unable to get installation json. Status Code: {r.status}")

cur_package = json.load(r)["packages"][0]
if cur_package["name"] != "Mega Hack v9":
    warn(f"This was tested for Mega Hack v9, most recent version seems to now be {cur_package['name']}")

def find_bundle(bundles: list[dict]):
    global MH_VERSION, USE_GEODE
    if MH_VERSION == 'latest':
        return bundles[0]

    found_other = False
    for bundle in bundles:
        if bundle["name"] == MH_VERSION:
            if bundle["geode"] != USE_GEODE:
                found_other = True
            else:
                return bundle

    if found_other:
        if USE_GEODE:
            warn(f"Found entry for '{MH_VERSION}' but it was the standalone version. Try rerunning with `--standalone`")
        else:
            warn(f"Found entry for '{MH_VERSION}' but it was the geode version. Try rerunning without `--standalone`")
    return None

cur_bundle = find_bundle(cur_package["bundles"])
if not cur_bundle:
    err(f"Unable to find bundle information for '{MH_VERSION}' ({'GEODE' if USE_GEODE else 'STANDALONE'})")

group = cur_bundle["group"]
filename = cur_bundle["file"]
MEGAHACK_URL = f"https://absolllute.com/api/mega_hack/v9/files/{group}/{filename}"

with progress_log(f"Downloading {cur_bundle['name']}"):
    try:
        with urlopen(Request(MEGAHACK_URL, headers={"User-Agent": USER_AGENT})) as r:
            megahack_zip = r.read()
    except HTTPError as e:
        err(f"HTTP error: {e.code}")
    except URLError as e:
        err(f"URL error: {e.reason} - {str(e)}")

# ---------- Patch patterns ----------
ID_CHECK_PAT = re.compile(rb'\x56\x57\x48\x83\xEC.\x48\x83\x79\x10\x40', re.DOTALL | re.MULTILINE)
JSON_SIGNATURE_CHECK_PAT = re.compile(rb'\x55\x41\x56\x56\x57\x53\x48\x83\xEC.\x48\x8D\x6C\x24.\x48\xC7\x45.........\x0F\x84....\x4C\x89\xC7', re.DOTALL | re.MULTILINE)
KEY_BYBASS_PAT = re.compile(rb'(?<=.\x10\x00\x00\x00)\xE8....(?=\x48\x83\x7F)', re.DOTALL | re.MULTILINE)
BYPASS_VERIFY_PAT = re.compile(br'\x55\x41\x57\x41\x56\x56\x57\x53\x48\x81\xEC....\x48\x8D\xAC\x24....\x48\xC7\x85........\x48\x89\xD7\x48\x89\xCB', re.MULTILINE | re.DOTALL)

PATCH_DATA1 = b"".join([b"\xb8\x01\x00\x00\x00", b"\xc3"])
PATCH_DATA2 = b"".join([b"\xb8\x00\x00\x00\x00"])
PATCH_DATA3 = b"".join([b"\xc3"])

def patch_dll(data: bytes):
    def apply_patch(pattern, patch, min_version=None):
        nonlocal data
        if min_version and parse_version(MH_VERSION) < parse_version(min_version):
            return True
        new_data = pattern.sub(lambda m: patch + m.group(0)[len(patch):], data, 1)
        changed = data != new_data
        data = new_data
        return changed

    if not apply_patch(ID_CHECK_PAT, PATCH_DATA1):
        err("Failed to find pattern for the id check!")
    if not apply_patch(JSON_SIGNATURE_CHECK_PAT, PATCH_DATA1):
        err("Failed to find pattern for the json signature check!")
    if not apply_patch(KEY_BYBASS_PAT, PATCH_DATA2):
        err("Failed to find pattern for the key bypass!")
    if not apply_patch(BYPASS_VERIFY_PAT, PATCH_DATA3, "v9.1.0-beta.2"):
        err("Failed to find pattern for the verification bypass!")
    return data

# ---------- Handlers ----------
def handle_standalone():
    with progress_log("Extracting zip file and patching"):
        with zipfile.ZipFile(io.BytesIO(megahack_zip), 'r') as zf:
            for item in zf.infolist():
                filename = item.filename
                if filename.endswith("/"):
                    (GD_PATH / filename.rstrip("/")).mkdir(parents=True, exist_ok=True)
                else:
                    data = zf.read(filename)
                    if filename == "hackpro.dll":
                        data = patch_dll(data)
                    (GD_PATH / item.filename).write_bytes(data)
    return output_message()

def handle_geode():
    with progress_log("Extracting geode file and patching"):
        OUT_FILENAME = "absolllute.hackmega.geode"
        with zipfile.ZipFile(io.BytesIO(megahack_zip), 'r') as zip_in, \
             zipfile.ZipFile(OUT_FILENAME, 'w') as zip_out:
            for item in zip_in.infolist():
                filename = item.filename
                data = zip_in.read(filename)
                if filename == "absolllute.megahack.dll":
                    data = patch_dll(data)
                    item.filename = OUT_FILENAME.replace(".geode", ".dll")
                elif filename == "mod.json":
                    mod = json.loads(data)
                    mod["id"] = "absolllute.hackmega"
                    mod["name"] = "HackMega"
                    mod["description"] = "Totally new software..."
                    data = json.dumps(mod, indent="\t").encode()
                zip_out.writestr(item, data)

    GEODE_DIR = GD_PATH / "geode" / "mods"
    if not GEODE_DIR.is_dir():
        warn("Geode mods folder not found! Please install Geode first.")
        return output_message(geode_copied=False)

    with progress_log("Copying geode to mods folder"):
        shutil.copy(OUT_FILENAME, str(GEODE_DIR / OUT_FILENAME))
    return output_message(geode_copied=True)

def output_message(geode_copied=None):
    BORDER = '#' * get_terminal_width()
    msg = f"\n{BORDER}\nCracking process finished!\n* License file created in {mh_local_dir} and {CWD}.\n"
    if geode_copied is True:
        msg += "* The cracked geode was copied to the mods folder. Press Tab in-game to open the mod menu.\n"
    elif geode_copied is False:
        msg += "* Geode was not found. After installing Geode, copy the .geode file manually.\n"
    msg += BORDER
    return msg

# ---------- License creation ----------
with progress_log("Creating fake license file"):
    mh_local_dir = LOCALAPPDATA / "absolllute.megahack"
    mh_local_dir.mkdir(parents=True, exist_ok=True)
    mh_license_path = mh_local_dir / "license"
    mh_license_fallback_path = CWD / "license"

    EXPECTED_CHACHA_KEY = bytes.fromhex("0E 84 1F A5 BF E5 CE 8F C9 1E B1 1A DD 1D CE F6 94 04 5B EE AF CF 52 1B F4 34 1D 39 97 C1 C2 19")

    def random_hex(length):
        assert length % 2 == 0
        return os.urandom(length // 2).hex().upper()

    signature = os.urandom(256)
    identifier = random_hex(64)
    token = random_hex(32)
    secret = random_hex(32)

    data = {
        "id": identifier,
        "token": token,
        "secret": secret,
        "timestamp": str(int(time.time())),
        "guid2": EXPECTED_CHACHA_KEY.hex().upper()
    }

    data_dump = json.dumps(data, separators=(",", ":"))
    license = {
        "data": base64.b64encode(data_dump.encode()).decode(),
        "sig": base64.b64encode(signature).decode(),
        "token": token
    }
    license_str = json.dumps(license, separators=(",", ":"))
    mh_license_path.write_text(license_str)
    mh_license_fallback_path.write_text(license_str)

# ---------- Final ----------
def get_terminal_width():
    try:
        return shutil.get_terminal_size().columns - 1
    except OSError:
        return 80

print(handle_geode() if USE_GEODE else handle_standalone())