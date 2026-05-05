"""
Tab 2 — PDF Flattener (with optional edit-protection)
------------------------------------------------------
Flattens fillable PDFs so the form data becomes permanent (non-editable),
and optionally protects them with an OWNER password.

Owner password vs user password:
  - Owner password (what we use): recipients can OPEN and VIEW freely, but
    cannot EDIT/annotate without the password.
  - User password (NOT used here): recipients couldn't even open the file
    without the password.

Analogy: like sending a sealed printed contract. The recipient can read it,
but can't change what it says. Editing requires authority you didn't grant.

Output structure:
  [parent_folder]/
  ├── filled_pdfs/        <- Tab 1 wrote here (this tab reads from here)
  ├── flattened_pdfs/     <- this tab writes here
  └── execution.log       <- shared log (this tab appends to it)
"""

import os
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import fitz  # PyMuPDF — handles flattening AND encryption

from utils import (
    setup_logger,
    close_logger,
    ensure_subfolder,
    FILLED_SUBFOLDER,
    FLATTENED_SUBFOLDER,
)


# -----------------------------
# Core flattening + encryption logic
# -----------------------------

def flatten_pdf(
    input_path: str,
    output_path: str,
    owner_password: str | None = None,
) -> int:
    """
    Flatten a single PDF and optionally apply an OWNER password.

    What the owner password does:
      - The recipient can OPEN and VIEW the PDF freely (no password to view).
      - But they CANNOT edit, modify, or annotate the file without the
        owner password.
      - Think of it like a museum exhibit: anyone can walk in and look,
        but only staff with the key can take a painting off the wall.

    We deliberately set user_pw="" (empty) so opening is free, and
    owner_pw=<your password> so editing requires the password.

    Returns the number of widgets that were baked in.
    """
    doc = fitz.open(input_path)
    widget_count = sum(len(list(page.widgets() or [])) for page in doc)

    if hasattr(doc, "bake"):
        doc.bake()
    else:
        for page in doc:
            if hasattr(page, "bake"):
                page.bake()

    save_kwargs = {"garbage": 4, "deflate": True}

    if owner_password:
        # Permissions GRANTED to anyone (no password needed):
        #   - viewing, printing (any quality), copying text, screen readers
        # Everything ELSE (modify, annotate, fill forms, assemble) is BLOCKED
        # unless the user provides the owner password.
        permissions = (
            fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_PRINT_HQ
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ACCESSIBILITY
        )
        save_kwargs.update({
            "encryption": fitz.PDF_ENCRYPT_AES_256,
            "user_pw": "",                  # empty -> file opens freely
            "owner_pw": owner_password,     # required to change permissions
            "permissions": permissions,
        })

    doc.save(output_path, **save_kwargs)
    doc.close()
    return widget_count


def list_pdfs_in_folder(folder: str) -> list[str]:
    """Return a sorted list of PDF file paths inside a folder (non-recursive)."""
    if not folder or not os.path.isdir(folder):
        return []
    return sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".pdf")
    ])


# -----------------------------
# GUI: Flattener Tab
# -----------------------------

