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
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 403

    data = request.get_json()
    solve_time = data["time"]
    scramble = data["scramble"]
    penalty = 0
    comment = ""
    date = int(time.time())

    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO Solves (time, penalty, comment, date, scramble) VALUES (?, ?, ?, ?, ?)",
              (solve_time, penalty, comment, date, scramble))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT solveID, time FROM Solves ORDER BY solveID")
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
        
        flash('You were successfully registered!')
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
            flash('You were successfully logged in!')
            return redirect(url_for('timer'))
        else:
            flash('Invalid credentials')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You were successfully logged out!')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
