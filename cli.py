#!/usr/bin/env python3

"""
uploader.jp Batch Downloader

based on uploader.jp_downloader_v3 (https://note.com/3935/n/n9011ee06eb78)
"""

import csv
import hashlib
import html
import re
import time
from enum import Enum
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

# CONFIG
script_dir = Path(__file__).resolve().parent
SAVE_DIR = script_dir / "downloads"
CSV_PATH = script_dir / "setting.csv"
LOG_DIR = script_dir / "log"
SLEEP_SEC = 0.5


class LogLevel(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3


def wait_for_exit():
    print("スクリプトが完了しました。Enterキーを押すとウィンドウを閉じます。")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass


def get_log_path(uploader_id: str) -> Path:
    return LOG_DIR / f"{uploader_id}.log"


def write_log(
    message: str,
    level: LogLevel = LogLevel.INFO,
    log_path: Path | None = None,
):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} [{level.name}] {message}"

    match level:
        case LogLevel.WARNING:
            print(f"\033[33m{log_message}\033[0m")
        case LogLevel.ERROR:
            print(f"\033[31m{log_message}\033[0m")
        case _:
            print(log_message)

    if log_path:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"ログ書き込みエラー: {e}")


def check_or_create_csv(csv_path: Path) -> bool:
    if not csv_path.exists():
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["url", "currentIndex", "isDownload"])
            writer.writerow(["https://u1.getuploader.com/sample/", "0", "1"])

        write_log(
            "setting.csvが見つかりませんでした。テンプレートを生成しました。\n"
            "URLを記入してから再度実行してください。",
            LogLevel.WARNING,
        )
        return False
    return True


class UploaderClient:
    def __init__(self):
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
    ):
        time.sleep(SLEEP_SEC)
        response = self.session.request(
            method=method, url=url, data=data, stream=stream, timeout=30
        )
        return response

    def get_latest_index(self, uploader_url: str) -> int:
        uploader_id = uploader_url.rstrip("/").split("/")[-1]
        log_path = get_log_path(uploader_id)
        try:
            res = self.request("GET", uploader_url)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            age_btn = soup.find("input", {"value": "age_confirmation"})
            if age_btn:
                res = self.request("POST", uploader_url, data={"q": "age_confirmation"})
                res.raise_for_status()
                write_log(
                    f"{uploader_url}: 年齢確認ページだったため「確認」ボタンを押しセッション情報を更新しました。",
                    log_path=log_path,
                )

            pattern = re.compile(
                rf'<tr>\s*<td>\s*<a href="https://.+?\.getuploader\.com/{re.escape(uploader_id)}/download/(\d+)"'
            )
            match = pattern.search(res.text)
            return int(match.group(1)) if match else 0

        except Exception as e:
            write_log(
                f"{uploader_url}: 最新indexの取得中にエラーが発生しました: {e}",
                LogLevel.ERROR,
                log_path,
            )
            return 0

    def download_file(self, index: int, uploader_url: str):
        uploader_id = uploader_url.rstrip("/").split("/")[-1]
        log_path = get_log_path(uploader_id)
        download_dir = SAVE_DIR / uploader_id

        base_url = uploader_url if uploader_url.endswith("/") else uploader_url + "/"
        uri = f"{base_url}download/{index}"

        try:
            res = self.request("GET", uri)
            if res.status_code == 404:
                write_log(
                    f"{index}: DLに失敗しました。ページが存在しません: 404",
                    LogLevel.ERROR,
                    log_path,
                )
                return
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")

            if soup.find("input", {"name": "password"}):
                write_log(
                    f"{index}: パスワード付きのためDLできませんでした",
                    LogLevel.WARNING,
                    log_path,
                )
                return

            all_inputs = soup.find_all("input")
            if len(all_inputs) < 3:
                write_log(
                    f"{index}: token/MD5が見つかりませんでした",
                    LogLevel.ERROR,
                    log_path,
                )
                return

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
                write_log(
                    f"{index}: DLリンクの抽出に失敗しました",
                    LogLevel.ERROR,
                    log_path,
                )
                return

            file_name = dl_url.rstrip("/").split("/")[-1]
            download_dir.mkdir(parents=True, exist_ok=True)
            download_path = download_dir / f"{index}_{file_name}"

            if download_path.exists():
                file_md5 = self.calculate_md5(download_path)
                if page_md5 and page_md5.lower() == file_md5.lower():
                    write_log(
                        f"{index}: 既にファイルが存在します。正しいMD5です: {page_md5}",
                        log_path=log_path,
                    )
                    return
                else:
                    write_log(
                        f"{index}: 既にファイルが存在しますが、ページとファイルでMD5が異なっています ([Page] {page_md5} : [File] {file_md5})",
                        LogLevel.ERROR,
                        log_path,
                    )
                    return

            with self.request("GET", dl_url, stream=True) as dl_res:
                dl_res.raise_for_status()
                with download_path.open("wb") as f:
                    for chunk in dl_res.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            file_md5 = self.calculate_md5(download_path)
            if page_md5 and page_md5.lower() == file_md5.lower():
                write_log(
                    f"{index}: DLに成功しました。正しいMD5です: {file_md5}",
                    log_path=log_path,
                )
            else:
                write_log(
                    f"{index}: DLできましたが、ページとファイルでMD5が異なっています ([Page] {page_md5} : [File] {file_md5})",
                    LogLevel.ERROR,
                    log_path,
                )

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "Unknown"
            write_log(
                f"{index}: DLに失敗しました。サイトの応答がエラーです: {status}",
                LogLevel.ERROR,
                log_path,
            )
        except Exception as e:
            write_log(
                f"{index}: 何らかのエラーが発生しました: {e}",
                LogLevel.ERROR,
                log_path,
            )


