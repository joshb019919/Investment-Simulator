import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def add_transaction(db, company, symbol, action, shares, price, total):
    """Adds user's transaction to database."""

    # Insert purchase/sale data into user's transaction history
    db.execute("""INSERT INTO main.transactions
                  (user_id, company, symbol, action, shares, price, value)

                  VALUES
                  (:uid, :company, :symbol, :action, :shares, :price, :value)""",

                  uid=session["user_id"], company=company, symbol=symbol,
                  action=action, shares=shares, price=price, value=total)


def apology(message, code=400):
    """Render message as an apology to user.
    From Distribution.
    """

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """

        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message))


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    From Distribution.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol.
    From Distribution.
    """

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")

        # API_KEY given as query parameter for easier testing.  Would be removed in production.
        response = requests.get(f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token=pk_be7cd775263e47688098391df4327827")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def set_data(db):
    """Adds user data to session."""

    # Select user data
    user_id = session["user_id"]
    session["username"] = db.execute("SELECT username FROM users WHERE id = :uid", uid=user_id)[0]["username"]
    session["cash"] = db.execute("SELECT cash FROM main.users WHERE id = :user_id", user_id=user_id)[0]["cash"]


def usd(value):
    """Format value as USD.
    From Distribution.
    """
    return f"${value:,.2f}"


def validate(username=None, password=None, symbol=None, shares=None, login=False, trade=False):
    """To validate login, set login=true; to validate transaction, set trade=true."""

    if login == True:

        # User left username blank
        if not username:
            return apology("must provide username", 403)

        # User left password blank
        elif not password:
            return apology("must provide password", 403)

    elif trade == True:

        if not symbol == "Select Symbol" and not symbol == "------------":

            # User left a symbol blank
            if not symbol:
                return apology("must enter symbol", 408)

            # User left shares blank
            elif not shares:
                return apology("must buy complete shares - at least one", 408)

            # User entered something other than a positive integer
            elif not shares.isdigit() or int(shares) < 1:
                return apology("shares must be a positive whole number", 408)

            # Safe to convert shares to integer
            else:
                return int(shares)


def view_data(db):
    """Assign to session the data to be displayed to user."""

    user_id = session["user_id"]

    # Data to be displayed
    total = 0
    session["totals"] = db.execute("""SELECT    company, symbol, SUM(shares)
                                      FROM      main.transactions
                                      WHERE     user_id = :uid
                                      GROUP BY  symbol
                                      HAVING    SUM(shares) >= 1""",

                                      uid=user_id)

    # User has transactions
    if session["totals"]:

        # Calculate and add price and value columns
        for symbol in session["totals"]:
            price = lookup(symbol["symbol"])["price"]
            symbol["price"] = "${}".format(price)
            value = price * symbol["SUM(shares)"]
            total += value
            symbol["value"] = "${:.2f}".format(value)

        session["total"] = total
        session["grand_total"] = total + session["cash"]

    else:
        session["total"] = 0