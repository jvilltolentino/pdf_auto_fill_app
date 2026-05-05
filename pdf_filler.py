"""
Tab 1 — PDF Filler
-------------------
Fills an existing fillable PDF template using each row from an Excel file.

Output structure:
  [parent_folder]/
  ├── filled_pdfs/     <- the generated PDFs go here
  └── execution.log    <- shared log (appended to)
"""

import os
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

from utils import (
    safe_filename,
    setup_logger,
    close_logger,
    ensure_subfolder,
    FILLED_SUBFOLDER,
)


# -----------------------------
# Core PDF + Excel logic
# -----------------------------

def read_excel(path: str) -> pd.DataFrame:
    """Read an Excel or CSV file into a pandas DataFrame."""
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def get_pdf_fields(pdf_path: str) -> list[str]:
    """Return the list of fillable field names in the PDF template."""
    reader = PdfReader(pdf_path)
    fields = reader.get_fields() or {}
    return list(fields.keys())


def fill_pdf(template_path: str, output_path: str, data: dict) -> None:
    """Fill a PDF template with a data dictionary and save the result."""
    reader = PdfReader(template_path)
    writer = PdfWriter(clone_from=reader)
    str_data = {k: ("" if v is None else str(v)) for k, v in data.items()}

    for page in writer.pages:
        if "/Annots" in page:
            writer.update_page_form_field_values(page, str_data)

    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update(
            {NameObject("/NeedAppearances"): BooleanObject(True)}
        )

    with open(output_path, "wb") as f:
        writer.write(f)


# -----------------------------
# GUI: Filler Tab
# -----------------------------

