"""
Tab 2 — PDF Flattener (with optional encryption)
-------------------------------------------------
Flattens fillable PDFs so the form data becomes permanent (non-editable),
and optionally encrypts them with a password to prevent unauthorized edits.

How it works (STAR):
  - Situation: Filled PDFs still have editable form fields. And even after
    flattening, anyone can still annotate or modify them.
  - Task:      "Bake" the data into the page AND lock the file with a password.
  - Action:    Use PyMuPDF's doc.bake() to flatten, then save with AES-256
               encryption using the password the user provides.
  - Result:    Locked-in PDFs that need a password to open, and once open,
               cannot be edited.

Analogy: Filling a form in pencil (editable) → tracing in ink (flattened)
→ putting it in a locked safe (encrypted). Each step adds a layer of safety.
"""

import os
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import fitz  # PyMuPDF — handles flattening AND encryption

from utils import setup_logger, close_logger


# -----------------------------
# Core flattening + encryption logic
# -----------------------------

def flatten_pdf(
    input_path: str,
    output_path: str,
    user_password: str | None = None,
    owner_password: str | None = None,
) -> int:
    """
    Flatten a single PDF and optionally encrypt it.

    Args:
        input_path:      The source PDF.
        output_path:     Where to save the result.
        user_password:   If set, the password needed to OPEN the PDF.
        owner_password:  If set, the password needed to CHANGE permissions.
                         (Falls back to user_password if not provided.)

    Returns the number of widgets that were baked in.

    Encryption is only applied when a password is provided. Otherwise the
    file is just flattened (same behavior as before).
    """
    doc = fitz.open(input_path)

    # Count widgets before flattening so we can log what got baked in
    widget_count = sum(len(list(page.widgets() or [])) for page in doc)

    # Bake form fields into permanent page content
    if hasattr(doc, "bake"):
        doc.bake()
    else:
        for page in doc:
            if hasattr(page, "bake"):
                page.bake()

    # Build save options. If a password was provided, add encryption.
    save_kwargs = {"garbage": 4, "deflate": True}

    if user_password:
        # Permissions: viewers can READ and PRINT, but NOT modify or annotate.
        # This is what prevents post-flatten edits.
        permissions = (
            fitz.PDF_PERM_PRINT          # allow printing
            | fitz.PDF_PERM_PRINT_HQ     # allow high-quality printing
            | fitz.PDF_PERM_COPY         # allow text copy
            | fitz.PDF_PERM_ACCESSIBILITY  # allow screen readers
        )
        save_kwargs.update({
            "encryption": fitz.PDF_ENCRYPT_AES_256,  # strongest standard option
            "user_pw": user_password,
            "owner_pw": owner_password or user_password,
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
    """A self-contained Tab that flattens (and optionally encrypts) PDFs."""

    def __init__(self, parent):
        super().__init__(parent, padding=12)

        # State
        self.input_dir: str | None = None
        self.output_dir: str | None = None
        self.pdf_files: list[str] = []
        self.suffix_var = tk.StringVar(value="_flattened")

        # Encryption fields
        self.encrypt_var = tk.BooleanVar(value=False)
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.show_password_var = tk.BooleanVar(value=False)
        self.mask_in_log_var = tk.BooleanVar(value=False)  # default: log in plain text

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Flatten PDF forms",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(header,
                  text="Bake fillable form fields into permanent text. Optionally lock the file with a password.",
                  foreground="#666").pack(anchor="w")

        # Step 1: Choose folders
        step1 = ttk.LabelFrame(self, text=" Step 1 — Choose folders ", padding=10)
        step1.pack(fill="x", pady=6)

        self._make_file_row(step1, "Input folder (PDFs):", "input", self._pick_input_dir)
        self._make_file_row(step1, "Output folder:", "out", self._pick_output_dir)

        # Step 2: Options
        step2 = ttk.LabelFrame(self, text=" Step 2 — Options ", padding=10)
        step2.pack(fill="x", pady=6)

        # Filename suffix
        suffix_row = ttk.Frame(step2)
        suffix_row.pack(fill="x", pady=2)
        ttk.Label(suffix_row, text="Filename suffix:", width=18).pack(side="left")
        ttk.Entry(suffix_row, textvariable=self.suffix_var, width=30).pack(side="left", padx=6)
        ttk.Label(suffix_row,
                  text="e.g. 'invoice.pdf' becomes 'invoice_flattened.pdf'",
                  foreground="#888", font=("Segoe UI", 8)).pack(side="left", padx=6)

        # Encryption checkbox
        enc_check_row = ttk.Frame(step2)
        enc_check_row.pack(fill="x", pady=(10, 2))
        ttk.Checkbutton(
            enc_check_row,
            text="🔒 Encrypt PDFs with a password (prevents anyone from editing them)",
            variable=self.encrypt_var,
            command=self._on_encrypt_toggle,
        ).pack(anchor="w")

        # Encryption fields container — gets enabled/disabled by the checkbox
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

        # Log warning + masking option
        warn_row = ttk.Frame(self.enc_frame)
        warn_row.pack(fill="x", pady=(6, 2))
        ttk.Label(
            warn_row,
            text="⚠ The username and password will appear in the execution log. Protect or delete the log when done.",
            foreground="#A33", font=("Segoe UI", 8),
        ).pack(anchor="w")
        ttk.Checkbutton(
            warn_row,
            text="Mask password in log (show as ●●●●●● instead of plain text)",
            variable=self.mask_in_log_var,
        ).pack(anchor="w", padx=(0, 0))

        # Found-files preview
        files_row = ttk.Frame(step2)
        files_row.pack(fill="x", pady=(10, 2))
        self.files_lbl = ttk.Label(files_row, text="No input folder selected.",
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

        # Initialize encryption fields as disabled (checkbox starts off)
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
        """Enable or disable the encryption fields based on the checkbox."""
        state = "normal" if self.encrypt_var.get() else "disabled"
        for child in self.enc_frame.winfo_children():
            for grandchild in child.winfo_children():
                try:
                    grandchild.configure(state=state)
                except tk.TclError:
                    pass

    def _toggle_show_password(self):
        """Toggle masking in the password entry box."""
        self.password_entry.configure(show="" if self.show_password_var.get() else "•")

    # ---- Pickers ----
    def _pick_input_dir(self):
        path = filedialog.askdirectory(title="Choose folder containing PDFs to flatten")
        if not path:
            return
        self.input_dir = path
        self.pdf_files = list_pdfs_in_folder(path)
        self.input_path_var.set(path)
        self.files_lbl.configure(
            text=f"Found {len(self.pdf_files)} PDF file(s) in this folder."
        )
        self._refresh_run_button()

    def _pick_output_dir(self):
        path = filedialog.askdirectory(title="Choose output folder")
        if not path:
            return
        self.output_dir = path
        self.out_path_var.set(path)
        self._refresh_run_button()

    def _refresh_run_button(self):
        ready = bool(self.input_dir and self.output_dir and self.pdf_files)
        self.run_btn.configure(state="normal" if ready else "disabled")

    # ---- Run ----
    def _on_run(self):
        if not (self.input_dir and self.output_dir and self.pdf_files):
            return

        # Validate encryption inputs if encryption is on
        if self.encrypt_var.get() and not self.password_var.get():
            messagebox.showwarning(
                "Password required",
                "You enabled encryption but didn't enter a password. "
                "Please enter a password or uncheck the encryption box.",
            )
            return

        if os.path.realpath(self.input_dir) == os.path.realpath(self.output_dir):
            if not messagebox.askyesno(
                "Same folder for input and output",
                "Input and output folders are the same. Output files will sit "
                "alongside the originals (using the suffix you chose).\n\nContinue?",
            ):
                return

        self.run_btn.configure(state="disabled")
        threading.Thread(target=self._run_flattening, daemon=True).start()

    def _run_flattening(self):
        total = len(self.pdf_files)
        self.progress.configure(maximum=total, value=0)
        successes = 0
        errors: list[str] = []
        suffix = self.suffix_var.get() or "_flattened"

        # Pull encryption settings
        encrypt = self.encrypt_var.get()
        username = self.username_var.get().strip() if encrypt else ""
        password = self.password_var.get() if encrypt else ""
        mask = self.mask_in_log_var.get()
        password_for_log = ("●" * len(password)) if (encrypt and mask) else password

        # Set up the per-run log file
        logger, log_path = setup_logger(self.output_dir, prefix="flatten")
        logger.info("=" * 60)
        logger.info("PDF FLATTEN RUN STARTED")
        logger.info("=" * 60)
        logger.info(f"Input folder:  {self.input_dir}")
        logger.info(f"Output folder: {self.output_dir}")
        logger.info(f"Total PDFs:    {total}")
        logger.info(f"Suffix:        {suffix}")
        logger.info(f"Encryption:    {'ENABLED (AES-256)' if encrypt else 'disabled'}")
        if encrypt:
            logger.info(f"Username:      {username or '(not provided)'}")
            logger.info(f"Password:      {password_for_log}")
            logger.warning(
                "This log contains the password used to lock the PDFs. "
                "Protect or delete this log file once you've shared it."
            )
        logger.info("-" * 60)

        for i, pdf_path in enumerate(self.pdf_files, start=1):
            src_name = Path(pdf_path).name
            try:
                stem = Path(pdf_path).stem
                out_name = f"{stem}{suffix}.pdf"
                out_path = os.path.join(self.output_dir, out_name)

                if os.path.realpath(out_path) == os.path.realpath(pdf_path):
                    raise RuntimeError(
                        "Output filename matches input — change the suffix to avoid overwriting."
                    )

                widget_count = flatten_pdf(
                    pdf_path,
                    out_path,
                    user_password=password if encrypt else None,
                )
                successes += 1
                lock_note = " [encrypted]" if encrypt else ""
                logger.info(
                    f"PDF {i}/{total} — flattened successfully: {src_name} → {out_name} "
                    f"({widget_count} field(s) baked in){lock_note}"
                )
            except Exception as e:
                errors.append(f"{src_name}: {e}")
                logger.error(f"PDF {i}/{total} — FAILED: {src_name} — {e}")

            self.after(0, self._update_progress, i, total)

        logger.info("-" * 60)
        logger.info("RUN COMPLETE")
        logger.info(f"Successes: {successes}")
        logger.info(f"Failures:  {len(errors)}")
        logger.info("=" * 60)
        close_logger(logger)

        self.after(0, self._finish, successes, errors, log_path, encrypt)

    def _update_progress(self, current: int, total: int):
        self.progress.configure(value=current)
        self.status_lbl.configure(text=f"Flattening... {current} / {total}")

    def _finish(self, successes: int, errors: list[str], log_path: str, encrypted: bool):
        self.run_btn.configure(state="normal")
        log_name = Path(log_path).name
        lock_msg = " (encrypted)" if encrypted else ""
        if errors:
            self.status_lbl.configure(
                text=f"Done with {len(errors)} error(s). {successes} PDFs flattened{lock_msg}. Log: {log_name}"
            )
            messagebox.showwarning(
                "Finished with errors",
                f"Flattened {successes} PDFs{lock_msg}.\n\nLog file: {log_name}\n\nErrors:\n"
                + "\n".join(errors[:10])
                + ("\n..." if len(errors) > 10 else ""),
            )
        else:
            self.status_lbl.configure(
                text=f"Done! {successes} PDFs flattened{lock_msg} in: {self.output_dir} (log: {log_name})"
            )
            messagebox.showinfo(
                "Success",
                f"Flattened {successes} PDFs{lock_msg} in:\n{self.output_dir}\n\nLog file: {log_name}",
            )
