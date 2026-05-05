# PDF Toolkit

A desktop GUI app with two tools in one window:

1. **Fill PDFs** — populates a fillable PDF template with each row from an Excel file
2. **Flatten PDFs** — bakes the form data into permanent text and (optionally) protects edits with an owner password

## What it does (the STAR)

- **Situation:** You have an Excel file (e.g. employees, invoices, certificates)
  and a fillable PDF template — and you want the final PDFs to be:
  (1) generated automatically, (2) locked so the data is permanent, and
  (3) optionally protected so recipients can read but not edit them.
- **Task:** Generate the PDFs, lock them, and keep an audit log — all
  organized in one tidy folder.
- **Action:** Tab 1 fills each row into the PDF template. Tab 2 flattens
  those filled PDFs and (optionally) applies an owner-password edit-lock.
- **Result:** A single project folder holding two subfolders and one log.

## Output structure

You pick **one project folder**. The app creates this for you:

```
[your project folder]/
├── filled_pdfs/         <- Tab 1 output
├── flattened_pdfs/      <- Tab 2 output
└── execution.log        <- shared timestamped log (both tabs append here)
```

> Think of the project folder as a **labeled file cabinet** for one job:
> the working drafts go in one drawer (`filled_pdfs/`), the final locked
> versions in another drawer (`flattened_pdfs/`), and the running activity
> log sits on top of the cabinet (`execution.log`).

## File structure (the code)

```
pdf_toolkit/
├── main_app.py        # Run this — the launcher with both tabs
├── pdf_filler.py      # Tab 1: PDF Filler
├── pdf_flattener.py   # Tab 2: PDF Flattener + edit protection
├── utils.py           # Shared logging, folder constants, helpers
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

1. Pick your **Excel/CSV file**, a **fillable PDF template**, and a **project folder**.
2. Map each PDF field to an Excel column (auto-guessed for you).
3. Click **Generate PDFs**. They appear in `[project folder]/filled_pdfs/`.

### Tab 2 — Flatten PDFs (with optional edit-protection)

1. Pick the **same project folder** (it's auto-suggested if you just ran Tab 1).
2. *(Optional)* Tick **🔒 Protect with owner password** and enter:
   - **Username** — recorded in the log for your records.
   - **Owner password** — needed to edit/annotate the file (NOT to view it).
3. Click **Flatten PDFs**. They appear in `[project folder]/flattened_pdfs/`.

## How edit-protection works

When you enable edit-protection, the PDFs use **AES-256** encryption with
an **owner password** only:

| Action | Without password | With owner password |
|---|---|---|
| Open & view | ✅ Allowed | ✅ Allowed |
| Print | ✅ Allowed | ✅ Allowed |
| Copy text | ✅ Allowed | ✅ Allowed |
| Edit content | ❌ Blocked | ✅ Allowed |
| Annotate | ❌ Blocked | ✅ Allowed |
| Fill forms | ❌ Blocked | ✅ Allowed |

> **Analogy:** like sending a sealed printed contract. The recipient can
> read it as much as they like, but they can't change what it says without
> coming back to you for permission.

This is different from a "user password" (also called an "open password"),
which would force recipients to type a password just to view the file. We
deliberately don't use that here — your recipients shouldn't need to know
a password for normal viewing.

## Execution log

The shared `execution.log` lives in your project folder and is **appended
to** every time a tab runs. Each line is tagged `[FILL]` or `[FLATTEN]` so
you can tell which run produced it.

### Sample log

```
[2026-05-05 12:01:18] [FILL] INFO — PDF FILL RUN STARTED
[2026-05-05 12:01:18] [FILL] INFO — Excel file:      /path/to/data.xlsx
[2026-05-05 12:01:18] [FILL] INFO — PDF template:    /path/to/template.pdf
[2026-05-05 12:01:18] [FILL] INFO — Project folder:  /path/to/project
[2026-05-05 12:01:18] [FILL] INFO — Output subfolder: /path/to/project/filled_pdfs
[2026-05-05 12:01:18] [FILL] INFO — Total rows:      3
[2026-05-05 12:01:18] [FILL] INFO — Row 1/3 — generated successfully: 001_Ana Cruz.pdf
[2026-05-05 12:01:18] [FILL] INFO — Row 2/3 — generated successfully: 002_Marco Reyes.pdf
[2026-05-05 12:01:18] [FILL] INFO — Row 3/3 — generated successfully: 003_Lea Santos.pdf
[2026-05-05 12:01:18] [FILL] INFO — FILL RUN COMPLETE
[2026-05-05 12:01:18] [FILL] INFO — Successes: 3 | Failures: 0
[2026-05-05 12:02:45] [FLATTEN] INFO — PDF FLATTEN RUN STARTED
[2026-05-05 12:02:45] [FLATTEN] INFO — Project folder:   /path/to/project
[2026-05-05 12:02:45] [FLATTEN] INFO — Input subfolder:  /path/to/project/filled_pdfs
[2026-05-05 12:02:45] [FLATTEN] INFO — Output subfolder: /path/to/project/flattened_pdfs
[2026-05-05 12:02:45] [FLATTEN] INFO — Edit-protection:  ENABLED (AES-256, owner password)
[2026-05-05 12:02:45] [FLATTEN] INFO — Username:         jdoe
[2026-05-05 12:02:45] [FLATTEN] INFO — Owner password:   MySecret123
[2026-05-05 12:02:45] [FLATTEN] INFO — Recipients can VIEW the PDFs freely; the owner password is
[2026-05-05 12:02:45] [FLATTEN] INFO — required only to EDIT, annotate, or modify them.
[2026-05-05 12:02:45] [FLATTEN] WARNING — This log contains the owner password. Protect or delete this log file once you've shared it.
[2026-05-05 12:02:45] [FLATTEN] INFO — PDF 1/3 — flattened successfully: 001_Ana Cruz.pdf → 001_Ana Cruz_flattened.pdf (2 field(s) baked in) [edit-protected]
...
```

### ⚠ Security note about the log

If you enable edit-protection, the log contains your **owner password** in
plain text (this is intentional — it's a record of which password was used
for which batch).

- **Don't share the log file** with anyone you don't want to give edit
  rights to.
- **Delete or move the log** to a secure location once you're done.
- If you'd rather not record the password, tick the **"Mask password in
  log"** option to write `●●●●●●●●●●` instead.

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

PyInstaller follows the import chain in `main_app.py` and bundles all four
Python files plus the libraries. The `.exe` appears in the `dist/` folder.

## Library roles (in plain words)

| Library | Used by | What it does | Analogy |
|---|---|---|---|
| `pandas` + `openpyxl` | Tab 1 | Reads Excel files | The "Excel translator" |
| `pypdf` | Tab 1 | Fills form fields in PDFs | The "PDF stamper" |
| `pymupdf` | Tab 2 | Flattens AND applies owner password | The "ink fixer + edit-lock" |
| `tkinter` | Both tabs | Builds the window/buttons | The "face" of the app (built into Python) |
