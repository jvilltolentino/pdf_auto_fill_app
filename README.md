# PDF Toolkit

A desktop GUI app with two tools in one window:

1. **Fill PDFs** — populates a fillable PDF template with each row from an Excel file
2. **Flatten PDFs** — bakes the form data into permanent text and (optionally) encrypts the file with a password

## What it does (the STAR)

- **Situation:** You have an Excel file (e.g. employees, invoices, certificates)
  and a fillable PDF template — and you want the final PDFs to be locked in
  so recipients can't edit them or even open them without permission.
- **Task:** Generate one filled-and-locked PDF per row, with a clear audit
  trail of what was created.
- **Action:** Tab 1 fills each row into the PDF template. Tab 2 flattens
  those filled PDFs and optionally encrypts them with a password.
- **Result:** A folder of locked-in PDFs, plus a timestamped log file for
  each step.

> **Three layers of safety**, one at a time:
> 1. Fill PDF (pencil — editable)
> 2. Flatten PDF (ink — permanent text)
> 3. Encrypt PDF (locked safe — password required)

## File structure

```
pdf_toolkit/
├── main_app.py        # Run this — the launcher with both tabs
├── pdf_filler.py      # Tab 1: PDF Filler logic + UI
├── pdf_flattener.py   # Tab 2: PDF Flattener + encryption logic + UI
├── utils.py           # Shared logging + filename helpers
├── requirements.txt   # Python libraries needed
└── README.md          # This file
```

## Setup (one-time)

You need Python 3.10 or newer.

```bash
cd pdf_toolkit

python -m venv venv

# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## Run the app

```bash
python main_app.py
```

A window opens with two tabs.

### Tab 1 — Fill PDFs

1. Pick your **Excel/CSV file**, a **fillable PDF template**, and an **output folder**.
2. Map each PDF field to an Excel column (auto-guessed for you).
3. Click **Generate PDFs**.

### Tab 2 — Flatten PDFs (with optional encryption)

1. Pick the **input folder** (e.g. the output folder from Tab 1).
2. Pick the **output folder** for flattened files.
3. *(Optional)* Tick **🔒 Encrypt PDFs with a password** and enter:
   - **Username** — recorded in the log for your records.
   - **Password** — needed to open the file and edit it.
4. Click **Flatten PDFs**.

## Encryption details

When encryption is enabled:

- PDFs are saved with **AES-256** (the strongest standard PDF encryption).
- Anyone trying to open the file is prompted for the password.
- Even after opening, the recipient **cannot modify or annotate** the file —
  but they can still view, print, and copy text.
- The original (unflattened) PDFs in the input folder are untouched.

> Think of it like a **safe with a viewing window**: people with the password
> can look inside and copy what they see, but they can't change what's in it.

## Execution logs

Every run creates a timestamped log file in the **output folder**:

- Filling produces: `execution_fill_2026-05-05_10-52-55.log`
- Flattening produces: `execution_flatten_2026-05-05_11-58-44.log`

Each log records:

- The input/output paths used
- A timestamped success line for each PDF generated/flattened
- For flattening with encryption: the **username and password** used
- A summary at the bottom (successes vs failures)

### Sample flatten log (with encryption)

```
[2026-05-05 11:58:44] INFO — PDF FLATTEN RUN STARTED
[2026-05-05 11:58:44] INFO — Input folder:  /home/user/filled_pdfs
[2026-05-05 11:58:44] INFO — Output folder: /home/user/locked_pdfs
[2026-05-05 11:58:44] INFO — Total PDFs:    3
[2026-05-05 11:58:44] INFO — Suffix:        _flattened
[2026-05-05 11:58:44] INFO — Encryption:    ENABLED (AES-256)
[2026-05-05 11:58:44] INFO — Username:      jdoe
[2026-05-05 11:58:44] INFO — Password:      MySecret123
[2026-05-05 11:58:44] WARNING — This log contains the password used to lock the PDFs. Protect or delete this log file once you've shared it.
[2026-05-05 11:58:44] INFO — PDF 1/3 — flattened successfully: 001_Ana Cruz.pdf → 001_Ana Cruz_flattened.pdf (2 field(s) baked in) [encrypted]
[2026-05-05 11:58:44] INFO — PDF 2/3 — flattened successfully: 002_Marco Reyes.pdf → 002_Marco Reyes_flattened.pdf (2 field(s) baked in) [encrypted]
[2026-05-05 11:58:44] INFO — PDF 3/3 — flattened successfully: 003_Lea Santos.pdf → 003_Lea Santos_flattened.pdf (2 field(s) baked in) [encrypted]
[2026-05-05 11:58:44] INFO — RUN COMPLETE
[2026-05-05 11:58:44] INFO — Successes: 3
[2026-05-05 11:58:44] INFO — Failures:  0
```

### ⚠ Security note about the log

If you enable encryption, the log file contains your password in plain text.
This is intentional — it gives you a record of which password was used for
which batch. However:

- **Don't share the log file** with anyone you don't want to give edit access to.
- **Delete or move the log** to a secure location once you're done.
- If you'd rather not log the password in plain text, tick the **"Mask password
  in log"** option — it'll write `●●●●●●●●●●` instead.

## Important: your PDF template must be "fillable"

Tab 1 needs a PDF that has real form fields (clickable text boxes). To
add form fields to a flat PDF, use:

- **Adobe Acrobat** (Prepare Form tool), or
- **LibreOffice Draw** (free).

If Tab 1 says "No fillable fields found," your PDF is just an image — add
form fields first.

## Building a single `.exe` (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "PDF Toolkit" main_app.py
```

PyInstaller follows the `import` chain in `main_app.py` and bundles all four
Python files plus the libraries. The `.exe` appears in the `dist/` folder.

## Library roles (in plain words)

| Library | Used by | What it does | Analogy |
|---|---|---|---|
| `pandas` + `openpyxl` | Tab 1 | Reads Excel files | The "Excel translator" |
| `pypdf` | Tab 1 | Fills form fields in PDFs | The "PDF stamper" |
| `pymupdf` | Tab 2 | Flattens AND encrypts PDFs | The "ink fixer + safe" |
| `tkinter` | Both tabs | Builds the window/buttons | The "face" of the app (built into Python) |
