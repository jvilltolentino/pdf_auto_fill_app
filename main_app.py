"""
PDF Toolkit — Main App
-----------------------
A desktop GUI app combining two tools in one window:
  Tab 1: PDF Filler    — fills a PDF template with each row from an Excel sheet
  Tab 2: PDF Flattener — bakes form fields into permanent text (with optional encryption)

Output structure (one project folder, two subfolders, one log):
  [project folder]/
  ├── filled_pdfs/        <- Tab 1 writes here
  ├── flattened_pdfs/     <- Tab 2 writes here
  └── execution.log       <- shared timestamped log (both tabs append)

The two tabs share state through a small `shared_state` dict so Tab 2 can
auto-pick up the project folder Tab 1 just used.
"""

import tkinter as tk
from tkinter import ttk

from pdf_filler import PdfFillerTab
from pdf_flattener import PdfFlattenerTab


class PdfToolkitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Toolkit")
        self.geometry("820x720")
        self.minsize(740, 640)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Top header
        header = ttk.Frame(self, padding=(16, 12, 16, 4))
        header.pack(fill="x")
        ttk.Label(header, text="PDF Toolkit",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Fill PDFs from Excel data, then flatten them to lock the data in. "
                 "All outputs go in one project folder.",
            foreground="#666",
        ).pack(anchor="w")

        # Shared state — used by Tab 1 to tell Tab 2 which folder it just used.
        # Lets us pre-fill the project folder field on Tab 2 automatically.
        shared_state: dict = {}

        # Tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=8)

        filler_tab = PdfFillerTab(notebook, shared_state=shared_state)
        flattener_tab = PdfFlattenerTab(notebook, shared_state=shared_state)

        notebook.add(filler_tab, text="  1. Fill PDFs  ")
        notebook.add(flattener_tab, text="  2. Flatten PDFs  ")


def main():
    app = PdfToolkitApp()
    app.mainloop()


if __name__ == "__main__":
    main()
