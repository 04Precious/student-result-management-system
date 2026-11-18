
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-key-change-before-deployment")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

DATABASE = os.environ.get("DATABASE_PATH", "database.db")


# Database connection
def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# Create database tables
def init_db():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE NOT NULL,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            subject_code TEXT UNIQUE NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            marks_obtained REAL NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id),
            UNIQUE(student_id, subject_id)
        )
    """)

    connection.commit()
    connection.close()


# Authentication
def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view_function(*args, **kwargs)
    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["admin_logged_in"] = True
            session["admin_name"] = "Amit Abhishek"
            flash("Welcome, Administrator!")
            return redirect(url_for("home"))

        flash("Incorrect username or password.")

    return render_template("login.html")


@app.route("/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("admin_login"))


@app.route("/student", methods=["GET", "POST"])
def student_portal():
    student = None
    marks = None
    result = None
    roll_number = ""

    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip()

        if not roll_number:
            flash("Please enter your roll number.")
        else:
            connection = get_db()
            student = connection.execute(
                "SELECT * FROM students WHERE roll_number = ?",
                (roll_number,)
            ).fetchone()

            if student:
                marks = connection.execute("""
                    SELECT subjects.subject_name, subjects.subject_code,
                           marks.marks_obtained
                    FROM marks
                    JOIN subjects ON marks.subject_id = subjects.id
                    WHERE marks.student_id = ?
                    ORDER BY subjects.subject_name
                """, (student["id"],)).fetchall()
            connection.close()

            if not student:
                flash("No student found with that roll number.")
            elif not marks:
                flash("Your marks have not been entered yet.")
                student = None
            else:
                total = sum(m["marks_obtained"] for m in marks)
                maximum = len(marks) * 100
                percentage = total / maximum * 100
                passed = all(m["marks_obtained"] >= 40 for m in marks)

                if not passed:
                    grade, status = "F", "FAIL"
                elif percentage >= 90:
                    grade, status = "A+", "PASS"
                elif percentage >= 80:
                    grade, status = "A", "PASS"
                elif percentage >= 70:
                    grade, status = "B+", "PASS"
                elif percentage >= 60:
                    grade, status = "B", "PASS"
                elif percentage >= 50:
                    grade, status = "C", "PASS"
                elif percentage >= 40:
                    grade, status = "D", "PASS"
                else:
                    grade, status = "F", "FAIL"

                result = {
                    "total": round(total, 2),
                    "maximum": maximum,
                    "percentage": round(percentage, 2),
                    "grade": grade,
                    "status": status
                }

    return render_template(
        "student_portal.html",
        student=student,
        marks=marks,
        result=result,
        roll_number=roll_number
    )


# Dashboard
@app.route("/")
@admin_required
def home():
    connection = get_db()

    total_students = connection.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    total_subjects = connection.execute(
        "SELECT COUNT(*) FROM subjects"
    ).fetchone()[0]

    connection.close()

    return render_template(
        "index.html",
        total_students=total_students,
        total_subjects=total_subjects
    )


# Student management
@app.route("/students")
@admin_required
def students():
    search = request.args.get("search", "").strip()

    connection = get_db()

    records = connection.execute("""
        SELECT * FROM students
        WHERE name LIKE ? OR roll_number LIKE ?
        ORDER BY id DESC
    """, (f"%{search}%", f"%{search}%")).fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=records,
        search=search
    )


@app.route("/students/add", methods=["POST"])
@admin_required
def add_student():
    name = request.form.get("name", "").strip()
    roll = request.form.get("roll_number", "").strip()
    course = request.form.get("course", "").strip()
    semester = request.form.get("semester", "").strip()

    if not all([name, roll, course, semester]):
        flash("Please fill all fields.")
        return redirect(url_for("students"))

    try:
        semester_number = int(semester)

        if semester_number < 1 or semester_number > 8:
            raise ValueError

        connection = get_db()

        connection.execute("""
            INSERT INTO students
            (name, roll_number, course, semester)
            VALUES (?, ?, ?, ?)
        """, (name, roll, course, semester_number))

        connection.commit()
        connection.close()

        flash("Student registered successfully!")

    except sqlite3.IntegrityError:
        connection.close()
        flash("This roll number already exists.")

    except ValueError:
        flash("Enter a valid semester between 1 and 8.")

    return redirect(url_for("students"))


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):
    connection = get_db()

    connection.execute(
        "DELETE FROM marks WHERE student_id = ?",
        (student_id,)
    )

    connection.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )

    connection.commit()
    connection.close()

    flash("Student deleted successfully!")
    return redirect(url_for("students"))


# Subject management
@app.route("/subjects")
@admin_required
def subjects():
    search = request.args.get("search", "").strip()

    connection = get_db()

    records = connection.execute("""
        SELECT * FROM subjects
        WHERE subject_name LIKE ? OR subject_code LIKE ?
        ORDER BY id DESC
    """, (f"%{search}%", f"%{search}%")).fetchall()

    connection.close()

    return render_template(
        "subjects.html",
        subjects=records,
        search=search
    )


# Add a subject
@app.route("/subjects/add", methods=["POST"])
@admin_required
def add_subject():
    subject_name = request.form.get(
        "subject_name", ""
    ).strip()

    subject_code = request.form.get(
        "subject_code", ""
    ).strip().upper()

    if not subject_name or not subject_code:
        flash("Please fill in both subject fields.")
        return redirect(url_for("subjects"))

    connection = get_db()

    try:
        connection.execute("""
            INSERT INTO subjects (subject_name, subject_code)
            VALUES (?, ?)
        """, (subject_name, subject_code))

        connection.commit()
        flash("Subject added successfully!")

    except sqlite3.IntegrityError:
        flash("This subject code already exists.")

    finally:
        connection.close()

    return redirect(url_for("subjects"))


# Delete a subject
@app.route("/subjects/delete/<int:subject_id>", methods=["POST"])
@admin_required
def delete_subject(subject_id):
    connection = get_db()

    connection.execute(
        "DELETE FROM marks WHERE subject_id = ?",
        (subject_id,)
    )

    connection.execute(
        "DELETE FROM subjects WHERE id = ?",
        (subject_id,)
    )

    connection.commit()
    connection.close()

    flash("Subject deleted successfully!")

    return redirect(url_for("subjects"))


# Marks Management
@app.route("/marks")
@admin_required
def marks():
    connection = get_db()

    students = connection.execute(
        "SELECT * FROM students ORDER BY name"
    ).fetchall()

    subjects = connection.execute(
        "SELECT * FROM subjects ORDER BY subject_name"
    ).fetchall()

    records = connection.execute("""
        SELECT
            marks.id,
            students.name,
            students.roll_number,
            subjects.subject_name,
            subjects.subject_code,
            marks.marks_obtained
        FROM marks
        JOIN students ON marks.student_id = students.id
        JOIN subjects ON marks.subject_id = subjects.id
        ORDER BY marks.id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "marks.html",
        students=students,
        subjects=subjects,
        records=records
    )


