# LabCV (sorted)

**What is this (r/ELI5):** A tiny local app where a camera looks at lab items, the computer spots what they are, and the app records who borrowed/returned them in a notebook file.

## Features

✅ **Complete Features:**
- Register students with ID, name, course, and year level
- Log equipment borrowing and returns
- View student transaction history
- View all transaction history
- Manage inventory (add/update/delete equipment)
- Track total equipment count per student
- YOLO-based equipment detection (optional)

🔄 **In Development:**
- Support for borrowing multiple equipment types in one transaction
- Detailed transaction summaries
- Advanced filtering and reporting

## How to run (beginner steps)

1. Create a virtual environment (r/ELI5: a clean sandbox for Python):
   - Windows: `py -m venv .venv && .venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`

2. Install packages (r/ELI5: buy everything on the shopping list):
   ```bash
   pip install -r requirements.txt
   ```

3. Start the app (r/ELI5: turn on the tiny traffic cop and open the page):
   ```bash
   python app.py
   ```
   Then open http://127.0.0.1:5000 in your browser.

## Project layout

- `app.py` — Flask server with all routes and logic
- `templates/` — HTML pages (index, register, borrow_return, records, history, inventory)
- `static/` — CSS styling (style.css)
- `database.db` — SQLite database with students, equipment_log, and inventory tables
- `after_dsmtf.pt` — YOLO model weights for equipment detection
- `requirements.txt` — Python dependencies
- `TASKS.md` — Development task list with completed and in-progress items

## Database Schema

### students table
```
- student_id (TEXT, PRIMARY KEY)
- name (TEXT)
- course (TEXT)
- year_level (INTEGER)
- number_of_equipment (INTEGER) - tracks total equipment borrowed
```

### equipment_log table
```
- id (INTEGER, PRIMARY KEY)
- student_id (TEXT)
- equipment_name (TEXT)
- action (TEXT) - 'borrow' or 'return'
- timestamp (TEXT) - auto-generated
```

### inventory table
```
- id (INTEGER, PRIMARY KEY)
- name (TEXT, UNIQUE)
- quantity (INTEGER) - managed via admin panel only
```

## Recent Updates

### ✅ Inventory Independence (Task 1)
- Borrowing and returning equipment no longer automatically updates inventory
- Inventory is now managed exclusively through the admin Inventory Management page
- This allows for better control and separate tracking of physical vs. logged inventory

### ✅ Student Equipment Tracking (Task 3)
- Each student now has a `number_of_equipment` counter
- Automatically increments when borrowing
- Automatically decrements when returning
- Helps track how much equipment each student currently has

## Development Tasks

See **[TASKS.md](TASKS.md)** for a detailed list of:
- ✅ Completed features
- 🔄 In-progress features
- 📋 Planned features
- 🚀 Optional enhancements

Quick summary:
1. ✅ Stop Inventory Auto-Update - **COMPLETED**
2. 🔄 Multiple Equipment Types - **IN PROGRESS**
3. ✅ Student Equipment Tracking - **COMPLETED**
4. 📋 Testing & Validation - **PLANNED**
5. 🚀 Transaction Summary - **OPTIONAL**
6. 🚀 Admin Logs - **OPTIONAL**
7. 🚀 Error Messages & Validation - **OPTIONAL**

## Usage Guide

### Register a Student
1. Click "Register Student" from the home page
2. Enter student ID, name, course, and year level
3. Click "Register"

### Borrow Equipment
1. Click "Log Borrow / Return"
2. Enter student ID
3. Select "Borrow" from the action dropdown
4. Choose equipment and quantity
5. Click "Borrow" - the transaction is logged and student equipment count increases

### Return Equipment
1. Click "Log Borrow / Return"
2. Enter student ID
3. Select "Return" from the action dropdown
4. Choose equipment and quantity
5. Click "Return" - the transaction is logged and student equipment count decreases

### View Student Records
1. Click "Student Records"
2. Enter student ID
3. View all borrow/return transactions for that student

### Manage Inventory
1. Click "Manage Inventory"
2. Add new equipment with quantities
3. Update quantities manually
4. Delete equipment entries

## Notes

- **Inventory vs. Transactions:** Inventory quantities are independent of borrow/return logs. Use the Inventory Management page to reflect actual physical stock.
- **Equipment Tracking:** `number_of_equipment` tracks logical items with a student, not physical inventory.
- If you later split code (optional), create `src/` with helpers and update imports carefully.

## Electron Desktop App

This project can also be run as a desktop application using Electron. Files:
- `electron-main.js` — Electron main process
- `preload.js` — Electron preload script
- `package.json` — Node.js dependencies and scripts

To run as desktop app: `npm start`
