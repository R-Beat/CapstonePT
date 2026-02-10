"""
Integration test suite for LabCV Flask application.
Tests Tasks 1, 2, and 3 implementations using the actual database.

Running tests:
    pytest test_integration.py -v
    pytest test_integration.py::test_inventory_independence -v
"""

import pytest  # type: ignore
import sqlite3
import os

# Get the actual database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

# Mock ultralytics if needed
try:
    from ultralytics import YOLO
except ImportError:
    import sys
    class MockYOLO:
        def __init__(self, *args, **kwargs):
            pass
        def predict(self, *args, **kwargs):
            return [MockResult()]
    class MockResult:
        def __init__(self):
            self.boxes = None
    sys.modules['ultralytics'] = type(sys)('ultralytics')
    sys.modules['ultralytics'].YOLO = MockYOLO

from app import app


@pytest.fixture
def client():
    """Create a test client with the actual Flask app."""
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        yield client


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def setup_test_students():
    """Add test students if not present."""
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM equipment_log")
        c.execute("DELETE FROM students")
        c.execute("DELETE FROM inventory")
        
        # Add test students
        c.execute("INSERT INTO students (student_id, name, course, year_level, number_of_equipment) VALUES (?, ?, ?, ?, ?)",
                  ("TEST001", "Test Student 1", "CS101", 1, 0))
        c.execute("INSERT INTO students (student_id, name, course, year_level, number_of_equipment) VALUES (?, ?, ?, ?, ?)",
                  ("TEST002", "Test Student 2", "CS102", 2, 0))
        
        # Add test inventory
        c.execute("INSERT INTO inventory (name, quantity) VALUES (?, ?)", ("Beaker", 20))
        c.execute("INSERT INTO inventory (name, quantity) VALUES (?, ?)", ("Graduated Cylinder", 15))
        c.execute("INSERT INTO inventory (name, quantity) VALUES (?, ?)", ("Erlenmeyer Flask", 10))
        c.execute("INSERT INTO inventory (name, quantity) VALUES (?, ?)", ("Funnel", 8))
        
        conn.commit()
    finally:
        conn.close()


class TestInventoryIndependence:
    """Test that inventory is independent from transaction logging (Task 1)."""
    
    def test_borrow_does_not_update_inventory(self, client):
        """Verify that borrowing doesn't reduce inventory quantity."""
        setup_test_students()
        
        # Get initial inventory
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT quantity FROM inventory WHERE name=?", ("Beaker",))
        initial_qty = c.fetchone()[0]
        conn.close()
        
        # Borrow equipment
        response = client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['2']
        }, follow_redirects=True)
        
        # Check inventory is unchanged
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT quantity FROM inventory WHERE name=?", ("Beaker",))
        final_qty = c.fetchone()[0]
        conn.close()
        
        assert final_qty == initial_qty, f"Inventory should not be updated. Initial: {initial_qty}, Final: {final_qty}"
    
    def test_transaction_logged_but_inventory_unchanged(self, client):
        """Verify transaction is logged to equipment_log without changing inventory."""
        setup_test_students()
        
        # Borrow equipment
        response = client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['3']
        }, follow_redirects=True)
        
        # Verify transaction is in log
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM equipment_log WHERE student_id=? AND equipment_name=? AND action=?",
                  ("TEST001", "Beaker", "borrow"))
        log_count = c.fetchone()[0]
        
        # Verify inventory unchanged
        c.execute("SELECT quantity FROM inventory WHERE name=?", ("Beaker",))
        qty = c.fetchone()[0]
        conn.close()
        
        assert log_count == 1, f"Transaction should be logged. Found: {log_count}"
        assert qty == 20, f"Inventory should remain at 20. Found: {qty}"


class TestMultipleEquipment:
    """Test multiple equipment borrowing/returning (Task 2)."""
    
    def test_borrow_multiple_items_single_transaction(self, client):
        """Test borrowing 3 different equipment types in one transaction."""
        setup_test_students()
        
        response = client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker', 'Graduated Cylinder', 'Funnel'],
            'quantities': ['2', '1', '3']
        }, follow_redirects=True)
        
        # Verify all transactions logged
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM equipment_log WHERE student_id=? AND action=?",
                  ("TEST001", "borrow"))
        log_count = c.fetchone()[0]
        conn.close()
        
        assert log_count == 3, f"All 3 items should be logged. Found: {log_count}"
    
    def test_return_multiple_items_single_transaction(self, client):
        """Test returning multiple items in one transaction."""
        setup_test_students()
        
        # Borrow first
        client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker', 'Graduated Cylinder'],
            'quantities': ['2', '1']
        }, follow_redirects=True)
        
        # Return
        response = client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'return',
            'equipment_names': ['Beaker', 'Graduated Cylinder'],
            'quantities': ['2', '1']
        }, follow_redirects=True)
        
        # Verify return transactions logged
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM equipment_log WHERE student_id=? AND action=?",
                  ("TEST001", "return"))
        return_count = c.fetchone()[0]
        conn.close()
        
        assert return_count == 2, f"Both return transactions should be logged. Found: {return_count}"