# Add marks
@app.route("/marks/add", methods=["POST"])
@admin_required
def add_marks():
    student_id = request.form.get("student_id", "").strip()
    subject_id = request.form.get("subject_id", "").strip()
    marks_value = request.form.get("marks_obtained", "").strip()

    try:
        student_id = int(student_id)
        subject_id = int(subject_id)
        marks_value = float(marks_value)

        if not 0 <= marks_value <= 100:
            flash("Marks must be between 0 and 100.")
            return redirect(url_for("marks"))

        connection = get_db()

        student = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        subject = connection.execute(
            "SELECT id FROM subjects WHERE id = ?",
            (subject_id,)
        ).fetchone()

        if not student or not subject:
            flash("Please select a valid student and subject.")
            connection.close()
            return redirect(url_for("marks"))

        connection.execute("""
            INSERT INTO marks
            (student_id, subject_id, marks_obtained)
            VALUES (?, ?, ?)
        """, (student_id, subject_id, marks_value))

        connection.commit()
        connection.close()

        flash("Marks saved successfully!")

    except sqlite3.IntegrityError:
        connection.close()
        flash("Marks already entered for this student and subject.")

    except ValueError:
        flash("Please enter valid marks.")

    return redirect(url_for("marks"))


# Delete marks
@app.route("/marks/delete/<int:mark_id>", methods=["POST"])
@admin_required
def delete_marks(mark_id):
    connection = get_db()

    connection.execute(
        "DELETE FROM marks WHERE id = ?",
        (mark_id,)
    )

    connection.commit()
    connection.close()

    flash("Marks record deleted successfully!")

    return redirect(url_for("marks"))

