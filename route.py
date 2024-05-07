from flask import Flask, render_template
import sqlite3


app = Flask(__name__)

@app.route("/")
def homepage():
    return render_template("layout.html")

@app.route("/about")
def about():
    return(":(")

@app.route("/results/<int:id>")
def result(id):
    conn = sqlite3.connect("results.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Pizza WHERE PizzaID=?",(id,))
    pizza = cur.fetchone()
    return render_template("pizza.html", pizza=pizza)

if __name__ == "__main__":
    app.run(debug=True)