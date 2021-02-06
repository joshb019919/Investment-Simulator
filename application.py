"""
Main Flask application.

Help from anything other than official documentation or shameless
copy off the already-built function, "login()", is specified.

SQLite whitespace formatting was inspired by "sqlitetutorial.net".
"""

import os

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import add_transaction, apology, debug, set_data, login_required, lookup, usd, validate, view_data

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Generate display data from session data
    view_data(db)
    session["cash"] = db.execute("SELECT cash FROM main.users WHERE id = :uid", uid=session["user_id"])[0]["cash"]

    return render_template("index.html", cash=usd(session["cash"]), data=session["totals"], total=session["total"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User has bought stock
    if request.method == "POST":

        # Grab values of form symbol and shares
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        # Validate input and make shares an integer
        shares = validate(symbol=symbol, shares=shares, trade=True)

        # Check for quote
        quote = lookup(symbol)

        # Company doesn't exist or doesn't offer stock
        if not quote:
            return apology("company doesn't exist or doesn't have stock", 401)

        # Grab data
        company = quote["name"]
        price = quote["price"]
        user_id = session["user_id"]

        # Calculate total cost of share(s)
        # Total should be precice to 3 places to get accurate rounding, later
        total = round(price * shares, 3)
        debug("Total", total)

        # Get user's cash
        cash = db.execute("SELECT cash FROM users WHERE id = :uid", uid=user_id)[0]["cash"]

        # Not enough cash
        if float(total) > cash:
            return apology("not enough cash", 401)

        session["data"] = {"quote":quote, "symbol":symbol, "shares":shares, "total":total}

        return render_template("confirmation.html", action="Buy", company=company, total=usd(total), symbol=symbol, shares=shares)

    # User clicked on Buy page
    else:
        return render_template("buy.html")


@app.route("/history", methods=["GET"])
@login_required
def history():
    """Show history of transactions"""

    # Provide template with user's history data
    user_id = session["user_id"]
    user_data = db.execute("""SELECT    datetime, company, symbol, action, shares, price, value
                              FROM      main.transactions
                              WHERE     user_id = :uid
                              ORDER BY  datetime""",
                              uid=user_id)

    return render_template("history.html", data=user_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Request username and pass from login form
        username = request.form.get("username")
        password = request.form.get("password")

        # Validate username and password
        validate(username, password, login=True)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                           username=username)

        # Ensure username exists and password is correct
        if (len(rows) != 1 or not
            check_password_hash(rows[0]["hash"], password)):
                return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        user_id = session["user_id"]

        # Add user data to session and redirect user to home page
        set_data(db)
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

    # User has requested a stock quote
    if request.method == "POST":

        # Grab symbol and turn uppercase for display
        symbol = request.form.get("symbol").upper()

        # User left symbol field blank
        if not symbol:
            return apology("must enter stock symbol", 405)

        # Look up quote
        quote = lookup(symbol)

        # Company doesn't exist or doesn't offer stock
        if not quote:
            return apology("company doesn't exist or doesn't have stock", 405)

        # Separate company name and stock price
        company = quote["name"]
        price = quote["price"]

        # Display quote
        return render_template("quoted.html", company=company, price=price, symbol=symbol)

    # Display lookup page
    else:
        return render_template("quote.html")


@app.route("/quoted", methods=["POST"])
@login_required
def quoted():
    """Display quote with option to buy."""

    # Grab symbol to prefill value on buy screen
    symbol = request.form.get("symbol")
    return render_template("buy.html", symbol=symbol)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Make sure user entered password and username
        validate(username=username, password=password, login=True)

        # Password did not match confirmation
        if password != confirmation:
            return apology("passwords did not match", 407)

        # Username is already in database
        elif db.execute("""SELECT   username
                           FROM     main.users
                           WHERE    username = :username""",

                           username=username) == [{"username": username}]:
            return apology("username not available", 407)

        # Hash password
        password = generate_password_hash(
            password, method="pbkdf2:sha256:10000", salt_length=len(password))

        # Add user credentials to database
        db.execute("""INSERT INTO main.users (username, hash)
                      VALUES (:username, :password)""",

                      username=username, password=password)

        # Grab method to add unique response upon reloading login.html
        post = request.method
        return render_template("login.html", post=post)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User has bought stock
    if request.method == "POST":

        # Grab values symbol and shares from form
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        # Validate input and make shares an integer
        shares = validate(symbol=symbol, shares=shares, trade=True)

        # Check for quote
        quote = lookup(symbol)

        # Company doesn't exist or doesn't offer stock
        if not quote:
            return apology("company doesn't exist or doesn't have stock", 408)

        # Grab data
        company = quote["name"]
        price = quote["price"]
        user_id = session["user_id"]

        owned = db.execute("""SELECT    SUM(shares)
                              FROM      main.transactions
                              WHERE     user_id = :uid
                              AND       symbol = :symbol""",

                              uid=user_id, symbol=symbol)[0]

        # User doesn't have that stock or doesn't have enough
        if not owned["SUM(shares)"] or owned["SUM(shares)"] < 1:
            return apology("you don't own that stock", 408)

        elif shares > owned["SUM(shares)"]:
            return apology("you can't sell more than you have", 408)

        # Calculate total cost of share(s)
        total = -price * shares

        session["data"] = {"quote":quote, "symbol":symbol, "shares":shares, "total":total}

        return render_template("confirmation.html", action="Sell", company=company, total=usd(abs(total)), symbol=symbol, shares=shares)

    # User clicked on Sell page
    else:

        # Collect symbols to display on sell page
        current = db.execute("""SELECT DISTINCT     symbol
                                FROM                transactions
                                WHERE               user_id = :uid
                                GROUP BY            symbol
                                HAVING              SUM(shares) >= 1""",

                                uid=session["user_id"])

        return render_template("sell.html", current=current)


@app.route("/confirmation/<action>", methods=["POST"])
@login_required
def confirmation(action):
    """Confirm sale or purchase"""

    # Request action from path
    action = request.path.split("/")[2]

    # Ensure no hijinks occurred
    if not action:
        return apology("no action present", 409)

    # Get user's info from session
    data = session["data"]
    symbol = data["symbol"]
    shares = data["shares"]
    total = data["total"]
    quote = data["quote"]
    company = quote["name"]
    price = quote["price"]
    user_id = session["user_id"]

    # Get user's cash from database
    cash = db.execute("SELECT cash FROM users WHERE id = :uid", uid=user_id)[0]["cash"]

    if action == "Sell":

        # Select user's already owned shares of chosen stock
        # Repeated here to activate even on refresh
        owned = db.execute("""SELECT    SUM(shares)
                              FROM      main.transactions
                              WHERE     user_id = :uid
                              AND       symbol = :symbol""",

                              uid=user_id, symbol=symbol)[0]

        # User doesn't have that stock or doesn't have enough
        if not owned["SUM(shares)"] or owned["SUM(shares)"] < 1:
            return apology("you don't own that stock", 409)

        elif shares > owned["SUM(shares)"]:
            return apology("you can't sell more than you have", 409)

        # Fix for calculations and display
        shares = -shares

    else:

        # Not enough cash
        if float(total) > cash:
            return apology("not enough cash", 409)

    # Add transaction data to db
    add_transaction(db, company, symbol, action, shares, price, total)

    # Select and update user's cash to reflect purchase
    cash = cash - total
    db.execute("UPDATE main.users SET cash = :cash WHERE id = :uid", uid=session["user_id"], cash=cash)
    session["cash"] = cash

    # Generate data to display on main page
    view_data(db)

    return render_template("index.html", cash=usd(session["cash"]), data=session["totals"], total=session["total"])


def errorhandler(e):
    """Handle error"""

    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)