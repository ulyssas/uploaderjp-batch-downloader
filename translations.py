import locale

try:
    loc = locale.getlocale()[0] or ""
except Exception:
    loc = ""
CURRENT_LANG = "ja" if loc.lower().startswith("ja") else "en"

MESSAGES = {
    "ja": {
        # CLI
        "WAIT_EXIT": "スクリプトが完了しました。Enterキーを押すとウィンドウを閉じます。",
        "ERR_LOG_WRITE": "ログ書き込みエラー: {0}",
        "WARN_CSV_TEMPLATE": "setting.csvが見つかりませんでした。テンプレートを生成しました。\nURLを記入してから再度実行してください。",
        "INFO_CSV_LOADED": "CSV読み込み完了: {0}",
        "INFO_AGE_CONFIRM": "{0}: 年齢確認ページだったため「確認」ボタンを押しセッション情報を更新しました。",
        "ERR_GET_INDEX": "{0}: 最新indexの取得中にエラーが発生しました: {1}",
        "ERR_NOT_FOUND": "{0}: DLに失敗しました。ページが存在しません: 404",
        "WARN_PASSWD": "{0}: パスワード付きのためDLできませんでした",
        "ERR_TOKEN_MISSING": "{0}: token/MD5が見つかりませんでした",
        "ERR_DL_LINK": "{0}: DLリンクの抽出に失敗しました",
        "INFO_EXISTS_GOOD": "{0}: 既にファイルが存在します。正しいMD5です: {1}",
        "ERR_EXISTS_BAD": "{0}: 既にファイルが存在しますが、ページとファイルでMD5が異なっています ([Page] {1} : [File] {2})",
        "INFO_DL_SUCCESS": "{0}: DLに成功しました。正しいMD5です: {1}",
        "ERR_DL_MD5_MISMATCH": "{0}: DLできましたが、ページとファイルでMD5が異なっています ([Page] {1} : [File] {2})",
        "ERR_HTTP_RESPONSE": "{0}: DLに失敗しました。サイトの応答がエラーです: {1}",
        "ERR_DL_GENERIC": "{0}: 何らかのエラーが発生しました: {1}",
        "ERR_CONFIG": "設定値がおかしいです: {0}",
        "ERR_CSV_DUPS": "アップローダーのURLが重複しています。重複が無いようにsetting.csvを修正してください。処理を中止します",
        "INFO_CHECK_LATEST": "アップローダーの最新状況を確認します",
        "INFO_CHECK_UPDATE": "{0}: 更新を確認します",
        "ERR_NO_FILE": "{0}: ファイルページのURL番号が1つも取得できませんでした。アップローダーにファイルが1つも存在しないか、アップローダーのURLが間違っています",
        "INFO_FOUND_NEW": "{0}: 新しいファイルがあったので {1} から {2} までDLします",
        "INFO_DL_FINISHED": "{0}: DLが終了しました",
        "INFO_NO_UPDATE": "{0}: 更新はありませんでした",
        "ERR_GENERIC": "何らかのエラーが発生したためこのアップローダーの処理を中断します: {0}",
        "INFO_CSV_UPDATE": "setting.csvを更新しました",
        "INFO_FINISHED": "すべての処理が完了しました",
        "WARN_ABORTED": "処理が中断されました",
        # GUI
        "TITLE": "uploader.jp 一括ダウンローダー {0}",
        "LABEL_CSV": "設定ファイル:",
        "BUTTON_OPEN": "参照",
        "BUTTON_RELOAD": "再読込",
        "LABEL_FOLDER": "ダウンロード先:",
        "LABEL_TARGET": "対象アップローダー",
        "TABLE_CURIDX": "現在Index",
        "TABLE_ISDL": "DL有効",
        "LABEL_PROGRESS": "進捗",
        "BUTTON_START": "開始",
        "BUTTON_ABORT": "中止",
        "BUTTON_CLEAR": "クリア",
        "OPEN_SAVEDIR": "保存先を開く",
        "PROG_COMPLETE": "完了",
        "PROG_ABORTING": "中断しています...",
        "PROG_READY": "待機中",
        "POPUP_EXIT_WHILE_RUNNING": "ファイルをダウンロード中です。本当に終了しますか？",
    },
    "en": {
        # CLI
        "WAIT_EXIT": "Finished running the script. Press Return to close the window.",
        "ERR_LOG_WRITE": "Error while writing log: {0}",
        "WARN_CSV_TEMPLATE": "Could not find setting.csv. A template CSV has been generated.\nRe-run the script after entering URLs.",
        "INFO_CSV_LOADED": "Loaded CSV: {0}",
        "INFO_AGE_CONFIRM": "{0}: Pressed confirm button on the age verification page. Session information has been updated.",
        "ERR_GET_INDEX": "{0}: Error while getting latest index: {1}",
        "ERR_NOT_FOUND": "{0}: Download failed. Page not found: 404",
        "WARN_PASSWD": "{0}: Download failed. Password protected.",
        "ERR_TOKEN_MISSING": "{0}: token/MD5 could not be found.",
        "ERR_DL_LINK": "{0}: Failed to extract download link.",
        "INFO_EXISTS_GOOD": "{0}: File already exists. Correct MD5: {1}",
        "ERR_EXISTS_BAD": "{0}: File already exists, but it has a different MD5 from the page ([Page] {1} : [File] {2})",
        "INFO_DL_SUCCESS": "{0}: Download successful. Correct MD5: {1}",
        "ERR_DL_MD5_MISMATCH": "{0}: Download was successful, but it has a different MD5 from the page ([Page] {1} : [File] {2})",
        "ERR_HTTP_RESPONSE": "{0}: Download failed. The website returned an error: {1}",
        "ERR_DL_GENERIC": "{0}: An unknown error has occurred: {1}",
        "ERR_CONFIG": "Incorrect configuration: {0}",
        "ERR_CSV_DUPS": "Duplicate uploader URLs found. Fix setting.csv to remove any duplicates. Aborting the process.",
        "INFO_CHECK_LATEST": "Checking latest status for uploaders",
        "INFO_CHECK_UPDATE": "{0}: Checking updates",
        "ERR_NO_FILE": "{0}: No URL numbers found for the file page. No file exists or wrong URL for the uploader.",
        "INFO_FOUND_NEW": "{0}: Found new files. Downloading from {1} to {2}.",
        "INFO_DL_FINISHED": "{0}: Download completed.",
        "INFO_NO_UPDATE": "{0}: There was no update.",
        "ERR_GENERIC": "Aborting this uploader due to an unknown error: {0}",
        "INFO_CSV_UPDATE": "Updated setting.csv.",
        "INFO_FINISHED": "All processes are complete.",
        "WARN_ABORTED": "Process aborted by user.",
        # GUI
        "TITLE": "uploader.jp Batch Downloader {0}",
        "LABEL_CSV": "Setting file:",
        "BUTTON_OPEN": "Open",
        "BUTTON_RELOAD": "Reload",
        "LABEL_FOLDER": "Download folder:",
        "LABEL_TARGET": "Target uploader",
        "TABLE_CURIDX": "current index",
        "TABLE_ISDL": "DL Active",
        "LABEL_PROGRESS": "Progress",
        "BUTTON_START": "Start",
        "BUTTON_ABORT": "Abort",
        "BUTTON_CLEAR": "Clear",
        "OPEN_SAVEDIR": "Open save location",
        "PROG_COMPLETE": "Completed",
        "PROG_ABORTING": "Aborting...",
        "PROG_READY": "Ready",
        "POPUP_EXIT_WHILE_RUNNING": "Download still in progress. Do you still quit?",
    },
}


def tr(key: str, *args, **kwargs) -> str:
    msg = MESSAGES.get(CURRENT_LANG, {}).get(key)
    if msg is None:
        msg = MESSAGES["en"].get(key, key)

    if args:
        return msg.format(*args)
    if kwargs:
        return msg.format(**kwargs)
    return msg
