r"""
-- MegaHack Crack Script --

Tested for MH versions: v9.0.3, v9.0.7, v9.0.9, v9.0.11, v9.1.0-beta.2, v9.1.0-beta.7, v9.1.1, v9.1.3+
Works with Steam and cracked Geometry Dash installations (auto-detects).
Interactive version selection using arrow keys.
"""

import platform

err = lambda msg: print(f"[ERROR] {msg}") or exit(1)
warn = lambda msg: print(f"[WARNING] {msg}")

if platform.system().lower() != 'windows':
    err("This crack is meant for windows versions of Mega Hack. "
        f"{platform.system()} is not supported.")

# ---------- Command line arguments ----------
import argparse
from pathlib import Path
import re

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
parser.add_argument('--mh-version', default=None,
                    help='Specify version (e.g., v9.1.3). If omitted, an interactive menu will appear.')
parser.add_argument('--standalone', action='store_true',
                    help='Use standalone version instead of Geode')
parser.add_argument('--gd-path', type=Path, default=None,
                    help='Manually specify Geometry Dash folder (optional)')
args = parser.parse_args()

MH_VERSION = args.mh_version
USE_GEODE = not args.standalone

# ---------- Geometry Dash location auto-detection ----------
import winreg
import os
from typing import Optional

def get_steam_path() -> Optional[Path]:
    for path in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            return Path(winreg.QueryValueEx(key, "InstallPath")[0])
        except FileNotFoundError:
            continue
    return None

def find_game_via_steam(app_id: str) -> Optional[Path]:
    steam_path = get_steam_path()
    if not steam_path:
        return None
    print(f"Steam found at: {steam_path}")
    libraries = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    if vdf_path.exists():
        content = vdf_path.read_text(encoding='utf-8')
        paths = re.findall(r'"path"\s+"([^"]+)"', content)
        libraries.extend(Path(p) for p in paths)
    for lib in libraries:
        manifest = lib / "steamapps" / f"appmanifest_{app_id}.acf"
        if manifest.exists():
            content = manifest.read_text(encoding='utf-8')
            match = re.search(r'"installdir"\s+"([^"]+)"', content)
            if match:
                return lib / "steamapps" / "common" / match.group(1)
    return None

def find_game_in_registry() -> Optional[Path]:
    uninstall_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    for root in uninstall_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        if "Geometry Dash" in display_name:
                            install_loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            if install_loc and (Path(install_loc) / "GeometryDash.exe").exists():
                                return Path(install_loc)
                    except (FileNotFoundError, OSError):
                        pass
                    finally:
                        subkey.Close()
                    i += 1
                except OSError:
                    break
        except Exception:
            continue
    return None

def scan_drives_for_gd() -> Optional[Path]:
    for letter in 'CDEFGHIJK':
        drive = f"{letter}:\\"
        if not os.path.exists(drive):
            continue
        gd_path = Path(drive) / "Geometry Dash"
        if gd_path.exists() and (gd_path / "GeometryDash.exe").exists():
            return gd_path
        games_path = Path(drive) / "Games" / "Geometry Dash"
        if games_path.exists() and (games_path / "GeometryDash.exe").exists():
            return games_path
    return None