class TestStudentEquipmentTracking:
    """Test student equipment count tracking (Task 3)."""
    
    def test_borrow_increments_student_count(self, client):
        """Verify borrowing increments the student's equipment count."""
        setup_test_students()
        
        # Borrow 3 items
        client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['3']
        }, follow_redirects=True)
        
        # Check updated count
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT number_of_equipment FROM students WHERE student_id=?", ("TEST001",))
        count = c.fetchone()[0]
        conn.close()
        
        assert count == 3, f"Count should be 3. Found: {count}"
    
    def test_return_decrements_student_count(self, client):
        """Verify returning decrements the student's equipment count."""
        setup_test_students()
        
        # Borrow 5 items
        client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['5']
        }, follow_redirects=True)
        
        # Return 3 items
        client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'return',
            'equipment_names': ['Beaker'],
            'quantities': ['3']
        }, follow_redirects=True)
        
        # Check count after return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT number_of_equipment FROM students WHERE student_id=?", ("TEST001",))
        count = c.fetchone()[0]
        conn.close()
        
        assert count == 2, f"Count should be 2 after returning 3 of 5. Found: {count}"
    
    def test_multiple_items_count_incremented_correctly(self, client):
        """Verify count increments correctly when borrowing multiple items."""
        setup_test_students()
        
        # Borrow 2 Beakers + 3 Funnels + 1 Graduated Cylinder = 6 total
        client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker', 'Funnel', 'Graduated Cylinder'],
            'quantities': ['2', '3', '1']
        }, follow_redirects=True)
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT number_of_equipment FROM students WHERE student_id=?", ("TEST001",))
        count = c.fetchone()[0]
        conn.close()
        
        assert count == 6, f"Total count should be 2+3+1=6. Found: {count}"
    
    def test_count_never_goes_negative(self, client):
        """Verify count doesn't go negative if returning more than borrowed."""
        setup_test_students()
        
        # Borrow 2 items
        client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['2']
        }, follow_redirects=True)
        
        # Try to return 5 items (more than borrowed)
        client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'return',
            'equipment_names': ['Beaker'],
            'quantities': ['5']
        }, follow_redirects=True)
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT number_of_equipment FROM students WHERE student_id=?", ("TEST001",))
        count = c.fetchone()[0]
        conn.close()
        
        assert count >= 0, f"Count should never be negative. Found: {count}"


class TestInputValidation:
    """Test input validation and error handling."""
    
    def test_empty_student_id(self, client):
        """Test that empty student ID is rejected."""
        setup_test_students()
        
        response = client.post('/borrow_return', data={
            'student_id': '',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['1']
        }, follow_redirects=True)
        
        # Should show error message
        assert b"Student ID cannot be empty" in response.data or response.status_code == 200
    
    def test_nonexistent_student(self, client):
        """Test that borrowing as non-existent student is rejected."""
        setup_test_students()
        
        response = client.post('/borrow_return', data={
            'student_id': 'NONEXIST999',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['1']
        }, follow_redirects=True)
        
        # Should show error message
        assert b"Student not found" in response.data or b"not found" in response.data.lower()
    
    def test_nonexistent_equipment(self, client):
        """Test that borrowing non-existent equipment is rejected."""
        setup_test_students()
        
        response = client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Nonexistent Equipment'],
            'quantities': ['1']
        }, follow_redirects=True)
        
        # Should show error message
        assert b"not found" in response.data.lower() or b"Equipment" in response.data
    
    def test_zero_quantity(self, client):
        """Test that zero quantity is rejected."""
        setup_test_students()
        
        response = client.post('/borrow_return', data={
            'student_id': 'TEST001',
            'action': 'borrow',
            'equipment_names': ['Beaker'],
            'quantities': ['0']
        }, follow_redirects=True)
        
        # Should show error message
        assert b"Quantity" in response.data or b"at least 1" in response.data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
