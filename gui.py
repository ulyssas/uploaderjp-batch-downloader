#!/usr/bin/env python3
import os
import platform
import subprocess
import threading
from functools import partial
from pathlib import Path

import TkEasyGUI as eg

from cli import (
    DEFAULT_CSV_PATH,
    DEFAULT_LOG_DIR,
    DEFAULT_SAVE_DIR,
    LogLevel,
    load_csv,
    make_dirs,
    run_batch,
)
from translations import tr

APP_VERSION = "v1.0.0"
worker_thread: threading.Thread | None = None
stop_event = threading.Event()


def print_gui(win: eg.Window, log_message: str, level: LogLevel):
    win["-LOG"].update(readonly=False)
    match level:
        case LogLevel.WARNING:
            win["-LOG"].print(log_message, text_color="orange")
        case LogLevel.ERROR:
            win["-LOG"].print(log_message, text_color="red")
        case _:
            win["-LOG"].print(log_message)
    win["-LOG"].update(readonly=True)


def progress_gui(win: eg.Window, completed: int, total: int, status: str):
    percent = int((completed / total) * 100) if total > 0 else 0
    percent = max(min(percent, 100), 0)
    display_text = f"{status} ({completed + 1}/{total})" if total > 0 else status

    win["-PROGRESS"].update(value=percent)
    win["-STATUS"].update(text=display_text)


def open_output(win: eg.Window, path: Path):
    gui_logger = partial(print_gui, win)
    make_dirs(DEFAULT_SAVE_DIR, DEFAULT_LOG_DIR, gui_logger)

    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def refresh_table(win: eg.Window, csv_path_str: str):
    gui_logger = partial(print_gui, win)

    path = Path(csv_path_str)
    settings = load_csv(path, gui_logger)
    if settings is not None:
        l = [list(d.values()) for d in settings]
        win["-CSV_TABLE"].update(values=l)


def setup(win: eg.Window, csv_path: Path):
    tree: eg.Table = win["-CSV_TABLE"].widget
    tree.column("#1", anchor="w")
    tree.column("#2", anchor="e")
    tree.column("#3", anchor="center")

    win["-LOG"].update(
        text="uploader.jp Batch Downloader\nbased on uploader.jp_downloader_v3 (https://note.com/3935/n/n9011ee06eb78)\n\n"
    )
    refresh_table(win, str(csv_path))
    window["-STATUS"].update(text=tr("PROG_READY"))


# fmt: off
layout = [
    # CSV Load
    [
        eg.Text(tr("LABEL_CSV")),
        eg.Input(str(DEFAULT_CSV_PATH), key="-CSV_PATH", expand_x=True),
        eg.FileBrowse(tr("BUTTON_OPEN"), key="-CSV_OPEN", file_types=(("CSV Files", "*.csv"),), enable_events=True),
        eg.Button(tr("BUTTON_RELOAD"), key="-CSV_RELOAD"),
    ],
    # Output Folder
    [
        eg.Text(tr("LABEL_FOLDER")),
        eg.Input(str(DEFAULT_SAVE_DIR), key="-SAVE_DIR", expand_x=True),
        eg.FolderBrowse(tr("BUTTON_OPEN"), key="-SAVE_OPEN"),
    ],
    # Loaded uploaders
    [
        eg.Frame(
            tr("LABEL_TARGET"),
            [
                [eg.Table(
                    values=[],
                    headings=["URL", tr("TABLE_CURIDX"), tr("TABLE_ISDL")],
                    col_widths=[30, 10, 5],
                    key="-CSV_TABLE",
                    size=(None, 8),
                    expand_x=True,
                )]
            ],
            expand_x=True,
        )
    ],
    # Progress (bar & status)
    [
        eg.Frame(
            tr("LABEL_PROGRESS"),
            [
                [eg.Progressbar(
                    value_range=(0, 100),
                    default_value=0,
                    key="-PROGRESS",
                    expand_x=True,
                )],
                [eg.Text(tr("PROG_READY"), key="-STATUS")]
            ],
            expand_x=True,
        )
    ],
    # Log
    [
        eg.Multiline(
            "Sample",
            key="-LOG",
            readonly=True,
            size=(100, 8),
            expand_x=True,
            expand_y=True,
            autoscroll=True,
            wrap="none",
        )
    ],
    # Buttons
    [
        eg.Button(tr("BUTTON_START"), key="-START"),
        eg.Button(tr("BUTTON_ABORT"), key="-ABORT", disabled=True),
        eg.Push(),
        eg.Button(tr("BUTTON_CLEAR"), key="-LOG_CLEAR"),
        eg.Button(tr("OPEN_SAVEDIR"), key="-OPEN_DIR"),
    ],
]
# fmt: on

window = eg.Window(
    tr("TITLE", APP_VERSION),
    layout,
    size=(700, 500),
    resizable=True,
)
window.window.minsize(500, 500)
window.read(timeout=0)
window.window.update_idletasks()

setup(window, DEFAULT_CSV_PATH)

while True:
    event, values = window.read(timeout=100)
    if event == eg.WIN_CLOSED:
        if worker_thread and worker_thread.is_alive():
            if eg.popup_yes_no(tr("POPUP_EXIT_WHILE_RUNNING")):
                stop_event.set()
                worker_thread.join(timeout=2.0)
                break
            else:
                continue
        else:
            break

    if worker_thread and not worker_thread.is_alive():
        worker_thread = None
        window["-START"].update(disabled=False)
        window["-ABORT"].update(disabled=True)
        window["-STATUS"].update(text=tr("PROG_READY"))

        refresh_table(window, window["-CSV_PATH"].get())
        window["-CSV_PATH"].update(readonly=False)
        window["-CSV_OPEN"].update(disabled=False)
        window["-CSV_RELOAD"].update(disabled=False)
        window["-SAVE_DIR"].update(readonly=False)
        window["-SAVE_OPEN"].update(disabled=False)

    elif event == "-CSV_RELOAD" or event == "-CSV_OPEN":
        refresh_table(window, values["-CSV_PATH"])
    elif event == "-OPEN_DIR":
        open_output(window, values["-SAVE_DIR"])
    elif event == "-LOG_CLEAR":
        window["-LOG"].update(text="")
    elif event == "-START":
        if worker_thread and worker_thread.is_alive():
            continue

        stop_event.clear()
        window["-START"].update(disabled=True)
        window["-ABORT"].update(disabled=False)

        window["-CSV_PATH"].update(readonly=True)
        window["-CSV_OPEN"].update(disabled=True)
        window["-CSV_RELOAD"].update(disabled=True)
        window["-SAVE_DIR"].update(readonly=True)
        window["-SAVE_OPEN"].update(disabled=True)

        gui_logger = partial(print_gui, window)
        gui_progress = partial(progress_gui, window)

        worker_thread = threading.Thread(
            target=run_batch,
            kwargs={
                "csv_path": Path(values["-CSV_PATH"]),
                "save_dir": Path(values["-SAVE_DIR"]),
                "log_callback": gui_logger,
                "progress_callback": gui_progress,
                "stop_event": stop_event,
            },
            daemon=True,
        )
        worker_thread.start()
    elif event == "-ABORT":
        stop_event.set()
        window["-ABORT"].update(disabled=True)
        window["-STATUS"].update(text=tr("PROG_ABORTING"))

window.close()
