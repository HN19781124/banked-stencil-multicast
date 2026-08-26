"""Download a pinned, portable RTL verification toolchain.

The installer is deliberately repository-local code with no third-party Python
dependencies. It selects one official YosysHQ OSS CAD Suite archive, verifies
its pinned size and SHA-256 digest, and extracts it into a per-user cache.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


RELEASE = "2026-08-26"
REPOSITORY = "YosysHQ/oss-cad-suite-build"
DOWNLOAD_BASE = f"https://github.com/{REPOSITORY}/releases/download/{RELEASE}"
USER_AGENT = "neumann-bottleneck-verifier/0.1"


@dataclass(frozen=True)
class Asset:
    platform_key: str
    filename: str
    size: int
    sha256: str

    @property
    def url(self) -> str:
        return f"{DOWNLOAD_BASE}/{self.filename}"


ASSETS = {
    "darwin-arm64": Asset(
        "darwin-arm64",
        "oss-cad-suite-darwin-arm64-20260826.tgz",
        519_882_774,
        "2a143c05f69e63cd22ec6190d7217f27f0804157f927c7007eb173caf7e03982",
    ),
    "darwin-x64": Asset(
        "darwin-x64",
        "oss-cad-suite-darwin-x64-20260826.tgz",
        502_661_117,
        "3db6a91ed6ca5aa265257fda5e39672cf24ad9aa4b05325c04ca4b3582f200ab",
    ),
    "linux-arm64": Asset(
        "linux-arm64",
        "oss-cad-suite-linux-arm64-20260826.tgz",
        678_371_762,
        "3de01954679ca8ab24d15a7f5b238a216f0ae7ae2f98301eb7ba0eebf5f34956",
    ),
    "linux-x64": Asset(
        "linux-x64",
        "oss-cad-suite-linux-x64-20260826.tgz",
        740_788_351,
        "b9c1f7a53a8b144be8ab7f8fd754b98b0d2b1a0b72d39165f7bb2bf104b2b652",
    ),
    "windows-x64": Asset(
        "windows-x64",
        "oss-cad-suite-windows-x64-20260826.tgz",
        595_309_275,
        "fdb296c1dedc1ff7370e378e3e7715dad48d9a4895d5d3525fba113db63642de",
    ),
}


def platform_key(system: str | None = None, machine: str | None = None) -> str:
    """Normalize host information to an OSS CAD Suite asset key."""

    normalized_system = (system or platform.system()).strip().lower()
    normalized_machine = (machine or platform.machine()).strip().lower()
    system_aliases = {"windows": "windows", "linux": "linux", "darwin": "darwin"}
    machine_aliases = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    try:
        key = f"{system_aliases[normalized_system]}-{machine_aliases[normalized_machine]}"
    except KeyError as error:
        raise RuntimeError(
            f"unsupported host: system={normalized_system!r}, machine={normalized_machine!r}"
        ) from error
    if key not in ASSETS:
        raise RuntimeError(f"no pinned OSS CAD Suite asset for {key}")
    return key


def selected_asset(system: str | None = None, machine: str | None = None) -> Asset:
    return ASSETS[platform_key(system, machine)]


def default_cache_root() -> Path:
    """Return a per-user cache path, avoiding spaces on typical Windows hosts."""

    configured = os.environ.get("NEUMANN_CAD_CACHE")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return (base / "neumann-cad").resolve()
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache).expanduser() if xdg_cache else Path.home() / ".cache"
    return (base / "neumann-cad").resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(asset: Asset, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.stat().st_size == asset.size and sha256_file(destination) == asset.sha256:
            print(f"archive cache: PASS ({destination})")
            return destination
        destination.unlink()

    partial = destination.with_name(destination.name + ".part")
    if partial.exists():
        partial.unlink()
    request = urllib.request.Request(asset.url, headers={"User-Agent": USER_AGENT})
    received = 0
    last_update = 0.0
    print(f"downloading {asset.url}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                received += len(chunk)
                now = time.monotonic()
                if now - last_update >= 1.0:
                    percent = 100.0 * received / asset.size
                    print(f"  {received / 1_048_576:.1f} MiB / {asset.size / 1_048_576:.1f} MiB ({percent:.1f}%)")
                    last_update = now
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    if received != asset.size:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"download size mismatch: expected {asset.size}, received {received}")
    actual_digest = sha256_file(partial)
    if actual_digest != asset.sha256:
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"SHA-256 mismatch: expected {asset.sha256}, received {actual_digest}"
        )
    partial.replace(destination)
    print("archive SHA-256: PASS")
    return destination


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (root / member.name).resolve()
        if not _is_inside(target, root):
            raise RuntimeError(f"archive member escapes destination: {member.name}")
        if member.issym() or member.islnk():
            link_target = (target.parent / member.linkname).resolve()
            if not _is_inside(link_target, root):
                raise RuntimeError(f"archive link escapes destination: {member.name}")
        if member.isdev() or member.isfifo():
            raise RuntimeError(f"unsupported special archive member: {member.name}")
    if sys.version_info >= (3, 12):
        archive.extractall(destination, filter="data")
    else:
        archive.extractall(destination)


def _remove_direct_child(path: Path, parent: Path) -> None:
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    if resolved_path.parent != resolved_parent:
        raise RuntimeError(f"refusing to remove path outside install parent: {resolved_path}")
    if resolved_path.exists():
        shutil.rmtree(resolved_path)


def suite_path(cache_root: Path | None = None) -> Path:
    root = (cache_root or default_cache_root()).resolve()
    return root / "installs" / RELEASE / "oss-cad-suite"


def find_suite(cache_root: Path | None = None) -> Path | None:
    configured = os.environ.get("OSS_CAD_SUITE")
    candidates = []
    if configured:
        configured_path = Path(configured).expanduser().resolve()
        candidates.extend((configured_path, configured_path / "oss-cad-suite"))
    candidates.append(suite_path(cache_root))
    for candidate in candidates:
        if (candidate / "bin").is_dir():
            return candidate
    return None


def tool_path(name: str, suite: Path | None = None) -> Path | None:
    executable = name + (".exe" if os.name == "nt" else "")
    if suite:
        candidate = suite / "bin" / executable
        if candidate.is_file():
            return candidate
    discovered = shutil.which(name)
    return Path(discovered).resolve() if discovered else None


def suite_environment(suite: Path | None) -> dict[str, str]:
    environment = os.environ.copy()
    if suite:
        suite_root = str(suite) + os.sep
        binary_path = suite / "bin"
        library_path = suite / "lib"
        environment["YOSYSHQ_ROOT"] = suite_root
        environment["PATH"] = os.pathsep.join(
            (str(binary_path), str(library_path), environment.get("PATH", ""))
        )
        environment["SSL_CERT_FILE"] = str(suite / "etc" / "cacert.pem")
        environment["PYTHON_EXECUTABLE"] = str(
            library_path / ("python3.exe" if os.name == "nt" else "python3")
        )
        environment["QT_PLUGIN_PATH"] = str(library_path / "qt6" / "plugins")
        environment["QT_LOGGING_RULES"] = "*=false"
        environment["GTK_EXE_PREFIX"] = suite_root
        environment["GTK_DATA_PREFIX"] = suite_root
        environment["GDK_PIXBUF_MODULEDIR"] = str(
            library_path / "gdk-pixbuf-2.0" / "2.10.0" / "loaders"
        )
        environment["GDK_PIXBUF_MODULE_FILE"] = str(
            library_path / "gdk-pixbuf-2.0" / "2.10.0" / "loaders.cache"
        )
        environment["OPENFPGALOADER_SOJ_DIR"] = str(suite / "share" / "openFPGALoader")
    return environment


def doctor(suite: Path | None) -> bool:
    checks = (("iverilog", "-V"), ("vvp", "-V"), ("yosys", "-V"))
    okay = True
    environment = suite_environment(suite)
    for name, version_flag in checks:
        executable = tool_path(name, suite)
        if not executable:
            print(f"{name}: NOT FOUND")
            okay = False
            continue
        result = subprocess.run(
            [str(executable), version_flag],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )
        first_line = (result.stdout or result.stderr).splitlines()
        summary = first_line[0] if first_line else f"exit={result.returncode}"
        print(f"{name}: {summary}")
        okay = okay and result.returncode == 0
    return okay


def install(cache_root: Path | None = None, keep_archive: bool = False) -> Path:
    root = (cache_root or default_cache_root()).resolve()
    asset = selected_asset()
    final_parent = root / "installs"
    final_version = final_parent / RELEASE
    final_suite = final_version / "oss-cad-suite"
    marker = final_version / ".installed.json"
    if final_suite.is_dir() and marker.is_file():
        print(f"toolchain cache: PASS ({final_suite})")
        if not doctor(final_suite):
            raise RuntimeError("cached toolchain failed its doctor checks")
        return final_suite

    archive_path = root / "downloads" / asset.filename
    _download(asset, archive_path)
    final_parent.mkdir(parents=True, exist_ok=True)
    # Keep the logical Windows path here. Resolving it inside a packaged app can
    # expose the AppContainer virtualization target and make the final rename
    # look like a cross-directory operation even though both paths share a root.
    temporary = Path(tempfile.mkdtemp(prefix=f"{RELEASE}-", dir=final_parent))
    try:
        print(f"extracting to {temporary}")
        with tarfile.open(archive_path, "r:gz") as archive:
            _safe_extract(archive, temporary)
        extracted_suite = temporary / "oss-cad-suite"
        if not (extracted_suite / "bin").is_dir():
            raise RuntimeError("archive did not contain oss-cad-suite/bin")
        (temporary / ".installed.json").write_text(
            json.dumps(
                {"release": RELEASE, "asset": asdict(asset), "source": asset.url},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if final_version.exists():
            _remove_direct_child(final_version, final_parent)
        temporary.replace(final_version)
    except BaseException:
        if temporary.exists():
            _remove_direct_child(temporary, final_parent)
        raise

    if not keep_archive:
        archive_path.unlink(missing_ok=True)
    if not doctor(final_suite):
        raise RuntimeError("installed toolchain failed its doctor checks")
    return final_suite


def print_plan(cache_root: Path | None = None) -> None:
    asset = selected_asset()
    plan = {
        "release": RELEASE,
        "asset": asdict(asset),
        "url": asset.url,
        "archive_mib": round(asset.size / 1_048_576, 1),
        "install_path": str(suite_path(cache_root)),
    }
    print(json.dumps(plan, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "install", "doctor"), nargs="?", default="plan")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--keep-archive", action="store_true")
    arguments = parser.parse_args()
    cache_root = arguments.cache_dir.expanduser().resolve() if arguments.cache_dir else None
    if arguments.action == "plan":
        print_plan(cache_root)
        return 0
    if arguments.action == "install":
        install(cache_root, keep_archive=arguments.keep_archive)
        return 0
    suite = find_suite(cache_root)
    return 0 if doctor(suite) else 1


if __name__ == "__main__":
    raise SystemExit(main())
