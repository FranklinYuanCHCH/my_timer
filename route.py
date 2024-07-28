from flask import Flask, render_template, request, session, jsonify, redirect, url_for
import sqlite3
import time


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return(":(")

# @app.route('/login', methods=['GET', 'POST'])
# def login():

def connect_db():
    return sqlite3.connect('results.db')

@app.route("/timer")
def timer():
    return render_template("timer.html")

@app.route("/save_time", methods=["POST"])
def save_time():
    data = request.get_json()
    solve_time = data["time"]
    scramble = data["scramble"]
    penalty = 0  # Adjust as needed
    comment = ""
    date = int(time.time())

    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    c.execute("INSERT INTO Solves (time, penalty, comment, date, scramble) VALUES (?, ?, ?, ?, ?)",
              (solve_time, penalty, comment, date, scramble))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/results')
def results():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    c.execute("SELECT solveID, time FROM Solves ORDER BY solveID")
    solves = c.fetchall()
    conn.close()
    return render_template("results.html", solves=solves)

@app.route('/delete_most_recent', methods=["POST"])
def delete_most_recent():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    c.execute("DELETE FROM Solves WHERE solveID = (SELECT solveID FROM Solves ORDER BY solveID DESC LIMIT 1)")
    conn.commit()
    conn.close()
    return redirect(url_for('results'))

@app.route('/delete_all', methods=["POST"])
def delete_all():
    conn = sqlite3.connect('results.db')
    c = conn.cursor()
    c.execute("DELETE FROM Solves")
    conn.commit()
    conn.close()
    return redirect(url_for('results'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)