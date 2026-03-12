r"""
-- MegaHack Crack Script --

Tested for the following MH versions: v9.0.3, v9.0.7, v9.0.9, v9.0.11, v9.1.0-beta.2, v9.1.0-beta.7, v9.1.1
"""

import platform

err = lambda msg: print(f"[ERROR] {msg}") or exit(1)
warn = lambda msg: print(f"[WARNING] {msg}")

if platform.system().lower() != 'windows':
    err(f"This crack is meant for windows versions of Mega Hack. {platform.system()} is not supported.")

# Get selected version from cli
import argparse
import re

def parse_version(version_str: str):
    # Remove " (Standalone)" or " (Geode)" from the string
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

args = parser.parse_args()
MH_VERSION = args.mh_version
USE_GEODE = not args.standalone # skip entries that have `geode: true`

# Find Geometry Dash's installation directory
from pathlib import Path
import winreg
import os
import tkinter as tk
from tkinter import filedialog

# ---------- Auto‑detection improvements ----------
CACHE_FILE = Path(__file__).parent / "gd_path.txt"

def load_cached_path():
    """Đọc đường dẫn đã lưu từ file cache, nếu file tồn tại và GeometryDash.exe vẫn còn."""
    if CACHE_FILE.exists():
        try:
            path = Path(CACHE_FILE.read_text().strip())
            if path.joinpath("GeometryDash.exe").exists():
                return path
        except:
            pass
    return None

def save_cached_path(path: Path):
    """Ghi đường dẫn thành công vào file cache."""
    try:
        CACHE_FILE.write_text(str(path))
    except:
        pass  # không gây lỗi nếu không ghi được

def get_steam_path():
    for path in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            return Path(winreg.QueryValueEx(key, "InstallPath")[0])
        except FileNotFoundError:
            continue

    warn("Unable to find Steam installation directory in your registry")
    return None

def get_steam_libraries(steam_path: Path):
    libraries = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    
    if vdf_path.exists():
        content = vdf_path.read_text(encoding='utf-8')
        # Find all "path" entries
        paths = re.findall(r'"path"\s+"([^"]+)"', content)
        libraries.extend(map(Path, paths))
    
    return libraries

def find_game_steam(app_id) -> Path | None:
    steam_path = get_steam_path()
    if not steam_path:
        return None

    print(f"Got a steam installation path of '{steam_path}'")
    
    for library in get_steam_libraries(steam_path):
        manifest = library / "steamapps" / f"appmanifest_{app_id}.acf"
        if manifest.exists():
            content = manifest.read_text(encoding='utf-8')
            match = re.search(r'"installdir"\s+"([^"]+)"', content)
            if match:
                return library / "steamapps" / "common" / match.group(1)

    return None

def find_common_locations():
    """Kiểm tra các thư mục cài đặt thủ công phổ biến."""
    common_paths = [
        Path("D:/Geometry Dash"),
        Path("C:/Program Files/Geometry Dash"),
        Path("C:/Program Files (x86)/Geometry Dash"),
        Path("C:/Games/Geometry Dash"),
        Path("D:/Games/Geometry Dash"),
        Path.home() / "Desktop/Geometry Dash",
        Path.home() / "Documents/Geometry Dash",
        Path(__file__).parent,  # cùng thư mục với script (nếu bạn để game ở đây)
    ]
    for loc in common_paths:
        if loc.joinpath("GeometryDash.exe").exists():
            return loc
    return None

# --- Quy trình tìm kiếm tự động ---
GD_PATH = None

# 1. Kiểm tra cache trước (nếu có)
cached = load_cached_path()
if cached:
    GD_PATH = cached
    print(f"Using cached Geometry Dash path: '{GD_PATH}'")

# 2. Nếu cache không hợp lệ, thử tìm qua Steam
if not GD_PATH:
    steam_path = find_game_steam("322170")
    if steam_path and steam_path.joinpath("GeometryDash.exe").exists():
        GD_PATH = steam_path
        print(f"Found Geometry Dash via Steam at '{GD_PATH}'")

# 3. Nếu chưa tìm thấy, thử các vị trí phổ biến
if not GD_PATH:
    common = find_common_locations()
    if common:
        GD_PATH = common
        print(f"Found Geometry Dash in common location '{GD_PATH}'")

# 4. Nếu vẫn không thấy, mở hộp thoại để người dùng chọn
if not GD_PATH:
    print("Geometry Dash not found automatically.")
    print("Please select your Geometry Dash folder manually in the window that opens...")
    
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        selected_dir = filedialog.askdirectory(title="Select the folder containing GeometryDash.exe")
        root.destroy()
        
        if selected_dir:
            GD_PATH = Path(selected_dir)
        else:
            err("No folder selected. Script aborted.")
    except Exception as e:
        err(f"Failed to open folder selection window: {e}")

# Kiểm tra lần cuối
if GD_PATH is None or not (GD_PATH / "GeometryDash.exe").exists():
    err(f"GeometryDash.exe not found in '{GD_PATH}'. Cannot proceed.")

