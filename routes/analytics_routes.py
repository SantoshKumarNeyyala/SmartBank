import pandas as pd
import matplotlib.pyplot as plt
from flask import Blueprint, render_template
from database.connection import get_connection

analytics = Blueprint("analytics", __name__)

@analytics.route("/analytics")
def show_analytics():
    conn = get_connection()
    df = pd.read_sql("SELECT type, amount FROM transactions", conn)
    conn.close()

    summary = df.groupby("type")["amount"].sum()
    summary.plot(kind="bar")
    plt.title("Transaction Summary")
    plt.savefig("static/analytics.png")
    plt.close()

    return render_template("analytics.html")