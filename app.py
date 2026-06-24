from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import os
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
app.secret_key = 'college_library_secret_2024'

# ──────────────────────────────────────────────
# Database Setup
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'library.db')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin@lib123'

logging.basicConfig(level=logging.DEBUG)

BOOK_CATEGORIES = [
    'Computer Science', 'Mathematics', 'Physics', 'Chemistry',
    'Biology', 'Electronics', 'Mechanical Engineering', 'Civil Engineering',
    'Literature', 'History', 'Economics', 'Management', 'Law', 'Other'
]

DEPARTMENTS = [
    'Computer Science & Engineering', 'Information Technology',
    'Electronics & Communication', 'Mechanical Engineering',
    'Civil Engineering', 'Electrical Engineering',
    'Physics', 'Chemistry', 'Mathematics', 'Management', 'Other'
]

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Other',
                quantity INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                roll_number TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                join_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS issued_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                member_id TEXT NOT NULL,
                issued_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                return_date TEXT,
                number_of_days INTEGER,
                fine INTEGER DEFAULT 0,
                FOREIGN KEY (book_id) REFERENCES books(id),
                FOREIGN KEY (member_id) REFERENCES members(id)
            );
        ''')
        db.commit()
        _seed_data(db)

def _seed_data(db):
    """Insert sample data if tables are empty."""
    if db.execute('SELECT COUNT(*) FROM books').fetchone()[0] > 0:
        return

    books_data = [
        ('B001', 'Introduction to Algorithms', 'Cormen et al.', 'Computer Science', 5),
        ('B002', 'Computer Networks', 'Andrew Tanenbaum', 'Computer Science', 3),
        ('B003', 'Database System Concepts', 'Silberschatz', 'Computer Science', 4),
        ('B004', 'Engineering Mathematics', 'B.S. Grewal', 'Mathematics', 6),
        ('B005', 'Engineering Physics', 'S.K. Gupta', 'Physics', 3),
        ('B006', 'Signals and Systems', 'Oppenheim', 'Electronics', 2),
        ('B007', 'Strength of Materials', 'R.K. Bansal', 'Mechanical Engineering', 4),
        ('B008', 'Fluid Mechanics', 'Frank White', 'Mechanical Engineering', 2),
        ('B009', 'Organic Chemistry', 'Morrison Boyd', 'Chemistry', 3),
        ('B010', 'Data Structures', 'Mark Allen Weiss', 'Computer Science', 5),
        ('B011', 'Operating Systems', 'Galvin', 'Computer Science', 3),
        ('B012', 'Discrete Mathematics', 'Kenneth Rosen', 'Mathematics', 4),
        ('B013', 'Principles of Economics', 'N. G. Mankiw', 'Economics', 2),
        ('B014', 'Business Management', 'P. C. Tripathi', 'Management', 3),
        ('B015', 'Electrical Technology', 'B.L. Theraja', 'Electronics', 2),
    ]
    db.executemany(
        'INSERT INTO books (id, title, author, category, quantity) VALUES (?,?,?,?,?)',
        books_data
    )

    members_data = [
        ('M001', 'Alice Smith', 'CS2021001', 'Computer Science & Engineering', 'alice@college.edu', '9876543210', '123 Main St', '2021-07-15'),
        ('M002', 'Bob Johnson', 'IT2021002', 'Information Technology', 'bob@college.edu', '9876543211', '234 Elm St', '2021-07-15'),
        ('M003', 'Charlie Brown', 'ME2022003', 'Mechanical Engineering', 'charlie@college.edu', '9876543212', '345 Oak St', '2022-07-20'),
        ('M004', 'David Wilson', 'CE2022004', 'Civil Engineering', 'david@college.edu', '9876543213', '456 Pine St', '2022-07-20'),
        ('M005', 'Eva Green', 'CS2023005', 'Computer Science & Engineering', 'eva@college.edu', '9876543214', '567 Maple St', '2023-07-18'),
    ]
    db.executemany(
        'INSERT INTO members (id, name, roll_number, department, email, phone, address, join_date) VALUES (?,?,?,?,?,?,?,?)',
        members_data
    )
    db.commit()

def generate_id(prefix, table, id_col='id'):
    db = get_db()
    count = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    return f'{prefix}{count + 1:03d}'

# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access the library system.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('Welcome back, Librarian!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────
@app.route('/')
@login_required
def dashboard():
    db = get_db()
    total_books = db.execute('SELECT SUM(quantity) FROM books').fetchone()[0] or 0
    total_titles = db.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    total_members = db.execute('SELECT COUNT(*) FROM members').fetchone()[0]
    active_issues = db.execute('SELECT COUNT(*) FROM issued_books WHERE return_date IS NULL').fetchone()[0]
    overdue_count = db.execute(
        "SELECT COUNT(*) FROM issued_books WHERE return_date IS NULL AND due_date < ?",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),)
    ).fetchone()[0]
    total_fines = db.execute('SELECT SUM(fine) FROM issued_books').fetchone()[0] or 0
    recent_issues = db.execute('''
        SELECT ib.id, b.title, m.name, m.roll_number, ib.issued_date, ib.due_date
        FROM issued_books ib
        JOIN books b ON ib.book_id = b.id
        JOIN members m ON ib.member_id = m.id
        WHERE ib.return_date IS NULL
        ORDER BY ib.issued_date DESC LIMIT 5
    ''').fetchall()
    return render_template('dashboard.html',
        total_books=total_books, total_titles=total_titles,
        total_members=total_members, active_issues=active_issues,
        overdue_count=overdue_count, total_fines=total_fines,
        recent_issues=recent_issues, now=datetime.now()
    )

# ──────────────────────────────────────────────
# Books
# ──────────────────────────────────────────────
@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        category = request.form['category']
        quantity = int(request.form['quantity'])
        db = get_db()
        existing = db.execute(
            'SELECT * FROM books WHERE title=? AND author=?', (title, author)
        ).fetchone()
        if existing:
            db.execute('UPDATE books SET quantity = quantity + ? WHERE id = ?', (quantity, existing['id']))
            db.commit()
            flash(f'Updated quantity for "{title}". Added {quantity} more copies.', 'success')
        else:
            book_id = generate_id('B', 'books')
            db.execute(
                'INSERT INTO books (id, title, author, category, quantity) VALUES (?,?,?,?,?)',
                (book_id, title, author, category, quantity)
            )
            db.commit()
            flash(f'Book "{title}" added successfully!', 'success')
        return redirect(url_for('view_books'))
    return render_template('add_book.html', categories=BOOK_CATEGORIES)

@app.route('/view_books')
@login_required
def view_books():
    db = get_db()
    query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()
    sql = 'SELECT * FROM books WHERE 1=1'
    params = []
    if query:
        sql += ' AND (title LIKE ? OR author LIKE ? OR id LIKE ?)'
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
    if category_filter:
        sql += ' AND category = ?'
        params.append(category_filter)
    sql += ' ORDER BY title'
    books = db.execute(sql, params).fetchall()
    return render_template('view_books.html', books=books, categories=BOOK_CATEGORIES,
                           query=query, category_filter=category_filter)

@app.route('/edit_book/<book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('view_books'))
    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        category = request.form['category']
        quantity = int(request.form['quantity'])
        db.execute(
            'UPDATE books SET title=?, author=?, category=?, quantity=? WHERE id=?',
            (title, author, category, quantity, book_id)
        )
        db.commit()
        flash(f'Book "{title}" updated successfully!', 'success')
        return redirect(url_for('view_books'))
    return render_template('edit_book.html', book=book, categories=BOOK_CATEGORIES)

@app.route('/delete_book/<book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    db = get_db()
    # Check if book is currently issued
    active = db.execute(
        'SELECT COUNT(*) FROM issued_books WHERE book_id=? AND return_date IS NULL', (book_id,)
    ).fetchone()[0]
    if active > 0:
        flash('Cannot delete: this book is currently issued to a member.', 'danger')
        return redirect(url_for('view_books'))
    book = db.execute('SELECT title FROM books WHERE id=?', (book_id,)).fetchone()
    db.execute('DELETE FROM books WHERE id=?', (book_id,))
    db.commit()
    flash(f'Book "{book["title"]}" deleted.', 'success')
    return redirect(url_for('view_books'))

# ──────────────────────────────────────────────
# Members
# ──────────────────────────────────────────────
@app.route('/add_member', methods=['GET', 'POST'])
@login_required
def add_member():
    if request.method == 'POST':
        name = request.form['name'].strip()
        roll_number = request.form['roll_number'].strip().upper()
        department = request.form['department']
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        db = get_db()
        existing = db.execute('SELECT id FROM members WHERE roll_number=?', (roll_number,)).fetchone()
        if existing:
            flash(f'A member with roll number {roll_number} already exists.', 'danger')
            return render_template('add_member.html', departments=DEPARTMENTS)
        member_id = generate_id('M', 'members')
        join_date = datetime.now().strftime('%Y-%m-%d')
        db.execute(
            'INSERT INTO members (id, name, roll_number, department, email, phone, address, join_date) VALUES (?,?,?,?,?,?,?,?)',
            (member_id, name, roll_number, department, email, phone, address, join_date)
        )
        db.commit()
        flash(f'Member "{name}" (Roll: {roll_number}) registered successfully!', 'success')
        return redirect(url_for('view_members'))
    return render_template('add_member.html', departments=DEPARTMENTS)

@app.route('/view_members')
@login_required
def view_members():
    db = get_db()
    query = request.args.get('q', '').strip()
    dept_filter = request.args.get('department', '').strip()
    sql = 'SELECT * FROM members WHERE 1=1'
    params = []
    if query:
        sql += ' AND (name LIKE ? OR roll_number LIKE ? OR email LIKE ?)'
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
    if dept_filter:
        sql += ' AND department = ?'
        params.append(dept_filter)
    sql += ' ORDER BY name'
    members = db.execute(sql, params).fetchall()
    # Get active issue count per member
    issue_counts = {
        row['member_id']: row['cnt']
        for row in db.execute(
            'SELECT member_id, COUNT(*) as cnt FROM issued_books WHERE return_date IS NULL GROUP BY member_id'
        ).fetchall()
    }
    return render_template('view_members.html', members=members, departments=DEPARTMENTS,
                           query=query, dept_filter=dept_filter, issue_counts=issue_counts)

@app.route('/edit_member/<member_id>', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    db = get_db()
    member = db.execute('SELECT * FROM members WHERE id=?', (member_id,)).fetchone()
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('view_members'))
    if request.method == 'POST':
        name = request.form['name'].strip()
        roll_number = request.form['roll_number'].strip().upper()
        department = request.form['department']
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        # Check for roll number conflict with other members
        conflict = db.execute(
            'SELECT id FROM members WHERE roll_number=? AND id!=?', (roll_number, member_id)
        ).fetchone()
        if conflict:
            flash(f'Roll number {roll_number} is already taken by another member.', 'danger')
            return render_template('edit_member.html', member=member, departments=DEPARTMENTS)
        db.execute(
            'UPDATE members SET name=?, roll_number=?, department=?, email=?, phone=?, address=? WHERE id=?',
            (name, roll_number, department, email, phone, address, member_id)
        )
        db.commit()
        flash(f'Member "{name}" updated successfully!', 'success')
        return redirect(url_for('view_members'))
    return render_template('edit_member.html', member=member, departments=DEPARTMENTS)

@app.route('/delete_member/<member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    db = get_db()
    active = db.execute(
        'SELECT COUNT(*) FROM issued_books WHERE member_id=? AND return_date IS NULL', (member_id,)
    ).fetchone()[0]
    if active > 0:
        flash('Cannot delete: member currently has books issued.', 'danger')
        return redirect(url_for('view_members'))
    member = db.execute('SELECT name FROM members WHERE id=?', (member_id,)).fetchone()
    db.execute('DELETE FROM members WHERE id=?', (member_id,))
    db.commit()
    flash(f'Member "{member["name"]}" deleted.', 'success')
    return redirect(url_for('view_members'))

# ──────────────────────────────────────────────
# Issue / Return
# ──────────────────────────────────────────────
@app.route('/issue_book', methods=['GET', 'POST'])
@login_required
def issue_book():
    db = get_db()
    if request.method == 'POST':
        book_id = request.form['book_id']
        member_id = request.form['member_id']
        issue_date_str = request.form['issue_date'] + ' ' + request.form['issue_time']

        book = db.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
        member = db.execute('SELECT * FROM members WHERE id=?', (member_id,)).fetchone()

        if not book or not member:
            flash('Invalid book or member selected.', 'danger')
        elif book['quantity'] <= 0:
            flash(f'"{book["title"]}" is currently out of stock.', 'danger')
        else:
            # Check borrow limit (max 3 books at a time)
            active_count = db.execute(
                'SELECT COUNT(*) FROM issued_books WHERE member_id=? AND return_date IS NULL', (member_id,)
            ).fetchone()[0]
            if active_count >= 3:
                flash(f'{member["name"]} already has 3 books issued. Return a book first.', 'danger')
            else:
                # Check if this member already has THIS book
                already = db.execute(
                    'SELECT id FROM issued_books WHERE book_id=? AND member_id=? AND return_date IS NULL',
                    (book_id, member_id)
                ).fetchone()
                if already:
                    flash(f'{member["name"]} already has "{book["title"]}" issued.', 'danger')
                else:
                    issued_date = datetime.strptime(issue_date_str, '%Y-%m-%d %H:%M')
                    due_date = issued_date + timedelta(days=15)
                    db.execute(
                        'INSERT INTO issued_books (book_id, member_id, issued_date, due_date, fine) VALUES (?,?,?,?,0)',
                        (book_id, member_id,
                         issued_date.strftime('%Y-%m-%d %H:%M:%S'),
                         due_date.strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    db.execute('UPDATE books SET quantity = quantity - 1 WHERE id=?', (book_id,))
                    db.commit()
                    flash(f'"{book["title"]}" issued to {member["name"]}. Due: {due_date.strftime("%d %b %Y")}.', 'success')
                    return redirect(url_for('view_issued_books'))

    books = db.execute('SELECT * FROM books WHERE quantity > 0 ORDER BY title').fetchall()
    members = db.execute('SELECT * FROM members ORDER BY name').fetchall()
    return render_template('issue_book.html', books=books, members=members, now=datetime.now())

@app.route('/view_issued_books')
@login_required
def view_issued_books():
    db = get_db()
    status_filter = request.args.get('status', 'all')
    query = request.args.get('q', '').strip()
    sql = '''
        SELECT ib.id, b.id as book_id, b.title, b.category,
               m.id as member_id, m.name as member_name, m.roll_number,
               ib.issued_date, ib.due_date, ib.return_date,
               ib.number_of_days, ib.fine
        FROM issued_books ib
        JOIN books b ON ib.book_id = b.id
        JOIN members m ON ib.member_id = m.id
        WHERE 1=1
    '''
    params = []
    if status_filter == 'active':
        sql += ' AND ib.return_date IS NULL'
    elif status_filter == 'returned':
        sql += ' AND ib.return_date IS NOT NULL'
    elif status_filter == 'overdue':
        sql += ' AND ib.return_date IS NULL AND ib.due_date < ?'
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    if query:
        sql += ' AND (b.title LIKE ? OR m.name LIKE ? OR m.roll_number LIKE ?)'
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
    sql += ' ORDER BY ib.issued_date DESC'
    issued_books = db.execute(sql, params).fetchall()
    now = datetime.now()
    return render_template('view_issued_books.html',
                           issued_books=issued_books,
                           status_filter=status_filter,
                           query=query,
                           now=now)

@app.route('/return_book', methods=['GET', 'POST'])
@login_required
def return_book():
    db = get_db()
    if request.method == 'POST':
        issue_id = request.form['issue_id']
        return_date_str = request.form['return_date'] + ' ' + request.form['return_time']
        issued_book = db.execute('SELECT * FROM issued_books WHERE id=?', (issue_id,)).fetchone()
        if not issued_book:
            flash('No matching issued record found.', 'danger')
        elif issued_book['return_date']:
            flash('This book has already been returned.', 'warning')
        else:
            return_dt = datetime.strptime(return_date_str, '%Y-%m-%d %H:%M')
            issued_dt = datetime.strptime(issued_book['issued_date'], '%Y-%m-%d %H:%M:%S')
            number_of_days = (return_dt - issued_dt).days
            fine = max(0, (number_of_days - 15) * 45)
            db.execute(
                'UPDATE issued_books SET return_date=?, number_of_days=?, fine=? WHERE id=?',
                (return_dt.strftime('%Y-%m-%d %H:%M:%S'), number_of_days, fine, issue_id)
            )
            db.execute('UPDATE books SET quantity = quantity + 1 WHERE id=?', (issued_book['book_id'],))
            db.commit()
            book = db.execute('SELECT title FROM books WHERE id=?', (issued_book['book_id'],)).fetchone()
            if fine > 0:
                flash(f'"{book["title"]}" returned. Fine: ₹{fine} ({number_of_days} days).', 'warning')
            else:
                flash(f'"{book["title"]}" returned on time. No fine.', 'success')
            return redirect(url_for('view_issued_books'))

    # Get active issued records for return
    active_issues = db.execute('''
        SELECT ib.id, b.title, m.name, m.roll_number, ib.issued_date, ib.due_date
        FROM issued_books ib
        JOIN books b ON ib.book_id = b.id
        JOIN members m ON ib.member_id = m.id
        WHERE ib.return_date IS NULL
        ORDER BY ib.due_date
    ''').fetchall()
    return render_template('return_book.html', active_issues=active_issues, now=datetime.now())

@app.route('/overdue_books')
@login_required
def overdue_books():
    db = get_db()
    now = datetime.now()
    overdue = db.execute('''
        SELECT ib.id, b.title, b.category,
               m.name as member_name, m.roll_number, m.department, m.phone,
               ib.issued_date, ib.due_date,
               CAST((julianday('now') - julianday(ib.due_date)) AS INTEGER) as days_overdue
        FROM issued_books ib
        JOIN books b ON ib.book_id = b.id
        JOIN members m ON ib.member_id = m.id
        WHERE ib.return_date IS NULL AND ib.due_date < ?
        ORDER BY ib.due_date ASC
    ''', (now.strftime('%Y-%m-%d %H:%M:%S'),)).fetchall()
    return render_template('overdue_books.html', overdue=overdue, now=now)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
