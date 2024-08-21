from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash
import sqlite3
import time

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def connect_db():
    return sqlite3.connect('results.db')

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return ":("

@app.route("/timer")
def timer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("timer.html")

@app.route("/save_time", methods=["POST"])
def save_time():
    if 'user_id' not in session or 'active_session_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in or no active session"}), 403

    data = request.get_json()
    solve_time = data["time"]
    scramble = data["scramble"]
    date = int(time.time())
    session_id = session['active_session_id']

    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO Solves (time, date, scramble, sessionID) VALUES (?, ?, ?, ?)",
              (solve_time, date, scramble, session_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'active_session_id' not in session:
        flash('No active session selected.', 'warning')
        return redirect(url_for('sessions'))

    session_id = session['active_session_id']

    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT time, scramble FROM Solves WHERE sessionID = ? ORDER BY solveID", (session_id,))
    solves = c.fetchall()
    conn.close()

    return render_template("results.html", solves=solves)

@app.route('/delete_most_recent', methods=["POST"])
def delete_most_recent():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM Solves WHERE solveID = (SELECT solveID FROM Solves ORDER BY solveID DESC LIMIT 1)")
    conn.commit()
    conn.close()
    return redirect(url_for('results'))

@app.route('/delete_all', methods=["POST"])
def delete_all():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM Solves")
    conn.commit()
    conn.close()
    return redirect(url_for('results'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO Users (userName, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        flash('You were successfully registered!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT userID, password FROM Users WHERE userName = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and password == user[1]:
            session['user_id'] = user[0]
            flash('You were successfully logged in!', 'success')
            return redirect(url_for('sessions'))
        else:
            flash('Username or password is incorrect', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You were successfully logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/sessions', methods=['GET', 'POST'])
def sessions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    if request.method == 'POST':
        if 'session_name' in request.form:
            session_name = request.form['session_name']
            c.execute("INSERT INTO Sessions (sessionName, isPinned, userID) VALUES (?, ?, ?)",
                      (session_name, 0, user_id))
            conn.commit()

        elif 'delete_session_id' in request.form:
            delete_session_id = request.form['delete_session_id']

            # First delete all solves in this session to avoid foreign key constraints
            c.execute("DELETE FROM Solves WHERE sessionID = ?", (delete_session_id,))
            conn.commit()

            # Then delete the session
            c.execute("DELETE FROM Sessions WHERE sessionID = ?", (delete_session_id,))
            conn.commit()

            # Remove the session from the active session
            if session.get('active_session_id') == int(delete_session_id):
                session.pop('active_session_id', None)

    c.execute("SELECT sessionID, sessionName, isPinned FROM Sessions WHERE userID = ?", (user_id,))
    user_sessions = c.fetchall()
    conn.close()

    return render_template('sessions.html', sessions=user_sessions)

@app.route('/session/<int:session_id>')
def view_session(session_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT solveID, time, scramble FROM Solves WHERE sessionID = ?", (session_id,))
    session_solves = c.fetchall()
    conn.close()

    return render_template('view_session.html', solves=session_solves)

@app.route('/set_active_session/<int:session_id>')
def set_active_session(session_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Set the active session ID in the session
    session['active_session_id'] = session_id
    return redirect(url_for('timer'))  # Redirect to the timer page

# Route for non-existing page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)