from flask import Flask, render_template, request, session, jsonify, redirect
from flask import url_for, flash, make_response
import bcrypt
import sqlite3
import time

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Use constants for maximum lengths for username, password, and session name
USERNAME_MAX = 16
PASSWORD_MAX = 16
SESSION_NAME_MAX = 16

# Function to set response headers to prevent caching
# Prevents the browser from accessing previous pages using the back function
def prevent_cache(response):
    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0')
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Connect to the SQLite database
def connect_db():
    return sqlite3.connect('results.db')


@app.route("/")
def home():
    response = make_response(render_template("index.html"))
    prevent_cache(response)
    return response


@app.route("/guide")
def guide():
    response = make_response(render_template("guide.html"))
    prevent_cache(response)
    return response


@app.route("/about")
def about():
    response = make_response(render_template("about.html"))
    prevent_cache(response)
    return response


@app.route("/timer")
def timer():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'active_session_name' not in session:
        flash("No active session selected. Please select a session.", 'danger')
        return redirect(url_for('sessions'))

    active_session_name = session.get('active_session_name')
    response = make_response(render_template("timer.html",
                                             active_session_name=active_session_name))
    prevent_cache(response)
    return response


@app.route("/save_time", methods=["POST"])
def save_time():
    # Check if the user is logged in and has an active session; return error if not
    if 'user_id' not in session or 'active_session_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in or no active session"}), 403

    # Retrieve the solve time and scramble data from the request
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

    response = jsonify({"status": "success"})
    prevent_cache(response)
    return response


@app.route("/get_recent_solves")
def get_recent_solves():
    if 'user_id' not in session or 'active_session_id' not in session:
        response = jsonify({'solves': []})
        prevent_cache(response)
        return response

    session_id = session['active_session_id']

    # Fetch the most recent solve times for the active session, limited to 5
    conn = connect_db()
    c = conn.cursor()
    c.execute("""
        SELECT time FROM Solves
        WHERE sessionID = ?
        ORDER BY date DESC
        LIMIT 5
    """, (session_id,))
    recent_solves = c.fetchall()
    conn.close()

    # Format the response with recent solve times
    response = jsonify({'solves': [{'time': solve[0]} for solve in recent_solves]})
    prevent_cache(response)
    return response


@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'active_session_id' not in session:
        flash('No active session selected.', 'danger')
        return redirect(url_for('sessions'))

    session_id = session['active_session_id']
    # Set default sorting option
    sort_by = request.args.get('sort_by', 'date_desc')

    conn = connect_db()
    c = conn.cursor()

    # Construct the query based on the sorting option   
    query = (
        "SELECT solveID, time, scramble FROM Solves WHERE sessionID = ? ORDER BY {}"
    ).format(
        'time' if sort_by == 'time' else
        'time DESC' if sort_by == 'time_desc' else
        'date DESC' if sort_by == 'date_desc' else 'date'
    )
    c.execute(query, (session_id,))
    solves = c.fetchall()
    conn.close()

    response = make_response(render_template("results.html", solves=solves, sort_by=sort_by))
    prevent_cache(response)
    return response