# Automatic Result Generation
@app.route("/results")
@admin_required
def results():

    connection = get_db()

    result_records = connection.execute("""
        SELECT
            students.id AS student_id,
            students.name,
            students.roll_number,
            students.course,
            students.semester,
            COUNT(marks.id) AS subjects_count,
            SUM(marks.marks_obtained) AS total_marks,
            SUM(marks.marks_obtained) AS obtained_marks,
            GROUP_CONCAT(subjects.subject_name, ', ') AS subject_names
        FROM students
        JOIN marks ON students.id = marks.student_id
        JOIN subjects ON marks.subject_id = subjects.id
        GROUP BY students.id
        ORDER BY students.name
    """).fetchall()

    connection.close()

    results_list = []

    for student in result_records:

        total = student["total_marks"]
        subjects_count = student["subjects_count"]
        maximum = subjects_count * 100

        percentage = (total / maximum) * 100

        # Check whether every subject has passing marks
        connection = get_db()

        subject_marks = connection.execute("""
            SELECT marks_obtained
            FROM marks
            WHERE student_id = ?
        """, (student["student_id"],)).fetchall()

        connection.close()

        passed = all(
            mark["marks_obtained"] >= 40
            for mark in subject_marks
        )

        if not passed:
            grade = "F"
            status = "FAIL"

        elif percentage >= 90:
            grade = "A+"
            status = "PASS"

        elif percentage >= 80:
            grade = "A"
            status = "PASS"

        elif percentage >= 70:
            grade = "B+"
            status = "PASS"

        elif percentage >= 60:
            grade = "B"
            status = "PASS"

        elif percentage >= 50:
            grade = "C"
            status = "PASS"

        elif percentage >= 40:
            grade = "D"
            status = "PASS"

        else:
            grade = "F"
            status = "FAIL"

        results_list.append({
            "student_id": student["student_id"],
            "name": student["name"],
            "roll_number": student["roll_number"],
            "course": student["course"],
            "semester": student["semester"],
            "total": round(total, 2),
            "maximum": maximum,
            "percentage": round(percentage, 2),
            "grade": grade,
            "status": status
        })

    return render_template(
        "results.html",
        results=results_list
    )


# Individual student result
@app.route("/results/<int:student_id>")
@admin_required
def student_result(student_id):

    connection = get_db()

    student = connection.execute("""
        SELECT * FROM students WHERE id = ?
    """, (student_id,)).fetchone()

    if not student:
        connection.close()
        return "Student not found", 404

    marks = connection.execute("""
        SELECT
            subjects.subject_name,
            subjects.subject_code,
            marks.marks_obtained
        FROM marks
        JOIN subjects ON marks.subject_id = subjects.id
        WHERE marks.student_id = ?
        ORDER BY subjects.subject_name
    """, (student_id,)).fetchall()

    connection.close()

    if not marks:
        return "No marks available for this student", 404

    total = sum(m["marks_obtained"] for m in marks)
    maximum = len(marks) * 100
    percentage = total / maximum * 100

    passed = all(m["marks_obtained"] >= 40 for m in marks)

    if not passed:
        grade = "F"
        status = "FAIL"
    elif percentage >= 90:
        grade, status = "A+", "PASS"
    elif percentage >= 80:
        grade, status = "A", "PASS"
    elif percentage >= 70:
        grade, status = "B+", "PASS"
    elif percentage >= 60:
        grade, status = "B", "PASS"
    elif percentage >= 50:
        grade, status = "C", "PASS"
    elif percentage >= 40:
        grade, status = "D", "PASS"
    else:
        grade, status = "F", "FAIL"

    return render_template(
        "student_result.html",
        student=student,
        marks=marks,
        total=round(total, 2),
        maximum=maximum,
        percentage=round(percentage, 2),
        grade=grade,
        status=status
    )

init_db()

if __name__ == "__main__":
    app.run(debug=False)
