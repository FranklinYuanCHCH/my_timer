from flask import Flask, render_template
# import sqlite3


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return(":(")

@app.route("/timer")
def result():
    return render_template("timer.html")

if __name__ == "__main__":
    app.run(debug=True)