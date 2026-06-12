# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

import tkinter as tk
from tkinter import ttk
from tkinter.simpledialog import Dialog as _TkInterBaseDialog
import os
import socket

class _AbstractCSTDialog(_TkInterBaseDialog):
    def __init__(self, parent, title=None):
        tk.Toplevel.__init__(self, parent)
        self.client(socket.gethostname())
        self.withdraw() # remain invisible for now
        # If the master is not viewable, don't
        # make the child transient, or else it
        # would be opened withdrawn
        if parent.winfo_viewable():
            self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        body = ttk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5, fill=tk.BOTH)

        self.buttonbox()

        self.update_idletasks()
        self.minsize(self.winfo_width(), self.winfo_height())

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        if self.parent is not None:
            self.geometry("+%d+%d" % (self.parent.winfo_rootx()+50,
                                      self.parent.winfo_rooty()+50))

        self.deiconify()  # become visible now

        self.initial_focus.focus_set()

        # wait for window to appear on screen before calling grab_set
        # skip this if we are GUI testing in session 0
        wait_activation = True
        gui_testing_active = os.getenv("CST_PYTHON_GUI_TESTING", "").lower() == "on"
        if gui_testing_active:
            import cst_context
            import cst_interface
            if cst_interface.IS_WINDOWS:
                import cstpy_ext
                if cstpy_ext.OSI.RemoteMFC().Win32API({'cmd':"ProcessIdToSessionId"}) == 0:
                    wait_activation = False

        if wait_activation:
            self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def buttonbox(self):
        '''add standard button box.

        override if you do not want the standard buttons
        '''

        box = ttk.Frame(self)

        w = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.RIGHT, padx=5, pady=5)
        w = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.RIGHT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack(fill=tk.X, side=tk.BOTTOM)


class CSTRootDialog(_AbstractCSTDialog):
    def __init__(self, title=None):
        self.parent = None
        self._tk_root = tk.Tk()
        self._tk_root.withdraw()

        gui_testing_active = os.getenv("CST_PYTHON_GUI_TESTING", "").lower() == "on"
        if gui_testing_active:
            import cst_context
            from remotetkinter.server import serve_remote_tkinter
            serve_remote_tkinter(self._tk_root)

        photo = tk.PhotoImage(width=1, height=1, master=self._tk_root)
        photo.blank()
        self._tk_root.iconphoto(True, photo)

        def report_error(*args):
            import traceback
            err_msg = traceback.format_exception(*args)
            tk.messagebox.showerror('Exception', ''.join(err_msg))

        self._tk_root.report_callback_exception = report_error
        _AbstractCSTDialog.__init__(self, self._tk_root, title)


class CSTChildDialog(_AbstractCSTDialog):
    def __init__(self, parent, title=None):
        _AbstractCSTDialog.__init__(self, parent, title)
