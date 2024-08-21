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
    
    if 'active_session_name' not in session:
        flash("No active session selected. Please select a session.", 'warning')
        return redirect(url_for('sessions'))

    active_session_name = session.get('active_session_name')
    return render_template("timer.html", active_session_name=active_session_name)

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
    sort_by = request.args.get('sort_by', 'date')  # Default to 'date'

    conn = connect_db()
    c = conn.cursor()

    if sort_by == 'time':
        c.execute("SELECT time, scramble FROM Solves WHERE sessionID = ? ORDER BY time", (session_id,))
    else:  # Default to sorting by date
        c.execute("SELECT time, scramble FROM Solves WHERE sessionID = ? ORDER BY date", (session_id,))

    solves = c.fetchall()
    conn.close()

    return render_template("results.html", solves=solves, sort_by=sort_by)

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
        password2 = request.form['password2']

        if password != password2:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT userName FROM Users WHERE userName = ?", (username,))
        existing_user = c.fetchone()
        
        if existing_user:
            flash('Username is already taken', 'danger')
        else:
            c.execute("INSERT INTO Users (userName, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash('You were successfully registered!', 'success')
            return redirect(url_for('login'))
        
        conn.close()

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
                session.pop('active_session_name', None)

    c.execute("SELECT sessionID, sessionName, isPinned FROM Sessions WHERE userID = ?", (user_id,))
    user_sessions = c.fetchall()
    conn.close()

    return render_template('sessions.html', sessions=user_sessions)

@app.route('/set_active_session/<int:session_id>')
def set_active_session(session_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT sessionName FROM Sessions WHERE sessionID = ?", (session_id,))
    session_data = c.fetchone()
    
    if session_data:
        session['active_session_id'] = session_id
        session['active_session_name'] = session_data[0]
        flash(f"Active session set to {session_data[0]}", 'success')
    else:
        flash("Session not found", 'danger')
    
    conn.close()
    return redirect(url_for('timer'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    if request.method == 'POST':
        if 'new_username' in request.form:
            new_username = request.form['new_username']
            
            # Check if the new username already exists
            c.execute("SELECT userName FROM Users WHERE userName = ?", (new_username,))
            existing_user = c.fetchone()
            
            if existing_user:
                flash('Username is already taken.', 'danger')
            else:
                c.execute("UPDATE Users SET userName = ? WHERE userID = ?", (new_username, user_id))
                conn.commit()
                flash('Username updated successfully', 'success')

        if 'current_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            c.execute("SELECT password FROM Users WHERE userID = ?", (user_id,))
            stored_password = c.fetchone()[0]

            if current_password != stored_password:
                flash('Current password is incorrect', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match', 'danger')
            else:
                c.execute("UPDATE Users SET password = ? WHERE userID = ?", (new_password, user_id))
                conn.commit()
                flash('Password updated successfully', 'success')

    c.execute("SELECT userName FROM Users WHERE userID = ?", (user_id,))
    user_info = c.fetchone()
    conn.close()

    return render_template('dashboard.html', user_info=user_info)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    # Delete all solves for the user
    c.execute("DELETE FROM Solves WHERE sessionID IN (SELECT sessionID FROM Sessions WHERE userID = ?)", (user_id,))
    
    # Delete all sessions for the user
    c.execute("DELETE FROM Sessions WHERE userID = ?", (user_id,))
    
    # Delete the user account
    c.execute("DELETE FROM Users WHERE userID = ?", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    flash('Your account has been deleted', 'success')
    return redirect(url_for('register'))

# Route for non-existing page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)