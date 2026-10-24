#!/usr/bin/env python3

"""
uploader.jp Batch Downloader CLI

based on uploader.jp_downloader_v3 (https://note.com/3935/n/n9011ee06eb78)
"""

import csv
import hashlib
import html
import re
import sys
import threading
import time
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

from translations import tr


def find_app_bundle() -> Path | None:
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return None

    executable = Path(sys.executable).resolve()
    return next(
        (parent for parent in executable.parents if parent.suffix == ".app"),
        None,
    )


# CONFIG
app_bundle = find_app_bundle()
if app_bundle:
    SCRIPT_DIR = app_bundle.parent
elif getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_CSV_PATH = SCRIPT_DIR / "setting.csv"
DEFAULT_SAVE_DIR = SCRIPT_DIR / "downloads"
DEFAULT_LOG_DIR = SCRIPT_DIR / "log"
DEFAULT_SLEEP_SEC = 2.0
CSV_HEADER = ["url", "currentIndex", "isDownload"]
UNWRITABLE_LOG_DIRS: set[Path] = set()


class LogLevel(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3


def write_log(
    message: str,
    level: LogLevel = LogLevel.INFO,
    log_path: Path | None = None,
    log_callback: Callable[[str, LogLevel], None] | None = None,
):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} [{level.name}] {message}"

    if log_callback:
        log_callback(log_message, level)
    match level:
        case LogLevel.WARNING:
            print(f"\033[33m{log_message}\033[0m")
        case LogLevel.ERROR:
            print(f"\033[31m{log_message}\033[0m")
        case _:
            print(log_message)

    if log_path and log_path.parent not in UNWRITABLE_LOG_DIRS:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except OSError as e:
            UNWRITABLE_LOG_DIRS.add(log_path.parent)
            if log_callback:
                log_callback(tr("ERR_LOG_WRITE", e), LogLevel.ERROR)
            print(tr("ERR_LOG_WRITE", e))


def check_or_create_csv(
    csv_path: Path, log_callback: Callable[[str, LogLevel], None] | None = None
) -> bool:
    if not csv_path.exists():
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerow(["https://u1.getuploader.com/sample/", "0", "1"])

        write_log(tr("WARN_CSV_TEMPLATE"), LogLevel.WARNING, log_callback=log_callback)
        return False
    return True


def load_csv(
    csv_path: Path, log_callback: Callable[[str, LogLevel], None] | None = None
) -> list[dict] | None:
    # Initialization
    try:
        if not check_or_create_csv(csv_path, log_callback):
            return None
    except Exception as e:
        write_log(tr("ERR_CONFIG", e), LogLevel.ERROR, log_callback=log_callback)
        return None

    # Verify and read uploader registries
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        settings = list(reader)

        if not reader.fieldnames:
            write_log(
                tr("ERR_CONFIG", "CSV header missing"),
                LogLevel.ERROR,
                log_callback=log_callback,
            )
            return None
        elif reader.fieldnames != CSV_HEADER:
            write_log(
                tr("ERR_CONFIG", "Incorrect CSV header"),
                LogLevel.ERROR,
                log_callback=log_callback,
            )
            return None

    urls = [row["url"] for row in settings]
    if len(urls) != len(set(urls)):
        write_log(tr("ERR_CSV_DUPS"), LogLevel.ERROR, log_callback=log_callback)
        return None

    write_log(tr("INFO_CSV_LOADED", csv_path), log_callback=log_callback)
    return settings


def make_dirs(
    save_dir: Path,
    log_dir: Path,
    log_callback: Callable[[str, LogLevel], None] | None = None,
) -> bool:
    try:
        save_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        write_log(tr("ERR_CONFIG", e), LogLevel.ERROR, log_callback=log_callback)
        return False
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        write_log(
            tr("ERR_CONFIG", f"Failed to create log folder, {e}"),
            LogLevel.WARNING,
            log_callback=log_callback,
        )
    return True