def main():
    # Initialization
    try:
        check_csv = check_or_create_csv(CSV_PATH)
        if not check_csv:
            wait_for_exit()
            return

        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        write_log(f"設定値がおかしいです: {e}", LogLevel.ERROR)
        wait_for_exit()
        return

    # Verify and read uploader registries
    with CSV_PATH.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        settings = list(reader)
        fieldnames = reader.fieldnames

    urls = [row["url"] for row in settings]
    if len(urls) != len(set(urls)):
        write_log(
            "アップローダーのURLが重複しています。重複が無いようにsetting.csvを修正してください。処理を中止します",
            LogLevel.ERROR,
        )
        wait_for_exit()
        return

    # Batch download
    client = UploaderClient()
    updated = False
    write_log("アップローダーの最新状況を確認します")
    for row in settings:
        if row.get("isDownload") != "1":
            continue

        uploader_url = row["url"]
        uploader_id = uploader_url.rstrip("/").split("/")[-1]
        log_path = get_log_path(uploader_id)

        try:
            write_log(f"{uploader_url}: 更新を確認します", log_path=log_path)
            start_index = int(row.get("currentIndex", 0)) + 1
            latest_index = client.get_latest_index(uploader_url)

            if latest_index == 0:
                write_log(
                    f"{uploader_url}: ファイルページのURL番号が1つも取得できませんでした。アップローダーにファイルが1つも存在しないか、アップローダーのURLが間違っています",
                    LogLevel.ERROR,
                    log_path,
                )
            elif latest_index >= start_index:
                write_log(
                    f"{uploader_url}: 新しいファイルがあったので {start_index} から {latest_index} までDLします",
                    log_path=log_path,
                )
                for i in range(start_index, latest_index + 1):
                    client.download_file(i, uploader_url)

                row["currentIndex"] = str(latest_index)
                updated = True
                write_log(f"{uploader_url}: DLが終了しました", log_path=log_path)
            else:
                write_log(f"{uploader_url}: 更新はありませんでした", log_path=log_path)
        except Exception as e:
            write_log(
                f"何らかのエラーが発生したためこのアップローダーの処理を中断します: {e}",
                LogLevel.ERROR,
                log_path,
            )

    # Update uploader registries
    if updated:
        with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(settings)
        write_log("setting.csvを更新しました")

    write_log("すべての処理が完了しました")
    wait_for_exit()


if __name__ == "__main__":
    main()
