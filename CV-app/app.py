import os
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from ultralytics import YOLO
import cv2
import numpy as np
import base64
import datetime

# Load YOLO model once - use relative path
model_path = os.path.join(os.path.dirname(__file__), "capstone.pt")
model = YOLO(model_path)

app = Flask(__name__)
app.secret_key = 'secret'

# Map YOLO class names to actual inventory names
CLASS_TO_EQUIPMENT = {
    "graduated_cylinder": "Graduated Cylinder",
    "beaker": "Beaker",
    'compass': 'Compass',
    'digital_balance': 'Digital Balance',
    'erlenmeyer_flask': 'Erlenmeyer Flask',
    'funnel': 'Funnel',
    'horseshoe_magnet': 'Horseshoe Magnet',
    'test_tube_rack': 'Test Tube Rack',
    'triple_beam_balance': 'Triple Beam Balance',
    'tripod': 'Tripod',
}

# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            course TEXT,
            year_level INTEGER,
            student_type TEXT DEFAULT 'college'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS equipment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            action TEXT CHECK(action IN ('borrow', 'return')),
            quantity INTEGER DEFAULT 1,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            total_quantity INTEGER DEFAULT 0,
            quantity INTEGER DEFAULT 0
        )
    ''')
    
    # Add quantity column if it doesn't exist
    try:
        c.execute("ALTER TABLE equipment_log ADD COLUMN quantity INTEGER DEFAULT 1")
    except:
        pass
    
    # Add student_type column if it doesn't exist
    try:
        c.execute("ALTER TABLE students ADD COLUMN student_type TEXT DEFAULT 'college'")
    except:
        pass
    
    # Add total_quantity column if it doesn't exist (migrate existing data)
    try:
        c.execute("ALTER TABLE inventory ADD COLUMN total_quantity INTEGER DEFAULT 0")
        # For existing items, set total_quantity equal to current quantity
        c.execute("UPDATE inventory SET total_quantity = quantity WHERE total_quantity = 0")
    except:
        pass
    
    conn.commit()
    conn.close()

# ---------- Helper Functions ----------
def get_inventory():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, name, total_quantity, quantity FROM inventory ORDER BY name ASC")
    items = c.fetchall()
    conn.close()
    return items

def get_inventory_dict():
    """Return dict: equipment_name -> available quantity"""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT name, quantity FROM inventory")
    items = c.fetchall()
    conn.close()
    return {name: qty for name, qty in items}

def get_pending_equipment(student_id):
    """Return list of equipment student borrowed but hasn't fully returned."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        SELECT equipment_name, SUM(CASE WHEN action='borrow' THEN quantity ELSE -quantity END) as pending
        FROM equipment_log
        WHERE student_id=?
        GROUP BY equipment_name
        HAVING pending > 0
        ORDER BY equipment_name ASC
    """, (student_id,))
    pending = c.fetchall()
    conn.close()
    return pending

# ---------- Routes ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        sid = request.form['student_id']
        name = request.form['name']
        course = request.form['course']
        year = request.form['year_level']
        student_type = request.form.get('student_type', 'college')
        try:
            if year:
                year = int(year)
                
                # Validate year level based on student type
                if student_type == 'ibed':
                    if year < 1 or year > 12:
                        flash("IBED student grade level must be between 1 and 12.")
                        return redirect(url_for('register'))
                elif student_type == 'college':
                    if year < 1:
                        flash("College student year level must be at least 1.")
                        return redirect(url_for('register'))
            else:
                year = None
        except ValueError:
            flash("Year level must be a valid number.")
            return redirect(url_for('register'))
        

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO students VALUES (?, ?, ?, ?, ?)", (sid, name, course, year, student_type))
        conn.commit()
        conn.close()
        flash("Student registered successfully!")
        return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/pending_equipment', methods=['GET', 'POST'])
def pending_equipment():
    """Display pending equipment for all students or a specific student."""
    pending_data = []
    search_student_id = request.form.get('student_id', '').strip() if request.method == 'POST' else ''
    
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    if search_student_id:
        # Get pending equipment for specific student
        c.execute("SELECT name, course, year_level FROM students WHERE student_id=?", (search_student_id,))
        student = c.fetchone()
        if student:
            pending_items = get_pending_equipment(search_student_id)
            if pending_items:
                pending_data.append({
                    'student_id': search_student_id,
                    'student_name': student[0],
                    'course': student[1],
                    'year_level': student[2],
                    'pending_items': pending_items,
                    'total_pending': sum(qty for _, qty in pending_items)
                })
        else:
            flash("Student not found.")
    else:
        # Get pending equipment for all students
        c.execute("SELECT student_id FROM students ORDER BY student_id ASC")
        students = c.fetchall()
        
        for (student_id,) in students:
            pending_items = get_pending_equipment(student_id)
            if pending_items:
                c.execute("SELECT name, course, year_level FROM students WHERE student_id=?", (student_id,))
                student = c.fetchone()
                if student:
                    pending_data.append({
                        'student_id': student_id,
                        'student_name': student[0],
                        'course': student[1],
                        'year_level': student[2],
                        'pending_items': pending_items,
                        'total_pending': sum(qty for _, qty in pending_items)
                    })
    
    # Get all students for dropdown
    c.execute("SELECT student_id, name FROM students ORDER BY student_id ASC")
    all_students = c.fetchall()
    conn.close()
    
    return render_template('pending_equipment.html',
                         pending_data=pending_data,
                         all_students=all_students,
                         search_student_id=search_student_id)

@app.route('/borrow_return', methods=['GET', 'POST'])
def borrow_return():
    inventory = get_inventory()
    inventory_dict = get_inventory_dict()
    detected_items = request.args.get('detected')
    if detected_items:
        detected_items = detected_items.split(',')
    else:
        detected_items = []

    # Get student_id from form or request (for displaying pending items)
    student_id = request.form.get('student_id', '').strip() or request.args.get('student_id', '').strip()
    pending_equipment = get_pending_equipment(student_id) if student_id else []

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        action = request.form.get('action', '')
        
        # Handle both detected and manually added equipment
        equipment_names = request.form.getlist('equipment_names')
        quantities = request.form.getlist('quantities')
        
        # Filter out empty values
        equipment_names = [e for e in equipment_names if e.strip()]
        quantities = [q for q in quantities if q.strip()]
        
        # Validate inputs
        if not student_id:
            flash("Student ID cannot be empty.")
            return redirect(url_for('borrow_return'))
        
        if not action:
            flash("Please select an action (Borrow or Return).")
            return redirect(url_for('borrow_return'))
        
        if not equipment_names or len(equipment_names) == 0:
            flash("Please select at least one equipment item.")
            return redirect(url_for('borrow_return'))
        
        if len(equipment_names) != len(quantities):
            flash("Equipment and quantity mismatch.")
            return redirect(url_for('borrow_return'))
        
        # Validate quantities
        try:
            quantities = [int(q) for q in quantities]
            for q in quantities:
                if q <= 0:
                    flash("Quantity must be at least 1.")
                    return redirect(url_for('borrow_return'))
        except ValueError:
            flash("Invalid quantity entered.")
            return redirect(url_for('borrow_return'))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        
        # Verify student exists
        c.execute("SELECT student_id FROM students WHERE student_id=?", (student_id,))
        student_row = c.fetchone()
        if not student_row:
            flash("Student not found. Please register first.")
            conn.close()
            return redirect(url_for('borrow_return'))
        
        # Verify all equipment exists
        for equipment_name in equipment_names:
            c.execute("SELECT quantity FROM inventory WHERE name=?", (equipment_name,))
            if not c.fetchone():
                flash(f"Equipment '{equipment_name}' not found in inventory.")
                conn.close()
                return redirect(url_for('borrow_return'))
        
        # Process all equipment items in one transaction
        success = True
        try:
            for equipment_name, quantity in zip(equipment_names, quantities):
                # Check inventory exists and quantity available
                c.execute("SELECT quantity FROM inventory WHERE name=?", (equipment_name,))
                row = c.fetchone()
                if not row:
                    flash(f"Equipment '{equipment_name}' not found in inventory.")
                    success = False
                    break
                inv_qty = row[0] or 0
                
                if action == 'borrow' and inv_qty < quantity:
                    flash(f"Not enough '{equipment_name}' in inventory. Available: {inv_qty}")
                    success = False
                    break
                
                # Validate return quantity doesn't exceed what student borrowed
                if action == 'return':
                    c.execute(
                        "SELECT COALESCE(SUM(CASE WHEN action='borrow' THEN quantity ELSE -quantity END), 0) FROM equipment_log WHERE student_id=? AND equipment_name=?",
                        (student_id, equipment_name)
                    )
                    net_borrowed = c.fetchone()[0] or 0
                    if quantity > net_borrowed:
                        flash(f"Student cannot return {quantity} '{equipment_name}'. Only {net_borrowed} borrowed.")
                        success = False
                        break

                # Update inventory counts
                new_qty = inv_qty - quantity if action == 'borrow' else inv_qty + quantity
                c.execute("UPDATE inventory SET quantity=? WHERE name=?", (new_qty, equipment_name))

                # Log the action with quantity
                c.execute(
                    "INSERT INTO equipment_log (student_id, equipment_name, action, quantity) VALUES (?, ?, ?, ?)",
                    (student_id, equipment_name, action, quantity)
                )

            if not success:
                conn.rollback()
                conn.close()
                return redirect(url_for('borrow_return'))

            conn.commit()
            conn.close()
            
            # Redirect to summary page with transaction details
            return redirect(url_for('transaction_summary', 
                student_id=student_id,
                action=action,
                items=','.join(equipment_names),
                quantities=','.join(map(str, quantities)),
                total=sum(quantities)
            ))
        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f"Error processing transaction: {e}")
            return redirect(url_for('borrow_return'))

    return render_template("borrow_return.html",
                           inventory=inventory,
                           inventory_dict=inventory_dict,
                           detected_items=detected_items,
                           pending_equipment=pending_equipment,
                           current_student_id=student_id)

@app.route('/process_capture', methods=['POST'])
def process_capture():
    image_data = request.form['image_data'].split(",")[1]
    nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    results = model(frame)
    detected_classes = set()
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            detected_classes.add(model.names[cls_id])

    # Map class names to inventory names
    detected_equipment = []
    inventory_dict = get_inventory_dict()
    for cls in detected_classes:
        if cls in CLASS_TO_EQUIPMENT and CLASS_TO_EQUIPMENT[cls] in inventory_dict:
            detected_equipment.append(CLASS_TO_EQUIPMENT[cls])

    if detected_equipment:
        flash("Detected: " + ", ".join(detected_equipment))
        return redirect(url_for("borrow_return", detected=",".join(detected_equipment)))
    else:
        flash("No valid equipment detected in inventory.")
        return redirect(url_for("borrow_return"))

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form['name'].strip()
            total_quantity = int(request.form['total_quantity'])
            if name:
                try:
                    c.execute("INSERT INTO inventory (name, total_quantity, quantity) VALUES (?, ?, ?)", (name, total_quantity, total_quantity))
                    conn.commit()
                    flash("Equipment added successfully.")
                except sqlite3.IntegrityError:
                    flash("Equipment already exists.")
        elif action == 'update_total':
            item_id = request.form['item_id']
            total_quantity = int(request.form['total_quantity'])
            # Get current borrowed quantity
            c.execute("SELECT total_quantity, quantity FROM inventory WHERE id=?", (item_id,))
            row = c.fetchone()
            if row:
                old_total = row[0]
                available = row[1]
                # Calculate new available based on difference in total
                difference = total_quantity - old_total
                new_available = available + difference
                c.execute("UPDATE inventory SET total_quantity=?, quantity=? WHERE id=?", (total_quantity, new_available, item_id))
                conn.commit()
                flash("Total quantity updated.")
        elif action == 'delete':
            item_id = request.form['item_id']
            c.execute("DELETE FROM inventory WHERE id=?", (item_id,))
            conn.commit()
            flash("Equipment deleted.")
        return redirect(url_for('inventory'))

    c.execute("SELECT id, name, total_quantity, quantity FROM inventory ORDER BY name ASC")
    items = c.fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

@app.route('/records', methods=['GET', 'POST'])
def records():
    logs = []
    if request.method == 'POST':
        student_id = request.form['student_id']
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT equipment_name, action, quantity, timestamp FROM equipment_log WHERE student_id=? ORDER BY timestamp DESC", (student_id,))
        logs = c.fetchall()
        conn.close()
    return render_template('records.html', logs=logs)


@app.route('/transaction_summary')
def transaction_summary():
    """Display transaction summary after successful borrow/return."""
    student_id = request.args.get('student_id', '')
    action = request.args.get('action', '')
    items = request.args.get('items', '').split(',') if request.args.get('items') else []
    quantities = request.args.get('quantities', '').split(',') if request.args.get('quantities') else []
    total = int(request.args.get('total', 0))
    
    # Get student details
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT name, course, year_level FROM students WHERE student_id=?", (student_id,))
    student_data = c.fetchone()
    conn.close()
    
    if not student_data:
        flash("Student not found.")
        return redirect(url_for('borrow_return'))
    
    student_name, course, year_level = student_data
    
    # Prepare transaction items list
    transaction_items = []
    for item, qty in zip(items, quantities):
        if item and qty:
            transaction_items.append({
                'name': item,
                'quantity': int(qty)
            })
    
    # Prepare context data
    context = {
        'student_id': student_id,
        'student_name': student_name,
        'course': course,
        'year_level': year_level,
        'action': action,
        'total_items': total,
        'items': transaction_items,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return render_template('transaction_summary.html', **context)


@app.route('/admin_logs', methods=['GET', 'POST'])
def admin_logs():
    """Display transaction logs with filtering and sorting options."""
    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        
        filters = {
            'student_id': request.args.get('student_id', '').strip(),
            'equipment': request.args.get('equipment', '').strip(),
            'action': request.args.get('action', ''),
            'sort': request.args.get('sort', 'timestamp_desc')
        }
        
        # Build query with filters
        query = """
            SELECT e.id, e.student_id, s.name, e.equipment_name, e.action, e.timestamp
            FROM equipment_log e
            LEFT JOIN students s ON e.student_id = s.student_id
            WHERE 1=1
        """
        params = []
        
        if filters['student_id']:
            query += " AND e.student_id = ?"
            params.append(filters['student_id'])
        
        if filters['equipment']:
            query += " AND e.equipment_name LIKE ?"
            params.append(f"%{filters['equipment']}%")
        
        if filters['action']:
            query += " AND e.action = ?"
            params.append(filters['action'])
        
        # Apply sorting
        if filters['sort'] == 'timestamp_asc':
            query += " ORDER BY e.timestamp ASC"
        elif filters['sort'] == 'student_id':
            query += " ORDER BY e.student_id ASC"
        elif filters['sort'] == 'action':
            query += " ORDER BY e.action ASC, e.timestamp DESC"
        else:
            query += " ORDER BY e.timestamp DESC"
        
        c.execute(query, params)
        logs = c.fetchall()
        
        # Get unique values for filter dropdowns
        c.execute("SELECT DISTINCT student_id FROM students ORDER BY student_id")
        all_students = [s[0] for s in c.fetchall()]
        
        c.execute("SELECT DISTINCT equipment_name FROM equipment_log ORDER BY equipment_name")
        all_equipment = [eq[0] for eq in c.fetchall()]
        
        conn.close()
        
        return render_template('admin_logs.html', 
                             logs=logs,
                             filters=filters,
                             students=all_students,
                             equipment=all_equipment)
    
    except Exception as e:
        print(f"Admin logs error: {str(e)}")
        flash(f"Error loading admin logs: {str(e)}")
        return redirect(url_for('home'))

@app.route('/history')
def history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT student_id, equipment_name, action, quantity, timestamp FROM equipment_log ORDER BY timestamp DESC")
    logs = c.fetchall()
    conn.close()
    return render_template('history.html', logs=logs)

@app.route('/registered_students')
def registered_students():
    """Display all registered students."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    # Get all students with their borrowing statistics
    c.execute("""
        SELECT 
            s.student_id, 
            s.name, 
            s.course, 
            s.year_level,
            s.student_type,
            COUNT(CASE WHEN el.action='borrow' THEN 1 END) as total_borrows,
            COUNT(CASE WHEN el.action='return' THEN 1 END) as total_returns,
            COALESCE(SUM(CASE WHEN el.action='borrow' THEN el.quantity ELSE -el.quantity END), 0) as currently_holding
        FROM students s
        LEFT JOIN equipment_log el ON s.student_id = el.student_id
        GROUP BY s.student_id, s.name, s.course, s.year_level, s.student_type
        ORDER BY s.student_id ASC
    """)
    students = c.fetchall()
    
    # Get total stats
    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]
    
    conn.close()
    
    return render_template('registered_students.html', 
                         students=students,
                         total_students=total_students)

@app.route('/edit_student/<student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student information."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    if request.method == 'POST':
        new_student_id = request.form['student_id'].strip()
        name = request.form['name'].strip()
        course = request.form['course'].strip()
        year_level = request.form['year_level'].strip()
        student_type = request.form.get('student_type', 'college')
        
        # Validate inputs
        if not new_student_id:
            flash("Student ID cannot be empty.")
            return redirect(url_for('edit_student', student_id=student_id))
        
        if not name:
            flash("Student name cannot be empty.")
            return redirect(url_for('edit_student', student_id=student_id))
        
        try:
            if year_level:
                year_level = int(year_level)
                
                # Validate year level based on student type
                if student_type == 'ibed':
                    if year_level < 1 or year_level > 12:
                        flash("IBED student grade level must be between 1 and 12.")
                        return redirect(url_for('edit_student', student_id=student_id))
                elif student_type == 'college':
                    if year_level < 1:
                        flash("College student year level must be at least 1.")
                        return redirect(url_for('edit_student', student_id=student_id))
            else:
                year_level = None
        except ValueError:
            flash("Year level must be a valid number.")
            return redirect(url_for('edit_student', student_id=student_id))
        
        # Check if new student_id already exists (and is different from old one)
        if new_student_id != student_id:
            c.execute("SELECT student_id FROM students WHERE student_id=?", (new_student_id,))
            if c.fetchone():
                flash("This Student ID already exists. Please use a unique ID.")
                conn.close()
                return redirect(url_for('edit_student', student_id=student_id))
        
        try:
            # If student_id changed, update references in equipment_log
            if new_student_id != student_id:
                c.execute("UPDATE equipment_log SET student_id=? WHERE student_id=?", (new_student_id, student_id))
            
            # Update student information
            c.execute("""
                UPDATE students 
                SET student_id=?, name=?, course=?, year_level=?, student_type=? 
                WHERE student_id=?
            """, (new_student_id, name, course if course else None, year_level, student_type, student_id))
            conn.commit()
            conn.close()
            
            flash("Student information updated successfully!")
            return redirect(url_for('registered_students'))
        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f"Error updating student: {str(e)}")
            return redirect(url_for('edit_student', student_id=student_id))
    
    # GET request - retrieve student info
    c.execute("SELECT student_id, name, course, year_level, student_type FROM students WHERE student_id=?", (student_id,))
    student = c.fetchone()
    conn.close()
    
    if not student:
        flash("Student not found.")
        return redirect(url_for('registered_students'))
    
    return render_template('edit_student.html', student=student)

# ---------- Run Server ----------
if __name__ == '__main__':
    init_db()
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host=host, port=port, debug=debug, use_reloader=False)
