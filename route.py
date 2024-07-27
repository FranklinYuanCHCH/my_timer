from flask import Flask, render_template, request, session, jsonify
import sqlite3
from datetime import datetime


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
    time = data.get('time')
    scramble = data.get('scramble')
    penalty = 0  # Add your logic to calculate penalty if needed
    comment = '' # Add your logic to get the comment if needed
    date = int(datetime.now().timestamp())

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Solves (time, penalty, comment, date, scramble) VALUES (?, ?, ?, ?, ?)", 
                   (time, penalty, comment, date, scramble))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(debug=True)