# Lưu lại đường dẫn thành công vào cache cho lần sau
save_cached_path(GD_PATH)

print(f"Targeting Geometry Dash installation at '{GD_PATH}'")

# ---------- Phần còn lại giữ nguyên ----------
# MegaHack uses SHGetKnownFolderPath to find the local appdata directory...
import ctypes
import uuid

FOLDERID_LocalAppData =  uuid.UUID("{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}").bytes_le
appdata_dir_buf = ctypes.c_wchar_p()

if ctypes.windll.shell32.SHGetKnownFolderPath(
    ctypes.byref(ctypes.create_string_buffer(FOLDERID_LocalAppData, 16)),
    0, 0,
    ctypes.byref(appdata_dir_buf)
):
    warn("Failed to find the local appdata directory using SHGetKnownFolderPath. Trying %LOCALAPPDATA%.")
    LOCALAPPDATA = os.getenv("LOCALAPPDATA", None)
    if not LOCALAPPDATA:
        err("Unable to find the local AppData directory with SHGetKnownFolderPath or %LOCALAPPDATA%. Aborting.")
else:
    LOCALAPPDATA = appdata_dir_buf.value

LOCALAPPDATA = Path(LOCALAPPDATA)
print(f"Found the local appdata directory at '{LOCALAPPDATA!s}'")

# the rest of the shit we need
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from textwrap import dedent
from contextlib import contextmanager
import zipfile
import io
import json
import time
import base64
import functools
import shutil

# convenience
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

# Download selected version

# json containing all megahack version and information
INSTALL_JSON_URL = "https://absolllute.com/api/mega_hack/v9/install.json"

# absolllute.com blocks user agents containing `Python-urllib` lmfao
# if the empty UA ever starts 403'ing, just copy one from online somewhere
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

MEGAHACK_URL = "https://absolllute.com/api/mega_hack/v9/files/{}/{}".format(group, filename)

with progress_log(f"Downloading {cur_bundle['name']}"):
    try:
        with urlopen(Request(MEGAHACK_URL, headers={"User-Agent": USER_AGENT})) as r:
            megahack_zip = r.read()
    except HTTPError as e:
        err(f"HTTP error: {e.code}")
    except URLError as e:
        err(f"URL error: {e.reason} - {str(e)}")

# Patch information
# Patterns tested on v9.0.3, v9.0.7, v9.0.9, v9.0.11, v9.1.0, and v9.1.1

ID_CHECK_PAT = re.compile(rb'\x56\x57\x48\x83\xEC.\x48\x83\x79\x10\x40', re.DOTALL | re.MULTILINE)
JSON_SIGNATURE_CHECK_PAT = re.compile(rb'\x55\x41\x56\x56\x57\x53\x48\x83\xEC.\x48\x8D\x6C\x24.\x48\xC7\x45.........\x0F\x84....\x4C\x89\xC7', re.DOTALL | re.MULTILINE)
KEY_BYBASS_PAT = re.compile(rb'(?<=.\x10\x00\x00\x00)\xE8....(?=\x48\x83\x7F)', re.DOTALL | re.MULTILINE)
BYPASS_VERIFY_PAT = re.compile(br'\x55\x41\x57\x41\x56\x56\x57\x53\x48\x81\xEC....\x48\x8D\xAC\x24....\x48\xC7\x85........\x48\x89\xD7\x48\x89\xCB', re.MULTILINE | re.DOTALL)

PATCH_DATA1 = b"".join([
    b"\xb8\x01\x00\x00\x00", # mov eax, 1
    b"\xc3", # ret
])

PATCH_DATA2 = b"".join([
    b"\xb8\x00\x00\x00\x00", # mov eax, 0
])

PATCH_DATA3 = b"".join([
    b"\xc3", # ret
])

def patch_dll(data: bytes):
    def apply_patch(pattern, patch, min_version=None):
        nonlocal data
        if min_version and parse_version(MH_VERSION) < parse_version(min_version):
            # No need to apply
            return True
        
        return data != (data := pattern.sub(lambda m: patch + m.group(0)[len(patch):], data, 1))
    
    if not apply_patch(ID_CHECK_PAT, PATCH_DATA1):
        err("Failed to find pattern for the id check!")
    if not apply_patch(JSON_SIGNATURE_CHECK_PAT, PATCH_DATA1):
        err("Failed to find pattern for the json signature check!")
    if not apply_patch(KEY_BYBASS_PAT, PATCH_DATA2):
        err("Failed to find pattern for the key bypass!")
    if not apply_patch(BYPASS_VERIFY_PAT, PATCH_DATA3, "v9.1.0-beta.2"):
        err("Failed to find pattern for the verification bypass!")
    
    return data