class UploaderClient:
    def __init__(
        self,
        save_dir: Path = DEFAULT_SAVE_DIR,
        log_dir: Path = DEFAULT_LOG_DIR,
        sleep_sec: float = DEFAULT_SLEEP_SEC,
        log_callback: Callable[[str, LogLevel], None] | None = None,
        stop_event: threading.Event | None = None,
    ):
        self.save_dir = save_dir
        self.log_dir = log_dir
        self.sleep_sec = sleep_sec
        self.log_callback = log_callback
        self.stop_event = stop_event

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    "AppleWebKit/537.36 (KHTML, like Gecko)"
                    "Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
                ),
            }
        )

    def _log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        log_path: Path | None = None,
    ):
        write_log(message, level, log_path, self.log_callback)

    def get_log_path(self, uploader_id: str) -> Path:
        return self.log_dir / f"{uploader_id}.log"

    @staticmethod
    def calculate_md5(file_path: Path) -> str:
        with file_path.open("rb") as f:
            return hashlib.file_digest(f, "md5").hexdigest()

    @staticmethod
    def get_input_val(tag) -> str:
        val = tag.get("value")
        return val if isinstance(val, str) else ""

    def request(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        stream: bool = False,
        timeout: tuple[float, float] | float = (10.0, 120.0),
    ):
        time.sleep(self.sleep_sec)
        response = self.session.request(
            method=method, url=url, data=data, stream=stream, timeout=timeout
        )
        return response

    def get_latest_index(self, uploader_url: str) -> int:
        uploader_id = uploader_url.rstrip("/").split("/")[-1]
        log_path = self.get_log_path(uploader_id)
        try:
            res = self.request("GET", uploader_url)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            age_btn = soup.find("input", {"value": "age_confirmation"})
            if age_btn:
                res = self.request("POST", uploader_url, data={"q": "age_confirmation"})
                res.raise_for_status()
                write_log(tr("INFO_AGE_CONFIRM", uploader_url), log_path=log_path)

            pattern = re.compile(
                rf'<tr>\s*<td>\s*<a href="https://.+?\.getuploader\.com/{re.escape(uploader_id)}/download/(\d+)"'
            )
            match = pattern.search(res.text)
            return int(match.group(1)) if match else 0

        except Exception as e:
            write_log(tr("ERR_GET_INDEX", uploader_url, e), LogLevel.ERROR, log_path)
            return 0

    def download_file(self, index: int, uploader_url: str) -> bool:
        """True: successful / skipped, False: ERROR (cannot proceed)"""
        if self.stop_event and self.stop_event.is_set():
            return False

        uploader_id = uploader_url.rstrip("/").split("/")[-1]
        log_path = self.get_log_path(uploader_id)
        download_dir = self.save_dir / uploader_id

        base_url = uploader_url if uploader_url.endswith("/") else uploader_url + "/"
        uri = f"{base_url}download/{index}"

        try:
            res = self.request("GET", uri)
            if res.status_code == 404:
                self._log(tr("ERR_NOT_FOUND", index), LogLevel.ERROR, log_path)
                return True
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")

            if soup.find("input", {"name": "password"}):
                self._log(tr("WARN_PASSWD", index), LogLevel.WARNING, log_path)
                return True

            all_inputs = soup.find_all("input")
            if len(all_inputs) < 3:
                self._log(tr("ERR_TOKEN_MISSING", index), LogLevel.ERROR, log_path)
                return False

            page_md5 = self.get_input_val(all_inputs[1])
            token = self.get_input_val(all_inputs[2])

            post_res = self.request("POST", uri, data={"token": token})
            post_res.raise_for_status()
            post_soup = BeautifulSoup(post_res.text, "html.parser")

            dl_url = None
            for a_tag in post_soup.find_all("a", href=True):
                raw_href = a_tag["href"]
                if not isinstance(raw_href, str):
                    continue

                decoded_href = unquote(html.unescape(raw_href))
                if "downloadx" in decoded_href:
                    dl_url = decoded_href
                    break

            if not dl_url:
                self._log(tr("ERR_DL_LINK", index), LogLevel.ERROR, log_path)
                return False

            file_name = dl_url.rstrip("/").split("/")[-1]
            download_dir.mkdir(parents=True, exist_ok=True)
            download_path = download_dir / f"{index}_{file_name}"

            if download_path.exists():
                file_md5 = self.calculate_md5(download_path)
                if page_md5 and page_md5.lower() == file_md5.lower():
                    self._log(
                        tr("INFO_EXISTS_GOOD", index, page_md5), log_path=log_path
                    )
                    return True
                else:
                    self._log(
                        tr("ERR_EXISTS_BAD", index, page_md5, file_md5),
                        LogLevel.ERROR,
                        log_path,
                    )
                    return True

            with self.request("GET", dl_url, stream=True) as dl_res:
                dl_res.raise_for_status()
                with download_path.open("wb") as f:
                    for chunk in dl_res.iter_content(chunk_size=8192):
                        if self.stop_event and self.stop_event.is_set():
                            return False
                        if chunk:
                            f.write(chunk)

            file_md5 = self.calculate_md5(download_path)
            if page_md5 and page_md5.lower() == file_md5.lower():
                self._log(tr("INFO_DL_SUCCESS", index, file_md5), log_path=log_path)
                return True
            else:
                self._log(
                    tr("ERR_DL_MD5_MISMATCH", index, page_md5, file_md5),
                    LogLevel.ERROR,
                    log_path,
                )
                return True

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "Unknown"
            self._log(tr("ERR_HTTP_RESPONSE", index, status), LogLevel.ERROR, log_path)
            return False
        except Exception as e:
            self._log(tr("ERR_DL_GENERIC", index, e), LogLevel.ERROR, log_path)
            return False


