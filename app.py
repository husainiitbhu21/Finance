import os
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Accces user's cash
    m = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    money = m
    # money is total value i.e cash and stock combined

    # We need table (stock) in database:
    # -> stock_id
    # -> symbol
    # -> name
    # -> shares
    # -> person_id

    # Access user's stock symbol, shares
    stocks = db.execute("SELECT symbol, SUM(shares) AS sum_shares FROM stocks WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0 ORDER BY symbol", session["user_id"])

    # Add the name, price and total with lookup function of API to every stock defined in helpers.py
    for stock in stocks:
        api = lookup(stock["symbol"])
        stock["name"] = api["name"]
        stock["price"] = api["price"]
        stock["total"] = stock["sum_shares"] * stock["price"]
        money += stock["total"]

    return render_template("index.html", stocks=stocks, cash=m, total=money)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "GET":
        return render_template("buy.html")

    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        api = lookup(symbol)

        if not symbol:
            return apology("missing symbol")
        elif api == None:
            return apology("invalid symbol")
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("invalid number")
        else:
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
            k = cash - api["price"] * int(shares)
            if k < 0:
                return apology("insufficient balance")
            else:
                cash = k
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
                db.execute("INSERT INTO stocks (user_id, symbol, name, price, shares, datetime) VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], symbol, api["name"], api["price"], int(shares), datetime.now())
                flash('Bought!')
                return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    stocks = db.execute("SELECT symbol, name, shares, price, datetime FROM stocks WHERE user_id = ?", session["user_id"])
    if not stocks:
        return apology("No history", 403)

    else:
        for stock in stocks:
            if stock["shares"] > 0:
                stock["status"] = "Bought"
            else:
                stock["status"] = "Sold"
        return render_template("history.html", stocks=stocks)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)

        # Ensure symbol exists in API KEY
        if not symbol:
            return apology("missing symbol")

        elif quote == None:
            return apology("invalid symbol")

        else:
            name = quote["name"]
            price = quote["price"]
            return render_template("quoted.html", name=name, symbol=symbol, price=price)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    name = request.form.get("username")
    p1 = request.form.get("password")
    p2 = request.form.get("confirmation")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not name:
            return apology("must provide username")

        # Ensure password was submitted
        elif not p1:
            return apology("must provide password")

        # Ensure confirmation matches with password
        elif p1 != p2:
            return apology("password and confirmation don't match")

        # Ensure username does not exists before
        elif db.execute("SELECT username FROM users WHERE username = ?", name):
            return apology("username already exist")

        # Take user in
        else:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", name, generate_password_hash(p1))
            # Remember which user has logged in (intentionally change variable rows to row)
            row = db.execute("SELECT * FROM users WHERE username = ?", name)
            session["user_id"] = row[0]["id"]
            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "GET":
        # Access user's stock symbol, shares
        symbols = db.execute("SELECT symbol FROM stocks WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0 ORDER BY symbol", session["user_id"])
        return render_template("sell.html", symbols=symbols)

    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        api = lookup(symbol)

        if not symbol:
            return apology("missing symbol")
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("invalid shares")
        else:
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
            m = int(shares)
            l = db.execute("SELECT SUM(shares) AS sum_shares FROM stocks WHERE user_id = ? AND symbol = ? GROUP BY symbol HAVING SUM(shares) > 0", session["user_id"], symbol)
            k = l[0]["sum_shares"]
            if k < m:
                return apology("too many shares")
            else:
                cash += m * api["price"]
                q = int(shares) * (-1)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])
                db.execute("INSERT INTO stocks (user_id, symbol, name, price, shares, datetime) VALUES(?, ?, ?, ?, ?, ?)", session["user_id"], symbol, api["name"], api["price"], q, datetime.now())
                flash('Sold!')
                return redirect("/")


@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    """Get extra cash."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        cash1 = request.form.get("addcash")

        # Ensure symbol exists in API KEY
        if not cash1:
            return apology("missing cash")

        elif not cash1.isdigit() or int(cash1) <= 0:
            return apology("invalid cash")

        else:
            flash('Cash Added')
            cash2 = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            cash5 = int(cash2[0]["cash"]) + int(cash1)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash5, session["user_id"])
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("addcash.html")