def find_game_cracked() -> Optional[Path]:
    common_paths = [
        Path(os.getenv("PROGRAMFILES", "C:\\Program Files")) / "Geometry Dash",
        Path(os.getenv("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Geometry Dash",
        Path.home() / "Desktop" / "Geometry Dash",
        Path.home() / "Downloads" / "Geometry Dash",
        Path("C:\\Games\\Geometry Dash"),
        Path("D:\\Games\\Geometry Dash"),
        Path("E:\\Games\\Geometry Dash"),
        Path.cwd(),
        Path.cwd().parent,
    ]
    for path in common_paths:
        if (path / "GeometryDash.exe").exists():
            return path
    reg_path = find_game_in_registry()
    if reg_path:
        return reg_path
    drive_path = scan_drives_for_gd()
    if drive_path:
        return drive_path
    return None

if args.gd_path:
    GD_PATH = args.gd_path
    if not (GD_PATH / "GeometryDash.exe").exists():
        err(f"GeometryDash.exe not found in provided path: '{GD_PATH}'")
else:
    GD_PATH = find_game_via_steam("322170")
    if GD_PATH:
        print(f"Found Steam version at: {GD_PATH}")
    else:
        print("Steam not found or GD not installed there. Searching for cracked installation...")
        GD_PATH = find_game_cracked()
        if GD_PATH:
            print(f"Found cracked version at: {GD_PATH}")
        else:
            print("Could not automatically find Geometry Dash.")
            try:
                from tkinter import Tk, filedialog
                root = Tk()
                root.withdraw()
                folder = filedialog.askdirectory(mustexist=True,
                                                  title="Select the folder containing GeometryDash.exe")
                root.destroy()
                if not folder:
                    err("No folder selected. Aborting.")
                GD_PATH = Path(folder)
            except ImportError:
                err("Tkinter not available. Please specify the path with --gd-path")

if not (GD_PATH / "GeometryDash.exe").exists():
    err(f"GeometryDash.exe not found at '{GD_PATH}'")

print(f"Using Geometry Dash from: {GD_PATH}")

# ---------- Local AppData ----------
import ctypes
import uuid

FOLDERID_LocalAppData = uuid.UUID("{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}").bytes_le
appdata_dir_buf = ctypes.c_wchar_p()
if ctypes.windll.shell32.SHGetKnownFolderPath(
    ctypes.byref(ctypes.create_string_buffer(FOLDERID_LocalAppData, 16)),
    0, 0,
    ctypes.byref(appdata_dir_buf)
):
    warn("Failed to find local appdata via SHGetKnownFolderPath. Trying %LOCALAPPDATA%.")
    LOCALAPPDATA = os.getenv("LOCALAPPDATA")
    if not LOCALAPPDATA:
        err("Unable to find local AppData directory.")
else:
    LOCALAPPDATA = appdata_dir_buf.value
LOCALAPPDATA = Path(LOCALAPPDATA)
print(f"Local AppData: {LOCALAPPDATA}")

# ---------- Download version information ----------
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
import msvcrt
import sys

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

print("\nFetching available versions...")
try:
    r = urlopen(Request(INSTALL_JSON_URL, headers={"User-Agent": USER_AGENT}))
except Exception as e:
    err(f"Failed to fetch install.json: {e}")
if r.status != 200:
    err(f"Unable to get installation json. Status Code: {r.status}")

cur_package = json.load(r)["packages"][0]
if cur_package["name"] != "Mega Hack v9":
    warn(f"This was tested for Mega Hack v9, most recent version seems to be {cur_package['name']}")

bundles = cur_package.get("bundles", [])

# ---------- Interactive version selection with arrow keys ----------
def interactive_select(bundles, use_geode):
    """Display a menu navigable with arrow keys. Returns selected bundle."""
    # Filter by Geode/Standalone
    filtered = [b for b in bundles if b.get("geode", False) == use_geode]
    if not filtered:
        print(f"\nNo {'Geode' if use_geode else 'Standalone'} bundles found. Showing all bundles.")
        filtered = bundles
    if not filtered:
        err("No bundles available.")
    
    # Sort by version (newest first)
    filtered_sorted = sorted(filtered, key=lambda b: parse_version(b["name"]), reverse=True)
    
    current_index = 0
    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            # Clear screen and print menu
            os.system('cls')
            print("\n" + "=" * 60)
            print("Select Mega Hack version to install (use ↑/↓ arrows, Enter to confirm):")
            print("=" * 60)
            for i, bundle in enumerate(filtered_sorted):
                name = bundle["name"]
                geode_tag = " [Geode]" if bundle.get("geode") else " [Standalone]"
                prefix = "> " if i == current_index else "  "
                print(f"{prefix}{i+1}. {name}{geode_tag}")
            print("=" * 60)
            
            # Get key press
            key = msvcrt.getch()
            if key == b'\r':  # Enter
                return filtered_sorted[current_index]
            elif key == b'\xe0':  # Arrow key prefix
                key2 = msvcrt.getch()
                if key2 == b'H':  # Up arrow
                    current_index = (current_index - 1) % len(filtered_sorted)
                elif key2 == b'P':  # Down arrow
                    current_index = (current_index + 1) % len(filtered_sorted)
    finally:
        # Show cursor again
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

# Determine selected bundle
if MH_VERSION is None:
    selected_bundle = interactive_select(bundles, USE_GEODE)
    MH_VERSION = selected_bundle["name"]
else:
    # Find bundle by exact name (with optional type mismatch warning)
    def find_bundle_by_name(bundles, name, use_geode):
        for b in bundles:
            if b["name"] == name and b.get("geode", False) == use_geode:
                return b
        for b in bundles:
            if b["name"] == name:
                if b.get("geode", False) != use_geode:
                    warn(f"Found '{name}' but it is {'Geode' if b['geode'] else 'Standalone'}. "
                         f"Use {'' if b['geode'] else '--standalone'} flag.")
                return b
        return None
    selected_bundle = find_bundle_by_name(bundles, MH_VERSION, USE_GEODE)
    if not selected_bundle:
        err(f"Unable to find bundle named '{MH_VERSION}' with Geode={USE_GEODE}")

group = selected_bundle["group"]
filename = selected_bundle["file"]
VERSION_STRING = selected_bundle["name"]
print(f"\nSelected: {VERSION_STRING} (Geode={USE_GEODE})")

MEGAHACK_URL = f"https://absolllute.com/api/mega_hack/v9/files/{group}/{filename}"
with progress_log(f"Downloading {VERSION_STRING}"):
    try:
        with urlopen(Request(MEGAHACK_URL, headers={"User-Agent": USER_AGENT})) as r:
            megahack_zip = r.read()
    except HTTPError as e:
        err(f"HTTP error: {e.code}")
    except URLError as e:
        err(f"URL error: {e.reason}")

# ---------- Patching patterns ----------
ID_CHECK_PAT = re.compile(rb'\x56\x57\x48\x83\xEC.\x48\x83\x79\x10\x40', re.DOTALL | re.MULTILINE)
JSON_SIGNATURE_CHECK_PAT = re.compile(
    rb'\x55\x41\x56\x56\x57\x53\x48\x83\xEC.\x48\x8D\x6C\x24.\x48\xC7\x45.........\x0F\x84....\x4C\x89\xC7',
    re.DOTALL | re.MULTILINE)
KEY_BYBASS_PAT = re.compile(rb'(?<=.\x10\x00\x00\x00)\xE8....(?=\x48\x83\x7F)', re.DOTALL | re.MULTILINE)
BYPASS_VERIFY_PAT = re.compile(
    br'\x55\x41\x57\x41\x56\x56\x57\x53\x48\x81\xEC....\x48\x8D\xAC\x24....\x48\xC7\x85........\x48\x89\xD7\x48\x89\xCB',
    re.MULTILINE | re.DOTALL)

PATCH_DATA1 = b"\xb8\x01\x00\x00\x00\xc3"
PATCH_DATA2 = b"\xb8\x00\x00\x00\x00"
PATCH_DATA3 = b"\xc3"

def patch_dll(data: bytes):
    actual_version = VERSION_STRING.split()[0]
    def apply_patch(pattern, patch, min_version=None):
        nonlocal data
        if min_version and parse_version(actual_version) < parse_version(min_version):
            return True
        new_data = pattern.sub(lambda m: patch + m.group(0)[len(patch):], data, 1)
        changed = new_data != data
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

def get_terminal_width():
    try:
        return shutil.get_terminal_size().columns - 1
    except OSError:
        return 80

def handle_standalone():
    with progress_log("Extracting zip file and patching"):
        with zipfile.ZipFile(io.BytesIO(megahack_zip), 'r') as zf:
            for item in zf.infolist():
                fn = item.filename
                if fn.endswith("/"):
                    (GD_PATH / fn.rstrip("/")).mkdir(parents=True, exist_ok=True)
                else:
                    content = zf.read(fn)
                    if fn == "hackpro.dll":
                        content = patch_dll(content)
                    (GD_PATH / fn).write_bytes(content)
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
        OUT_FILENAME = "absolllute.megahack.geode"
        with zipfile.ZipFile(io.BytesIO(megahack_zip), 'r') as zip_in, \
             zipfile.ZipFile(OUT_FILENAME, 'w') as zip_out:
            for item in zip_in.infolist():
                data = zip_in.read(item.filename)
                if item.filename == "absolllute.megahack.dll":
                    data = patch_dll(data)
                    item.filename = OUT_FILENAME.replace(".geode", ".dll")
                elif item.filename == "mod.json":
                    mod = json.loads(data)
                    mod["id"] = OUT_FILENAME.removesuffix(".geode")
                    mod["name"] = "Megahack"
                    mod["description"] = "Cracked version"
                    data = json.dumps(mod, indent="\t").encode()
                zip_out.writestr(item, data)

    GEODE_DIR = GD_PATH / "geode" / "mods"
    copied_geode = False
    if not GEODE_DIR.is_dir():
        warn("Geode mods folder not found! Please install Geode first.")
    else:
        with progress_log("Copying geode to mods folder"):
            shutil.copy(OUT_FILENAME, GEODE_DIR / OUT_FILENAME)
            copied_geode = True

    geode_msg = (
        "* The cracked geode was copied to the mods folder. You should be able to open the game and press tab to see the mod menu!"
        if copied_geode else
        "* Geode was not found during the cracking process. After installing Geode, either rerun this script or copy the newly created .geode file manually."
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

# ---------- Create fake license ----------
with progress_log("Creating fake license file"):
    mh_local_dir = LOCALAPPDATA / "absolllute.megahack"
    mh_local_dir.mkdir(parents=True, exist_ok=True)
    mh_license_path = mh_local_dir / "license"
    mh_license_fallback_path = CWD / "license"

    EXPECTED_CHACHA_KEY = bytes.fromhex(
        "0E 84 1F A5 BF E5 CE 8F C9 1E B1 1A DD 1D CE F6 94 04 5B EE AF CF 52 1B F4 34 1D 39 97 C1 C2 19"
    )

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

    license_dict = {
        "data": base64.b64encode(data_dump.encode()).decode('utf-8'),
        "sig": base64.b64encode(signature).decode('utf-8'),
        "token": token
    }

    license_str = json.dumps(license_dict, separators=(",", ":"))
    mh_license_path.write_text(license_str)
    mh_license_fallback_path.write_text(license_str)

    assert mh_license_path.exists() or mh_license_fallback_path.exists()

# ---------- Run ----------
print(handle_geode() if USE_GEODE else handle_standalone())