def handle_standalone():
    # Extract the zip
    with progress_log("Extracting zip file and patching"):
        with zipfile.ZipFile(io.BytesIO(megahack_zip), 'r') as zf:
            # Patching and unpacking shit
            for item in zf.infolist():
                filename = item.filename

                # Directories always come before the contents within the directories, so it's safe to extract sequentially
                if filename.endswith("/"):
                    (GD_PATH / filename.rstrip("/")).mkdir(parents=True, exist_ok=True)
                else:
                    data = zf.read(filename)            
                    match filename:
                        case "hackpro.dll":
                            data = patch_dll(data)

                    (GD_PATH / item.filename).write_bytes(data)
    
    BORDER = '#' * get_terminal_width()
    return dedent(f"""
        {BORDER}
        Cracking process finished!
        * The license file was created in {mh_local_dir} and {CWD}.
        * If you don't see the license file in {mh_local_dir}, copy the one in {CWD} to there.
        {BORDER}
    """)

def handle_geode():
    with progress_log("Extracting geode file and patching"):
        OUT_FILENAME = "absolllute.hackmega.geode"
        with zipfile.ZipFile(io.BytesIO(megahack_zip), 'r') as zip_in, \
            zipfile.ZipFile(OUT_FILENAME, 'w') as zip_out:
            
            # Patching shit
            for item in zip_in.infolist():
                filename = item.filename
                data = zip_in.read(filename)
                
                match filename:
                    case "absolllute.megahack.dll":
                        data = patch_dll(data)

                        # need to update the filename too
                        item.filename = OUT_FILENAME.replace(".geode", ".dll")
                    case "mod.json":
                        # we need to modify the id to match the output filename, all the other changes are cosmetic
                        mod = json.loads(data)
                        mod["id"] = "absolllute.hackmega"
                        mod["name"] = "HackMega"
                        mod["description"] = "Totally new software..."
                        data = json.dumps(mod, indent="\t").encode()
                
                zip_out.writestr(item, data)
    
    # Transfer it over to the geode folder now
    GEODE_DIR = GD_PATH / "geode" / "mods"
    if not GEODE_DIR.is_dir():
        warn("Unable to find geode mods folder! Please make sure to install geode after this script finishes running.")
        return
    
    copied_geode = False
    with progress_log("Copying geode to mods folder"):
        shutil.copy(OUT_FILENAME, str(GEODE_DIR / OUT_FILENAME))
        copied_geode = True
    
    geode_msg = (
        "* The cracked geode was copied to the mods folder. You should be able to open the game and press tab to see the mod menu!"
        if copied_geode else
        "* Geode was not found during the cracking process. After installing geode, either rerun this script or copy the newly created .geode file manually."
    )
    
    BORDER = '#' * get_terminal_width()
    return dedent(f"""
        {BORDER}
        Cracking process finished!
        * The license file was created in {mh_local_dir} and {CWD}.
        * If you don't see the license file in {mh_local_dir}, copy the one in {CWD} to there.
        {geode_msg}
        {BORDER}
    """)

# Write a now valid license to the expected directory
with progress_log("Creating fake license file"):
    mh_local_dir = LOCALAPPDATA / "absolllute.megahack"
    mh_local_dir.mkdir(parents=True, exist_ok=True)
    mh_license_path = mh_local_dir / "license"
    mh_license_fallback_path = CWD / "license"

    EXPECTED_CHACHA_KEY = bytes.fromhex("0E 84 1F A5 BF E5 CE 8F C9 1E B1 1A DD 1D CE F6 94 04 5B EE AF CF 52 1B F4 34 1D 39 97 C1 C2 19")

    def random_hex(length):
        assert length % 2 == 0
        return os.urandom(length // 2).hex().upper()

    signature = os.urandom(256) # we bypass this check, so just set it to whatever
    identifier = random_hex(64) # this is possible to generate legitamately, but it really bloats the code bc it involves a lot of winapi stuff
    token = random_hex(32) # honestly, I have no idea what this is for, it's not used anywhere from what I can tell
    secret = random_hex(32) # same with this, couldn't find anywhere that reads this

    data = {
        "id": identifier,
        "token": token,
        "secret": secret,
        "timestamp": str(int(time.time())),
        # this is used to decrypt some resources or something else important (didn't really dig into it) but it's requried to be this
        "guid2": EXPECTED_CHACHA_KEY.hex().upper()
    }

    data_dump = json.dumps(data, separators=(",", ":"))

    license = {
        "data": base64.b64encode(data_dump.encode()).decode('utf-8'),
        "sig": base64.b64encode(signature).decode('utf-8'),
        "token": token
    }

    license_str = json.dumps(license, separators=(",", ":"))
    mh_license_path.write_text(license_str)
    mh_license_fallback_path.write_text(license_str)

    assert mh_license_path.exists() or mh_license_fallback_path.exists()

# Yay all done, past this point is just printing stuff to make it nice and pretty

def get_terminal_width():
    try:
        size = shutil.get_terminal_size()
        return size.columns - 1
    except OSError:
        # Fallback if the terminal size cannot be determined
        return 80

print(handle_geode() if USE_GEODE else handle_standalone())