# Route for deleting a specific solve
@app.route('/delete_solve/<int:solve_id>', methods=['POST'])
def delete_solve(solve_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    c = conn.cursor()

    c.execute("DELETE FROM Solves WHERE solveID = ?", (solve_id,))
    conn.commit()
    conn.close()

    flash('Solve deleted successfully.', 'success')
    return redirect(url_for('results'))


# Route for deleting the most recent solve of the session
@app.route('/delete_most_recent', methods=["POST"])
def delete_most_recent():
    # Ensure the user is logged in and has an active session; return error if not
    if 'user_id' not in session or 'active_session_id' not in session:
        response = jsonify({"status": "error",
                            "message": "Not logged in or no active session"}), 403
        prevent_cache(response)
        return response

    session_id = session['active_session_id']

    conn = connect_db()
    c = conn.cursor()
    # Delete the most recent solve from the Solves table for the active session
    c.execute("""DELETE FROM Solves WHERE solveID =
              (SELECT solveID FROM Solves WHERE sessionID = ?
              ORDER BY date DESC LIMIT 1)""", (session_id,))
    conn.commit()
    conn.close()

    # Return a success message confirming the deletion
    response = jsonify({"status": "success",
                        "message": "Most recent solve deleted"})
    prevent_cache(response)
    return response


# Route for deleting all solves in the current session
@app.route('/delete_all', methods=["POST"])
def delete_all():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM Solves")
    conn.commit()
    conn.close()

    response = redirect(url_for('results'))
    prevent_cache(response)
    return response


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Retrieve and strip input values from the registration form
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        # Validate input fields and provide feedback
        if not username or not password or not confirm_password:
            flash('All fields must be filled out.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match', 'danger')
        elif len(username) > USERNAME_MAX:
            flash('Username cannot exceed ' + str(USERNAME_MAX) + ' characters.', 'danger')
        elif len(password) > PASSWORD_MAX:
            flash('Password cannot exceed ' + str(PASSWORD_MAX) + ' characters.', 'danger')
        else:
            conn = connect_db()
            c = conn.cursor()
            # Check if the username is already taken
            c.execute("SELECT userName FROM Users WHERE userName = ?", (username,))
            existing_user = c.fetchone()

            # Check if the username is already taken
            if existing_user:
                flash('Username is already taken', 'danger')
            else:
                # Hash the password before storing it for security
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                c.execute("INSERT INTO Users (userName, password) VALUES (?, ?)",
                          (username, hashed_password))
                conn.commit()
                flash('You were successfully registered!', 'success')
                conn.close()
                return redirect(url_for('login'))
            conn.close()

    response = make_response(render_template('register.html'))
    prevent_cache(response)
    return response


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve and strip input values from the login form
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            flash('Both fields must be filled out.', 'danger')
        else:
            conn = connect_db()
            c = conn.cursor()
            c.execute("SELECT userID, password FROM Users WHERE userName = ?", (username,))
            user = c.fetchone()
            conn.close()

            # Check if the user exists and verify the password
            if user and bcrypt.checkpw(password.encode('utf-8'), user[1]):
                session['user_id'] = user[0]
                flash('You were successfully logged in!', 'success')
                return redirect(url_for('sessions'))
            else:
                flash('Username or password is incorrect', 'danger')

    response = make_response(render_template('login.html'))
    prevent_cache(response)
    return response


@app.route('/logout')
def logout():
    # Clear all the user related data
    session.pop('user_id', None)
    session.pop('active_session_id', None)
    session.pop('active_session_name', None)

    response = redirect(url_for('login'))
    flash('You were successfully logged out!', 'success')
    prevent_cache(response)
    return response


# Route for the sessions page after logging in
@app.route('/sessions', methods=['GET', 'POST'])
def sessions():
    # If the user is not logged in, redirect them to the login page
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    if request.method == 'POST':
        # Handling session creation
        if 'session_name' in request.form:
            session_name = request.form['session_name'].strip()
            if len(session_name) > SESSION_NAME_MAX:
                flash('Session name must not exceed ' + str(SESSION_NAME_MAX) + ' characters.', 'danger')
            elif not session_name:
                flash('Session name must not be blank.', 'danger')
            else:
                c.execute("INSERT INTO Sessions (sessionName, isPinned, userID) VALUES (?, ?, ?)",
                          (session_name, 0, user_id))
                conn.commit()
                flash('Session created successfully.', 'success')

        # Deleting a specific session and all solves associated with it
        elif 'delete_session_id' in request.form:
            session_id = request.form['delete_session_id']
            c.execute("DELETE FROM Sessions WHERE sessionID = ?", (session_id,))
            conn.commit()
            flash('Session deleted successfully.', 'success')

    c.execute("SELECT sessionID, sessionName, isPinned FROM Sessions WHERE userID = ?", (user_id,))
    sessions = c.fetchall()
    conn.close()

    response = make_response(render_template('sessions.html', sessions=sessions))
    prevent_cache(response)
    return response


# Deceleration for the current session variable which will be used on other pages
@app.route('/set_active_session/<int:session_id>')
def set_active_session(session_id):
    if 'user_id' not in session:
        flash('You need to log in to access sessions.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    # Check if the session belongs to the logged-in user
    c.execute("""SELECT sessionName FROM Sessions
              WHERE sessionID = ? AND userID = ?""", (session_id, user_id))
    session_data = c.fetchone()

    if session_data:
        # Session belongs to the user, set it as active
        session['active_session_id'] = session_id
        session['active_session_name'] = session_data[0]
        flash(f"Active session set to {session_data[0]}", 'success')
    else:
        # Either the session doesn't exist or doesn't belong to the user
        flash("You don't have permission to access this session.", 'danger')
        return redirect(url_for('sessions'))

    conn.close()
    response = redirect(url_for('timer'))
    prevent_cache(response)
    return response


# Route for the dashboard (renamed to profile) page
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    # Retrieve the current username for display and updating
    c.execute("SELECT userName FROM Users WHERE userID = ?", (user_id,))
    current_username = c.fetchone()[0]

    if request.method == 'POST':
        # Handle username change
        if 'new_username' in request.form:
            new_username = request.form['new_username'].strip()

            # Validate new username input
            if not new_username:
                flash('Username must not be blank.', 'danger')
            elif len(new_username) > USERNAME_MAX:
                flash('Username must be ' + str(USERNAME_MAX) + ' characters or less.', 'danger')
            elif new_username == current_username:
                flash('The new username must be different from the current username.', 'danger')
            else:
                c.execute("SELECT userName FROM Users WHERE userName = ?", (new_username,))
                existing_user = c.fetchone()

                # Check if the new username is already taken
                if existing_user:
                    flash('Username is already taken.', 'danger')
                else:
                    c.execute("""
                        UPDATE Users SET userName = ? WHERE userID = ?
                    """, (new_username, user_id))
                    conn.commit()
                    flash('Username updated successfully', 'success')

        # Handle password change
        if 'current_password' in request.form:
            current_password = request.form['current_password'].strip()
            new_password = request.form['new_password'].strip()
            confirm_password = request.form['confirm_password'].strip()

            # Check if password fields are filled out and validate passwords
            if not current_password or not new_password or not confirm_password:
                flash('All password fields must be filled out.', 'danger')
            else:
                # Retrieve the stored password for verification
                c.execute("SELECT password FROM Users WHERE userID = ?", (user_id,))
                stored_password = c.fetchone()

                if not stored_password:
                    flash('Error retrieving stored password.', 'danger')
                else:
                    stored_password = stored_password[0]

                    # Validate the current password and the new password criteria
                    if not bcrypt.checkpw(current_password.encode('utf-8'), stored_password):
                        flash('Current password is incorrect', 'danger')
                    elif new_password != confirm_password:
                        flash('New passwords do not match', 'danger')
                    elif new_password == current_password:
                        flash('Your new password must be different from your current password',
                              'danger')
                    elif len(new_password) > PASSWORD_MAX:
                        flash('Your new password must not exceed ' + str(PASSWORD_MAX) + ' characters', 'danger')
                    else:
                        # Hash the new password and update it in the database
                        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'),
                                                            bcrypt.gensalt())
                        c.execute("""
                            UPDATE Users SET password = ? WHERE userID = ?
                        """, (hashed_new_password, user_id))
                        conn.commit()
                        flash('Password updated successfully', 'success')

    # Fetch user info for display on the profile
    c.execute("SELECT userName FROM Users WHERE userID = ?", (user_id,))
    user_info = c.fetchone()
    conn.close()

    response = make_response(render_template('dashboard.html', user_info=user_info))
    prevent_cache(response)
    return response


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    # Delete all solves for the user
    c.execute("""DELETE FROM Solves WHERE
               sessionID IN (SELECT sessionID
              FROM Sessions WHERE userID = ?)""", (user_id,))

    # Delete all sessions for the user
    c.execute("DELETE FROM Sessions WHERE userID = ?", (user_id,))

    # Delete the user account
    c.execute("DELETE FROM Users WHERE userID = ?", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    flash('Your account has been deleted', 'success')
    response = redirect(url_for('register'))
    prevent_cache(response)
    return response


# Route for single solve stat
@app.route('/solve_stats/<int:solve_id>')
def solve_stats(solve_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = connect_db()
    c = conn.cursor()

    # Fetch solve and details associated sessionID
    c.execute("SELECT time, date, scramble, sessionID FROM Solves WHERE solveID = ?", (solve_id,))
    solve = c.fetchone()

    if solve:
        solve_time, solve_date, scramble, session_id = solve

        # Fetch the user's sessions to check if the solve's sessionID belongs to them
        c.execute("SELECT sessionID FROM Sessions WHERE userID = ?", (user_id,))
        user_sessions = c.fetchall()
        user_session_ids = {session[0] for session in user_sessions}

        if session_id in user_session_ids:
            # Fetch the session name based on session_id
            c.execute("SELECT sessionName FROM Sessions WHERE sessionID = ?", (session_id,))
            session_name = c.fetchone()

            if session_name:
                session_name = session_name[0]
            else:
                session_name = "Unknown Session"

            solve_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(solve_date))
            response = make_response(render_template(
                "solve_stats.html",
                solve_id=solve_id,
                time=solve_time,
                date=solve_date,
                scramble=scramble,
                session_name=session_name  # Passing the session name to the template
            ))
        else:
            # Render error message if the user does not have access to the solve
            response = make_response(render_template(
                'solve_stats.html',
                error_message="Sorry, you can't access this solve."
            ))

    else:
        # Render a 404 page if the solve is not found
        response = make_response(render_template('404.html'), 404)

    prevent_cache(response)
    return response


# Route for non-existing page
@app.errorhandler(404)
def page_not_found(e):
    response = make_response(render_template('404.html'), 404)
    prevent_cache(response)
    return response


# Route for handling server error
@app.errorhandler(405)
def server_error(e):
    response = make_response(render_template('405.html'), 405)
    prevent_cache(response)
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
