# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

import os


def _wait_for_debugger_to_attach(mode: str) -> bool:
    import tkinter as tk
    from tkinter import ttk
    import sys

    root = tk.Tk()
    root.title("CST STUDIO SUITE")
    mode_stringvar = tk.StringVar()
    mode_stringvar.set(mode)
    b = ttk.Button(root, text="Continue without debugging", command=root.destroy)
    b.pack(side=tk.BOTTOM, padx=10, pady=10, anchor="e")
    ttk.Label(root, image="::tk::icons::information").pack(side=tk.LEFT, anchor="n", expand=False, pady=5, padx=5)
    lbl = ttk.Label(root, text=f"Waiting for Python Debugger to attach. (PID: {os.getpid()})")
    lbl.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2, anchor="w")
    c = ttk.Checkbutton(
        root, text="Break when debugger is attached", variable=mode_stringvar, onvalue="wait_and_break", offvalue="wait"
    )
    c.pack(padx=10, pady=2, anchor="w")

    root.minsize(350, 100)
    _root_killed = False
    _try_to_break = False

    def kill_window_if_debugger_attached():
        nonlocal _root_killed
        nonlocal _try_to_break
        if _root_killed:
            return
        if "pydevd" not in sys.modules:
            root.after(300, kill_window_if_debugger_attached)
        else:
            # noinspection PyUnresolvedReferences
            import pydevd

            if not pydevd.get_global_debugger() or not pydevd.get_global_debugger().ready_to_run:
                root.after(300, kill_window_if_debugger_attached)
            else:
                if not _root_killed:
                    root.destroy()
                    _root_killed = True
                    _try_to_break = True

    root.after(300, kill_window_if_debugger_attached)

    root.mainloop()
    _root_killed = True
    if _try_to_break and mode_stringvar.get() == "wait_and_break":
        return True
    else:
        return False


def wait_for_debugger_if_requested() -> bool:
    _debug_mode = os.getenv("CST_WAIT_FOR_PYTHON_DEBUG", "")
    if _debug_mode == "wait" or _debug_mode == "wait_and_break":
        return _wait_for_debugger_to_attach(_debug_mode)
    else:
        return False