class PdfFillerTab(ttk.Frame):
    """Self-contained tab that fills PDFs from an Excel sheet."""

    def __init__(self, parent, shared_state=None):
        super().__init__(parent, padding=12)

        # State
        self.excel_path: str | None = None
        self.pdf_path: str | None = None
        self.parent_dir: str | None = None
        self.df: pd.DataFrame | None = None
        self.pdf_fields: list[str] = []
        self.mappings: dict[str, tk.StringVar] = {}
        self.name_field_var = tk.StringVar()

        # Shared state lets the two tabs talk to each other (e.g. when this
        # tab finishes, it tells the flattener tab to use the same folder).
        self.shared_state = shared_state or {}

        self._build_ui()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Fill PDF forms from Excel data",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Pick an Excel file, a fillable PDF template, and a project folder. "
                 "Filled PDFs will be saved in a 'filled_pdfs' subfolder.",
            foreground="#666",
        ).pack(anchor="w")

        # Step 1: File selection
        step1 = ttk.LabelFrame(self, text=" Step 1 — Choose files ", padding=10)
        step1.pack(fill="x", pady=6)

        self._make_file_row(step1, "Excel / CSV file:", "excel", self._pick_excel)
        self._make_file_row(step1, "PDF template:", "pdf", self._pick_pdf)
        self._make_file_row(step1, "Project folder:", "parent", self._pick_parent_dir)

        # Tip about folder structure
        tip_row = ttk.Frame(step1)
        tip_row.pack(fill="x", padx=(140, 0), pady=(0, 2))
        ttk.Label(
            tip_row,
            text="↳ Filled PDFs will go in [project folder]/filled_pdfs/",
            foreground="#888", font=("Segoe UI", 8),
        ).pack(anchor="w")

        # Step 2: Mapping
        step2 = ttk.LabelFrame(self, text=" Step 2 — Map PDF fields to Excel columns ", padding=10)
        step2.pack(fill="both", expand=True, pady=6)

        canvas_container = ttk.Frame(step2)
        canvas_container.pack(fill="both", expand=True)

        self.map_canvas = tk.Canvas(canvas_container, highlightthickness=0, height=180)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.map_canvas.yview)
        self.map_canvas.configure(yscrollcommand=scrollbar.set)
        self.map_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.map_frame = ttk.Frame(self.map_canvas)
        self.map_canvas.create_window((0, 0), window=self.map_frame, anchor="nw")
        self.map_frame.bind(
            "<Configure>",
            lambda e: self.map_canvas.configure(scrollregion=self.map_canvas.bbox("all")),
        )

        self.map_placeholder = ttk.Label(
            self.map_frame,
            text="↑ Choose an Excel file and a PDF template above to see field mappings here.",
            foreground="#666",
        )
        self.map_placeholder.pack(pady=20, padx=10, anchor="w")

        # Filename source selector
        name_frame = ttk.Frame(step2)
        name_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(name_frame, text="Use this field for output filenames:").pack(side="left")
        self.name_combo = ttk.Combobox(name_frame, textvariable=self.name_field_var,
                                       state="disabled", width=30)
        self.name_combo.pack(side="left", padx=8)

        # Step 3: Generate
        step3 = ttk.LabelFrame(self, text=" Step 3 — Generate filled PDFs ", padding=10)
        step3.pack(fill="x", pady=(6, 0))

        action_row = ttk.Frame(step3)
        action_row.pack(fill="x")
        self.generate_btn = ttk.Button(action_row, text="Generate PDFs",
                                       command=self._on_generate, state="disabled")
        self.generate_btn.pack(side="left")

        self.progress = ttk.Progressbar(step3, mode="determinate")
        self.progress.pack(fill="x", pady=(8, 4))

        self.status_lbl = ttk.Label(step3, text="Waiting...", foreground="#666")
        self.status_lbl.pack(anchor="w")

    def _make_file_row(self, parent, label_text, kind, command):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label_text, width=18).pack(side="left")
        var = tk.StringVar(value="(none selected)")
        setattr(self, f"{kind}_path_var", var)
        ttk.Label(row, textvariable=var, foreground="#444").pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="Browse...", command=command).pack(side="right")

    # ---- File pickers ----
    def _pick_excel(self):
        path = filedialog.askopenfilename(
            title="Choose Excel or CSV file",
            filetypes=[("Excel/CSV files", "*.xlsx *.xls *.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.df = read_excel(path)
        except Exception as e:
            messagebox.showerror("Cannot read file", f"Could not read the spreadsheet:\n{e}")
            return
        self.excel_path = path
        self.excel_path_var.set(
            f"{Path(path).name}  —  {len(self.df)} rows, {len(self.df.columns)} columns"
        )
        self._refresh_mapping_area()
        self._refresh_generate_button()

    def _pick_pdf(self):
        path = filedialog.askopenfilename(
            title="Choose fillable PDF template",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            fields = get_pdf_fields(path)
        except Exception as e:
            messagebox.showerror("Cannot read PDF", f"Could not read PDF fields:\n{e}")
            return
        if not fields:
            messagebox.showwarning(
                "No fillable fields found",
                "This PDF doesn't contain any fillable form fields.\n\n"
                "Tip: open it in Adobe Acrobat or LibreOffice and add form fields, "
                "or pick a different template.",
            )
            return
        self.pdf_path = path
        self.pdf_fields = fields
        self.pdf_path_var.set(f"{Path(path).name}  —  {len(fields)} fillable fields")
        self._refresh_mapping_area()
        self._refresh_generate_button()

    def _pick_parent_dir(self):
        path = filedialog.askdirectory(title="Choose project folder")
        if not path:
            return
        self.parent_dir = path
        self.parent_path_var.set(path)
        self._refresh_generate_button()

    # ---- Mapping UI ----
    def _refresh_mapping_area(self):
        for child in self.map_frame.winfo_children():
            child.destroy()
        self.mappings = {}

        if not (self.df is not None and self.pdf_fields):
            self.map_placeholder = ttk.Label(
                self.map_frame,
                text="↑ Choose an Excel file and a PDF template above to see field mappings here.",
                foreground="#666",
            )
            self.map_placeholder.pack(pady=20, padx=10, anchor="w")
            self.name_combo.configure(state="disabled", values=[])
            return

        header_row = ttk.Frame(self.map_frame)
        header_row.pack(fill="x", pady=(0, 4))
        ttk.Label(header_row, text="PDF field", width=30,
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        ttk.Label(header_row, text="Excel column",
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)

        excel_cols = list(self.df.columns)
        options = ["(skip)"] + [str(c) for c in excel_cols]

        for field in self.pdf_fields:
            row = ttk.Frame(self.map_frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=field, width=30).pack(side="left", padx=4)

            var = tk.StringVar()
            guess = self._guess_match(field, excel_cols)
            var.set(guess if guess else "(skip)")

            combo = ttk.Combobox(row, textvariable=var, values=options,
                                 state="readonly", width=35)
            combo.pack(side="left", padx=4)
            self.mappings[field] = var

        self.name_combo.configure(state="readonly", values=self.pdf_fields)
        default_name = next((f for f in self.pdf_fields if "name" in f.lower()),
                            self.pdf_fields[0])
        self.name_field_var.set(default_name)

    def _guess_match(self, pdf_field: str, excel_cols: list) -> str | None:
        pf = pdf_field.lower().replace(" ", "").replace("_", "")
        for col in excel_cols:
            cl = str(col).lower().replace(" ", "").replace("_", "")
            if pf == cl or pf in cl or cl in pf:
                return str(col)
        return None

    def _refresh_generate_button(self):
        ready = bool(self.excel_path and self.pdf_path and self.parent_dir)
        self.generate_btn.configure(state="normal" if ready else "disabled")

    # ---- Generation ----
    def _on_generate(self):
        if not (self.df is not None and self.pdf_path and self.parent_dir):
            return

        active_map = {pdf_f: var.get() for pdf_f, var in self.mappings.items()
                      if var.get() != "(skip)"}
        if not active_map:
            messagebox.showwarning("No mappings",
                                   "Please map at least one PDF field to an Excel column.")
            return

        name_field = self.name_field_var.get()
        self.generate_btn.configure(state="disabled")
        threading.Thread(
            target=self._run_generation,
            args=(active_map, name_field),
            daemon=True,
        ).start()

    def _run_generation(self, active_map: dict, name_field: str):
        total = len(self.df)
        self.progress.configure(maximum=total, value=0)
        successes = 0
        errors: list[str] = []

        # Make sure the 'filled_pdfs' subfolder exists in the parent folder
        filled_dir = ensure_subfolder(self.parent_dir, FILLED_SUBFOLDER)

        # Open the shared log in append mode and tag every line with [FILL]
        logger, log_path = setup_logger(self.parent_dir, run_tag="FILL")
        logger.info("=" * 60)
        logger.info("PDF FILL RUN STARTED")
        logger.info("=" * 60)
        logger.info(f"Excel file:      {self.excel_path}")
        logger.info(f"PDF template:    {self.pdf_path}")
        logger.info(f"Project folder:  {self.parent_dir}")
        logger.info(f"Output subfolder: {filled_dir}")
        logger.info(f"Total rows:      {total}")
        logger.info(f"Field mappings:  {active_map}")
        logger.info(f"Filename source field: {name_field}")
        logger.info("-" * 60)

        for i, (_, row) in enumerate(self.df.iterrows(), start=1):
            try:
                data = {pdf_f: row[excel_col]
                        for pdf_f, excel_col in active_map.items()
                        if excel_col in row.index}

                name_source = data.get(name_field) or f"row_{i}"
                fname = f"{i:03d}_{safe_filename(name_source)}.pdf"
                out_path = os.path.join(filled_dir, fname)

                fill_pdf(self.pdf_path, out_path, data)
                successes += 1
                logger.info(f"Row {i}/{total} — generated successfully: {fname}")
            except Exception as e:
                errors.append(f"Row {i}: {e}")
                logger.error(f"Row {i}/{total} — FAILED: {e}")

            self.after(0, self._update_progress, i, total)

        logger.info("-" * 60)
        logger.info("FILL RUN COMPLETE")
        logger.info(f"Successes: {successes}")
        logger.info(f"Failures:  {len(errors)}")
        logger.info("=" * 60)
        close_logger(logger)

        # Tell the flattener tab where this output went, so it can pre-fill
        # its own input folder field next time the user clicks that tab.
        self.shared_state["last_parent_dir"] = self.parent_dir
        self.shared_state["last_filled_dir"] = filled_dir

        self.after(0, self._finish_generation, successes, errors, log_path, filled_dir)

    def _update_progress(self, current: int, total: int):
        self.progress.configure(value=current)
        self.status_lbl.configure(text=f"Generating... {current} / {total}")

    def _finish_generation(self, successes: int, errors: list[str],
                           log_path: str, filled_dir: str):
        self.generate_btn.configure(state="normal")
        if errors:
            self.status_lbl.configure(
                text=f"Done with {len(errors)} error(s). {successes} PDFs in '{Path(filled_dir).name}/'."
            )
            messagebox.showwarning(
                "Finished with errors",
                f"Generated {successes} PDFs in:\n{filled_dir}\n\n"
                f"Log: {log_path}\n\nErrors:\n"
                + "\n".join(errors[:10])
                + ("\n..." if len(errors) > 10 else ""),
            )
        else:
            self.status_lbl.configure(
                text=f"Done! {successes} PDFs in '{Path(filled_dir).name}/'. Now switch to the Flatten tab."
            )
            messagebox.showinfo(
                "Success",
                f"Generated {successes} PDFs in:\n{filled_dir}\n\n"
                f"Log file: {log_path}\n\n"
                f"Next: switch to the 'Flatten PDFs' tab to lock these PDFs.",
            )