class PdfFlattenerTab(ttk.Frame):
    """Self-contained tab that flattens (and optionally encrypts) PDFs."""

    def __init__(self, parent, shared_state=None):
        super().__init__(parent, padding=12)

        self.parent_dir: str | None = None
        self.pdf_files: list[str] = []
        self.suffix_var = tk.StringVar(value="")

        # Encryption state
        self.encrypt_var = tk.BooleanVar(value=False)
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.show_password_var = tk.BooleanVar(value=False)
        self.mask_in_log_var = tk.BooleanVar(value=False)

        self.shared_state = shared_state or {}

        self._build_ui()

        # If Tab 1 already ran, pre-fill the parent folder for convenience.
        # We bind to <Visibility> so it updates whenever the user switches to
        # this tab — picks up the value from the most recent fill run.
        self.bind("<Visibility>", self._on_visible)

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Flatten PDF forms",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Bake fillable form fields into permanent text. "
                 "Optionally protect the file from edits with an owner password.",
            foreground="#666",
        ).pack(anchor="w")

        # Step 1: Project folder
        step1 = ttk.LabelFrame(self, text=" Step 1 — Project folder ", padding=10)
        step1.pack(fill="x", pady=6)

        self._make_file_row(step1, "Project folder:", "parent", self._pick_parent_dir)

        tip_row = ttk.Frame(step1)
        tip_row.pack(fill="x", padx=(140, 0), pady=(0, 2))
        ttk.Label(
            tip_row,
            text="↳ Reads from [project folder]/filled_pdfs/, writes to [project folder]/flattened_pdfs/",
            foreground="#888", font=("Segoe UI", 8),
        ).pack(anchor="w")

        # Step 2: Options
        step2 = ttk.LabelFrame(self, text=" Step 2 — Options ", padding=10)
        step2.pack(fill="x", pady=6)

        suffix_row = ttk.Frame(step2)
        suffix_row.pack(fill="x", pady=2)
        ttk.Label(suffix_row, text="Filename suffix:", width=18).pack(side="left")
        ttk.Entry(suffix_row, textvariable=self.suffix_var, width=30).pack(side="left", padx=6)
        ttk.Label(suffix_row,
                  text="optional — e.g. '_final' makes 'invoice.pdf' → 'invoice_final.pdf'.",
                  foreground="#888", font=("Segoe UI", 8)).pack(side="left", padx=6)

        # Encryption checkbox
        enc_check_row = ttk.Frame(step2)
        enc_check_row.pack(fill="x", pady=(10, 2))
        ttk.Checkbutton(
            enc_check_row,
            text="🔒 Protect with owner password (recipients can view freely; need password to edit)",
            variable=self.encrypt_var,
            command=self._on_encrypt_toggle,
        ).pack(anchor="w")

        # Encryption fields container
        self.enc_frame = ttk.Frame(step2)
        self.enc_frame.pack(fill="x", pady=(2, 2), padx=(20, 0))

        user_row = ttk.Frame(self.enc_frame)
        user_row.pack(fill="x", pady=2)
        ttk.Label(user_row, text="Username:", width=14).pack(side="left")
        self.username_entry = ttk.Entry(user_row, textvariable=self.username_var, width=30)
        self.username_entry.pack(side="left", padx=6)
        ttk.Label(user_row, text="(for your records — appears in the log)",
                  foreground="#888", font=("Segoe UI", 8)).pack(side="left", padx=6)

        pw_row = ttk.Frame(self.enc_frame)
        pw_row.pack(fill="x", pady=2)
        ttk.Label(pw_row, text="Password:", width=14).pack(side="left")
        self.password_entry = ttk.Entry(
            pw_row, textvariable=self.password_var, width=30, show="•"
        )
        self.password_entry.pack(side="left", padx=6)
        ttk.Checkbutton(
            pw_row, text="show", variable=self.show_password_var,
            command=self._toggle_show_password,
        ).pack(side="left")
        ttk.Label(pw_row, text="(needed to edit, not view)",
                  foreground="#888", font=("Segoe UI", 8)).pack(side="left", padx=6)

        warn_row = ttk.Frame(self.enc_frame)
        warn_row.pack(fill="x", pady=(6, 2))
        ttk.Label(
            warn_row,
            text="⚠ The username and owner password will appear in the execution log. Protect or delete the log when done.",
            foreground="#A33", font=("Segoe UI", 8),
        ).pack(anchor="w")
        ttk.Checkbutton(
            warn_row,
            text="Mask owner password in log (show as ●●●●●● instead of plain text)",
            variable=self.mask_in_log_var,
        ).pack(anchor="w")

        # Found-files preview
        files_row = ttk.Frame(step2)
        files_row.pack(fill="x", pady=(10, 2))
        self.files_lbl = ttk.Label(files_row, text="No project folder selected.",
                                   foreground="#666")
        self.files_lbl.pack(side="left")

        # Step 3: Run
        step3 = ttk.LabelFrame(self, text=" Step 3 — Flatten PDFs ", padding=10)
        step3.pack(fill="x", pady=(6, 0))

        action_row = ttk.Frame(step3)
        action_row.pack(fill="x")
        self.run_btn = ttk.Button(action_row, text="Flatten PDFs",
                                  command=self._on_run, state="disabled")
        self.run_btn.pack(side="left")

        self.progress = ttk.Progressbar(step3, mode="determinate")
        self.progress.pack(fill="x", pady=(8, 4))

        self.status_lbl = ttk.Label(step3, text="Waiting...", foreground="#666")
        self.status_lbl.pack(anchor="w")

        # Initialize encryption fields as disabled
        self._on_encrypt_toggle()

    def _make_file_row(self, parent, label_text, kind, command):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label_text, width=18).pack(side="left")
        var = tk.StringVar(value="(none selected)")
        setattr(self, f"{kind}_path_var", var)
        ttk.Label(row, textvariable=var, foreground="#444").pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="Browse...", command=command).pack(side="right")

    # ---- Encryption UI helpers ----
    def _on_encrypt_toggle(self):
        state = "normal" if self.encrypt_var.get() else "disabled"
        for child in self.enc_frame.winfo_children():
            for grandchild in child.winfo_children():
                try:
                    grandchild.configure(state=state)
                except tk.TclError:
                    pass

    def _toggle_show_password(self):
        self.password_entry.configure(show="" if self.show_password_var.get() else "•")

    # ---- Visibility hook: pre-fill folder if Tab 1 just finished ----
    def _on_visible(self, event):
        suggested = self.shared_state.get("last_parent_dir")
        if suggested and not self.parent_dir:
            self._set_parent_dir(suggested)

    # ---- Pickers ----
    def _pick_parent_dir(self):
        path = filedialog.askdirectory(title="Choose project folder")
        if not path:
            return
        self._set_parent_dir(path)

    def _set_parent_dir(self, path: str):
        self.parent_dir = path
        self.parent_path_var.set(path)

        # Look for the filled_pdfs subfolder and list its PDFs
        filled_dir = os.path.join(path, FILLED_SUBFOLDER)
        self.pdf_files = list_pdfs_in_folder(filled_dir)

        if not os.path.isdir(filled_dir):
            self.files_lbl.configure(
                text=f"⚠ No '{FILLED_SUBFOLDER}/' subfolder found here. "
                     f"Run Tab 1 first or pick a different folder.",
                foreground="#A33",
            )
        elif not self.pdf_files:
            self.files_lbl.configure(
                text=f"'{FILLED_SUBFOLDER}/' folder is empty.",
                foreground="#A33",
            )
        else:
            self.files_lbl.configure(
                text=f"Found {len(self.pdf_files)} PDF(s) in '{FILLED_SUBFOLDER}/'.",
                foreground="#666",
            )

        self._refresh_run_button()

    def _refresh_run_button(self):
        ready = bool(self.parent_dir and self.pdf_files)
        self.run_btn.configure(state="normal" if ready else "disabled")

    # ---- Run ----
    def _on_run(self):
        if not (self.parent_dir and self.pdf_files):
            return

        if self.encrypt_var.get() and not self.password_var.get():
            messagebox.showwarning(
                "Owner password required",
                "You enabled edit-protection but didn't enter an owner password. "
                "Please enter one or uncheck the protection box.",
            )
            return

        self.run_btn.configure(state="disabled")
        threading.Thread(target=self._run_flattening, daemon=True).start()

    def _run_flattening(self):
        total = len(self.pdf_files)
        self.progress.configure(maximum=total, value=0)
        successes = 0
        errors: list[str] = []
        suffix = self.suffix_var.get()  # empty string = keep original filename

        # Make sure the flattened_pdfs subfolder exists
        flattened_dir = ensure_subfolder(self.parent_dir, FLATTENED_SUBFOLDER)

        # Encryption settings
        encrypt = self.encrypt_var.get()
        username = self.username_var.get().strip() if encrypt else ""
        password = self.password_var.get() if encrypt else ""
        mask = self.mask_in_log_var.get()
        password_for_log = ("●" * len(password)) if (encrypt and mask) else password

        # Append to the shared log
        logger, log_path = setup_logger(self.parent_dir, run_tag="FLATTEN")
        logger.info("=" * 60)
        logger.info("PDF FLATTEN RUN STARTED")
        logger.info("=" * 60)
        logger.info(f"Project folder:   {self.parent_dir}")
        logger.info(f"Input subfolder:  {os.path.join(self.parent_dir, FILLED_SUBFOLDER)}")
        logger.info(f"Output subfolder: {flattened_dir}")
        logger.info(f"Total PDFs:       {total}")
        logger.info(f"Suffix:           {repr(suffix) if suffix else '(none — keeping original filenames)'}")
        logger.info(f"Edit-protection:  {'ENABLED (AES-256, owner password)' if encrypt else 'disabled'}")
        if encrypt:
            logger.info(f"Username:         {username or '(not provided)'}")
            logger.info(f"Owner password:   {password_for_log}")
            logger.info("Recipients can VIEW the PDFs freely; the owner password is")
            logger.info("required only to EDIT, annotate, or modify them.")
            logger.warning(
                "This log contains the owner password. "
                "Protect or delete this log file once you've shared it."
            )
        logger.info("-" * 60)

        for i, pdf_path in enumerate(self.pdf_files, start=1):
            src_name = Path(pdf_path).name
            try:
                stem = Path(pdf_path).stem
                out_name = f"{stem}{suffix}.pdf"
                out_path = os.path.join(flattened_dir, out_name)

                if os.path.realpath(out_path) == os.path.realpath(pdf_path):
                    raise RuntimeError(
                        "Output path matches input path — this would overwrite the source file. "
                        "Make sure the input and output subfolders are different, "
                        "or add a filename suffix."
                    )

                widget_count = flatten_pdf(
                    pdf_path,
                    out_path,
                    owner_password=password if encrypt else None,
                )
                successes += 1
                lock_note = " [edit-protected]" if encrypt else ""
                logger.info(
                    f"PDF {i}/{total} — flattened successfully: {src_name} → {out_name} "
                    f"({widget_count} field(s) baked in){lock_note}"
                )
            except Exception as e:
                errors.append(f"{src_name}: {e}")
                logger.error(f"PDF {i}/{total} — FAILED: {src_name} — {e}")

            self.after(0, self._update_progress, i, total)

        logger.info("-" * 60)
        logger.info("FLATTEN RUN COMPLETE")
        logger.info(f"Successes: {successes}")
        logger.info(f"Failures:  {len(errors)}")
        logger.info("=" * 60)
        close_logger(logger)

        self.after(0, self._finish, successes, errors, log_path, encrypt, flattened_dir)

    def _update_progress(self, current: int, total: int):
        self.progress.configure(value=current)
        self.status_lbl.configure(text=f"Flattening... {current} / {total}")

    def _finish(self, successes: int, errors: list[str], log_path: str,
                encrypted: bool, flattened_dir: str):
        self.run_btn.configure(state="normal")
        lock_msg = " (edit-protected)" if encrypted else ""
        if errors:
            self.status_lbl.configure(
                text=f"Done with {len(errors)} error(s). {successes} PDFs in '{Path(flattened_dir).name}/'."
            )
            messagebox.showwarning(
                "Finished with errors",
                f"Flattened {successes} PDFs{lock_msg} in:\n{flattened_dir}\n\n"
                f"Log: {log_path}\n\nErrors:\n"
                + "\n".join(errors[:10])
                + ("\n..." if len(errors) > 10 else ""),
            )
        else:
            self.status_lbl.configure(
                text=f"Done! {successes} PDFs flattened{lock_msg} in '{Path(flattened_dir).name}/'."
            )
            messagebox.showinfo(
                "Success",
                f"Flattened {successes} PDFs{lock_msg} in:\n{flattened_dir}\n\n"
                f"Log file: {log_path}",
            )