def run_batch(
    csv_path: Path = DEFAULT_CSV_PATH,
    save_dir: Path = DEFAULT_SAVE_DIR,
    log_dir: Path = DEFAULT_LOG_DIR,
    sleep_sec: float = DEFAULT_SLEEP_SEC,
    log_callback: Callable[[str, LogLevel], None] | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    stop_event: threading.Event | None = None,
) -> bool:

    def _log(
        message: str,
        level: LogLevel = LogLevel.INFO,
        log_path: Path | None = None,
    ):
        write_log(message, level, log_path, log_callback)

    # Initialization
    settings = load_csv(csv_path, log_callback)
    if settings is None:
        return False

    if not make_dirs(save_dir, log_dir, log_callback):
        return False

    # Batch download
    client = UploaderClient(
        save_dir=save_dir,
        log_dir=log_dir,
        sleep_sec=sleep_sec,
        log_callback=log_callback,
        stop_event=stop_event,
    )
    _log(tr("INFO_CHECK_LATEST"))

    # Total Downloads (for progress bar)
    tasks = []
    for row in settings:
        if stop_event and stop_event.is_set():
            return False

        if row.get("isDownload") != "1":
            continue

        uploader_url = row["url"]
        uploader_id = uploader_url.rstrip("/").split("/")[-1]
        log_path = client.get_log_path(uploader_id)

        _log(tr("INFO_CHECK_UPDATE", uploader_url), log_path=log_path)
        start_index = int(row.get("currentIndex", 0)) + 1
        latest_index = client.get_latest_index(uploader_url)

        if latest_index == 0:
            _log(tr("ERR_NO_FILE", uploader_url), LogLevel.ERROR, log_path)
        elif latest_index >= start_index:
            tasks.append((row, uploader_url, start_index, latest_index))
            _log(
                tr("INFO_FOUND_NEW", uploader_url, start_index, latest_index),
                log_path=log_path,
            )
        else:
            _log(tr("INFO_NO_UPDATE", uploader_url), log_path=log_path)

    total_files = sum(end - start + 1 for _, _, start, end in tasks)
    completed_files = 0

    if progress_callback:
        progress_callback(0, max(total_files, 1), tr("PROG_READY"))

    log_path = Path()
    updated = False
    is_aborted = False

    try:
        for row, uploader_url, start_index, latest_index in tasks:
            uploader_id = uploader_url.rstrip("/").split("/")[-1]
            log_path = client.get_log_path(uploader_id)

            for i in range(start_index, latest_index + 1):
                if stop_event and stop_event.is_set():
                    is_aborted = True
                    break

                if progress_callback:
                    progress_callback(
                        completed_files, total_files, f"{uploader_id} #{i}"
                    )

                max_retries = 3
                success = False
                for attempt in range(1, max_retries + 1):
                    if stop_event and stop_event.is_set():
                        break
                    if client.download_file(i, uploader_url):
                        success = True
                        break
                    if attempt < max_retries:
                        time.sleep(3 * attempt)

                if success:
                    completed_files += 1
                    row["currentIndex"] = str(i)
                    updated = True
                else:
                    break

            if is_aborted:
                break

            _log(tr("INFO_DL_FINISHED", uploader_url), log_path=log_path)

    except Exception as e:
        _log(tr("ERR_GENERIC", e), LogLevel.ERROR, log_path)

    finally:
        # Update uploader registries
        if updated:
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
                writer.writeheader()
                writer.writerows(settings)
            _log(tr("INFO_CSV_UPDATE"))

    if is_aborted:
        _log(tr("WARN_ABORTED"), LogLevel.WARNING)
        return False

    _log(tr("INFO_FINISHED"))
    if progress_callback:
        progress_callback(0, max(total_files, 1), tr("PROG_COMPLETE"))
    return True


def wait_for_exit():
    print(tr("WAIT_EXIT"))
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    run_batch()
    wait_for_exit()


if __name__ == "__main__":
    main()
