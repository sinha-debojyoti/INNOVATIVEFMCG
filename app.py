import pickle
from math import radians, sin, cos, acos

import mysql.connector
from flask import Flask, render_template, request, session
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from passlib.hash import sha256_crypt
import os

import pathlib

def get_ssl_cert():
    current_path = pathlib.Path(__file__).parent.parent
    return str(current_path / 'BaltimoreCyberTrustRoot.crt.pem')

# Database Connection
mydb = mysql.connector.connect(
    host=os.environ.get("host"),
    user=os.environ.get("user"),
    passwd=os.environ.get("passwd"),
    database=os.environ.get("database"),
    ssl_ca="BaltimoreCyberTrustRoot.crt.pem"
)

# mydb = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     passwd="root",
#     database="database"
# )

app = Flask(__name__)

# Creating the secret Key For Session For Storing Session Value
app.secret_key = "FPH_FMCG"

#Index Page
@app.route('/')
def index():
    return render_template("index.html")

# Search Product
@app.route('/search_items')
def search_items():

    # For Fetching products from the database
    mycursor = mydb.cursor()
    sql = """
                SELECT pd.`Product Name`
                FROM product_details pd;"""
    mycursor.execute(sql)
    products = mycursor.fetchall()

    # Return product list to search page
    return render_template("search.html", products=products)


@app.route("/search_items_process", methods=["POST"])
def search_items_process():
    #Data from form

    # For getting selected product name
    item_name = request.form.get("item_name")

    #For getting latitude
    latitude = request.form.get("send_latitude")

    # For getting longitide
    longitude = request.form.get("send_longitude")

    #if Geotracking not working return defalt longitude and latitude location
    if latitude == None or longitude == None:
        latitude = 22.698038
        longitude = 88.38031

    # SQL for fetching Shop Name, Shop ID, Shop location(longitude and latitude), Product Quantity, Product Selling Price
    mycursor = mydb.cursor()
    sql = """
        SELECT sd.shop_name, ps.quantity, ps.selling_price, sd.latitude, sd.longitude, ps.shop_id, sd.contact
        FROM product_stocks ps
            JOIN shop_details sd on ps.shop_id = sd.shop_id
            JOIN product_details pd on ps.`S.N.` = pd.BARCODE
        WHERE pd.`Product Name` = %(item_name)s
        ORDER BY ps.selling_price;"""
    mycursor.execute(sql, {'item_name': item_name})
    shop_list = mycursor.fetchall()

    # For counting number of shop
    shop_avail = len(shop_list)

    # Zero Shops present return No shop Found
    if shop_avail == 0:
        return render_template("message.html", message="No Shop Found")

    # Creating a Modified Shop details with rating and distance from the user.
    shop_list_mod = []

    if (shop_avail > 0):

        # SQL Code for Fetching product ID by providing Product Name
        mycursor = mydb.cursor()
        sql = """
                SELECT pd.BARCODE
                FROM product_details pd
                WHERE pd.`Product Name`= %(product_name)s;"""
        mycursor.execute(sql, {'product_name': item_name})
        product_id = mycursor.fetchone()
        product_id = product_id[0]

        # SQL code for product rating for a particular product 0 - Negative, 1 - Neutral, 3 - Positive
        mycursor = mydb.cursor()
        sql = """
                SELECT avg(pr.product_rating)
                FROM product_review pr
                WHERE pr.barcode = %(product_id)s
                GROUP BY pr.barcode;"""
        mycursor.execute(sql, {'product_id': product_id})
        pdreview = mycursor.fetchone()
        pdreview = pdreview[0]

        # For setting product rating to Positive, Neutral, Negative
        pdreview_comment = "Neutral"
        if pdreview <= 1.0:
            pdreview_comment = "Negative"
        elif pdreview <= 2.0:
            pdreview_comment = "Neutral"
        elif pdreview <= 3.0:
            pdreview_comment = "Good"

        for x in shop_list:

            # For Converting tuple to List
            x = list(x)

            # For getting shop id
            shop_id = x[5]

            # SQL code for shop rating for a particular product 0 - Negative, 1 - Neutral, 3 - Positive
            mycursor = mydb.cursor()
            sql = """
                    SELECT avg(sr.shop_rating)
                    FROM shop_review sr
                    WHERE sr.shop_id = %(shop_id)s
                    GROUP BY sr.shop_id;"""
            mycursor.execute(sql, {'shop_id': shop_id})
            review = mycursor.fetchone()
            review = float(review[0])

            # For setting product rating to Positive, Neutral, Negative
            review_comment = "Neutral"
            if review <= 1.0:
                review_comment = "Negative"
            elif review <= 2.0:
                review_comment = "Neutral"
            elif review <= 3.0:
                review_comment = "Good"

            # Add shop review to the Result
            x.append(review_comment)

            #Calculating distance between two points
            slat = radians(x[3])
            slon = radians(x[4])
            elat = radians(latitude)
            elon = radians(longitude)
            dist = 6371.01 * acos(sin(slat) * sin(elat) + cos(slat) * cos(elat) * cos(slon - elon))
            dist = round(dist, 2)

            # Add distance to the Result
            x.append(dist)

            # Add complete result to the modified shop list
            shop_list_mod.append(x)

    #Delete Old shop List
    del shop_list

    return render_template("items_search_result.html", shop_list=shop_list_mod, shop_avail=shop_avail,
                           item_name=item_name, pdreview_comment=pdreview_comment)


@app.route("/shop_login")
def shop_login():
    # Redirecting to the shop Login Page
    return render_template("shop_login.html")


@app.route("/shop_login_process", methods=["POST"])
def shop_login_process():

    # Getting Shop Id and Password from the form
    shop_id = request.form.get("shop_id")
    password = request.form.get("password")

    # SQL Command for fetching shop_id and password
    mycursor = mydb.cursor()
    sql = """
        SELECT shop_details.shop_id, shop_details.pasword
        FROM shop_details
        WHERE shop_details.shop_id = %(shop_id)s;"""
    mycursor.execute(sql, {'shop_id': shop_id, 'password': password})
    result = mycursor.fetchone()

    # Return If No Result Found
    if result == None:
        return render_template("shop_login.html", message="Wrong Shop ID or Password")

    passfmdb = result[1]

    # Converting password to SHA256
    password = sha256_crypt.encrypt(password)

    # Password Doesn't Match
    if sha256_crypt.verify(passfmdb, password) == False:
        return render_template("shop_login.html", message="Wrong Shop ID or Password")

    # Password Match store shop_id in cookies.
    session['shop_id'] = shop_id

    # redirect to Shop Option
    return render_template("shop_option.html", shop_id=shop_id)


@app.route("/shop_main_page")
def shop_main_page():
    return render_template("shop_option.html", shop_id=session["shop_id"])


@app.route("/store_inventory")
def store_inventory():

    #MySql Code for fetching Product Name, Quantity and Selling Price
    mycursor = mydb.cursor()
    sql = """
            SELECT pd.`Product Name`, ps.quantity, ps.selling_price
            FROM product_stocks ps
                     JOIN product_details pd on ps.`S.N.` = pd.BARCODE
            WHERE ps.shop_id = %(shop_id)s;"""
    mycursor.execute(sql, {'shop_id': session["shop_id"]})
    shop_list = mycursor.fetchall()

    # Calculate number of Product
    shop_avail = len(shop_list)

    # Return Invetory Page.
    return render_template("display_inventory.html", shop_id=session["shop_id"], shop_list=shop_list,
                           shop_avail=shop_avail)


@app.route("/update_prices")
def update_prices():

    # MySql Code to Fetch Product from a particular shop.
    mycursor = mydb.cursor()
    sql = """
            SELECT pd.`Product Name`
            FROM product_stocks ps
                JOIN product_details pd on ps.`S.N.` = pd.BARCODE
                JOIN shop_details sd on ps.shop_id = sd.shop_id
            WHERE ps.shop_id = %(shop_id)s;"""
    mycursor.execute(sql, {'shop_id': session["shop_id"]})
    products = mycursor.fetchall()

    # Redirect to update page
    return render_template("update_prices.html", shop_id=session['shop_id'], products=products)


@app.route("/update_price_process", methods=["POST"])
def update_price_process():

    # MySql for Fetching current Selling Price.
    product_name = request.form.get("product")
    mycursor = mydb.cursor()
    sql = """
            SELECT ps.selling_price, pd.MRP, pd.weight, pd.cream
            FROM product_stocks ps
                JOIN product_details pd on ps.`S.N.` = pd.BARCODE
                JOIN shop_details sd on ps.shop_id = sd.shop_id
            WHERE pd.`Product Name` = %(product_name)s
                AND ps.shop_id = %(shop_id)s;"""
    mycursor.execute(sql, {'product_name': product_name, 'shop_id': session['shop_id']})
    curr_price = mycursor.fetchone()

    # Getting MRP, Weight, Has Cream parameter for the biscuits.
    MRP = curr_price[1]
    WEIGHT = curr_price[2]
    CREAM = curr_price[3]

    # Preparing data for for Machine Learning Model
    result = []
    if (CREAM == 'YES'):
        result.append(MRP)
        result.append(WEIGHT)
        result.append(0)
        result.append(1)
    elif (CREAM == 'NO'):
        result.append(MRP)
        result.append(WEIGHT)
        result.append(1)
        result.append(0)

    # Loading Machine Learning Model
    with open('model_pickle', 'rb') as file:
        mp = pickle.load(file)

    # Predict Price for the product.
    pred_sp = mp.predict([result])
    pred_sp = round(pred_sp[0], 2)

    # If Predict Selling price more than MRP then setting Selling pring Price ToMRP
    if (pred_sp > MRP):
        pred_sp = MRP

    # Return Predicted Price
    return render_template("update_prices_data.html", shop_id=session['shop_id'], curr_price=curr_price,
                           product_name=product_name, pred_sp=pred_sp)


@app.route("/update_price_to_db", methods=["POST"])
def update_price_to_db():

    #Get Updated Price, Update Quantity and product Name from the form
    update_price = request.form.get("update_price")
    update_quantity = request.form.get("update_quantity")
    product_name = request.form.get("product")

    #MySql Code For Updating Price, Quantity for particular product.
    mycursor = mydb.cursor()
    sql = """
               UPDATE product_stocks ps
                SET ps.selling_price = %(update_price)s,
                    ps.quantity = %(update_quantity)s
                WHERE ps.`S.N.` = (SELECT pd.BARCODE
                                   FROM product_details pd
                                   WHERE pd.`Product Name` = %(product_name)s)
                  AND ps.shop_id = %(shop_id)s;"""
    mycursor.execute(sql,
                     {'product_name': product_name, 'update_price': update_price, 'update_quantity': update_quantity,
                      'shop_id': session['shop_id']})
    mydb.commit()

    # Redirect to shop Option.
    return render_template("shop_option.html", shop_id=session['shop_id'], message="Updated Successfully.")

# Shopkeeper logout Code
@app.route("/shop_login_logout")
def shop_login_logout():
    # Deleting shop id from cookies.
    session.pop("shop_id", None)
    return render_template("message.html", message="Logout Successfully")


@app.route("/reviews_option")
def reviews_option():
    return render_template("reviews_option.html")


@app.route("/product_review")
def product_review():

    # MySql Code for Fetching Product Name
    mycursor = mydb.cursor()
    sql = """
            SELECT pd.`Product Name`
            FROM product_details pd;"""
    mycursor.execute(sql)
    products = mycursor.fetchall()

    # Redirect to Product Review Section.
    return render_template("product_reviews_option1.html", products=products)


@app.route("/product_reviews_process", methods=["POST"])
def product_reviews_process():

    # Fetching product Name, review from the form
    product_name = request.form.get("product")
    reviews = request.form.get("reviews")

    # MySQL for product barcode
    mycursor = mydb.cursor()
    sql = """
                SELECT pd.BARCODE
                FROM product_details pd
                WHERE pd.`Product Name`=%(product_name)s;"""
    mycursor.execute(sql, {'product_name': product_name})
    products_id = mycursor.fetchone()

    # NLP Based Library to classify review as positive, negative or neutral
    sid = SentimentIntensityAnalyzer()
    score = sid.polarity_scores(reviews)
    product_rating = 1
    if score['compound'] >= 0.05:
        product_rating = 3
    elif score['compound'] <= -0.05:
        product_rating = 1
    else:
        product_rating = 2

    # Storing product review to the database
    mycursor = mydb.cursor()
    sql = """INSERT INTO product_review (barcode, product_rating) VALUES (%(products_id)s, %(product_rating)s);"""
    mycursor.execute(sql,
                     {'product_rating': product_rating, 'products_id': products_id[0]})
    mydb.commit()

    return render_template("message.html", message="Review Added")


@app.route("/shop_review")
def shop_review():

    #MySQL for fetching Store Data.
    mycursor = mydb.cursor()
    sql = """
                SELECT sd.shop_name
                FROM shop_details sd;"""
    mycursor.execute(sql)
    shops = mycursor.fetchall()

    return render_template("shop_reviews_option1.html", shops=shops)


@app.route("/shop_reviews_process", methods=["POST"])
def shop_reviews_process():

    #Fetching Shop Name and reviews from the form
    shop_name = request.form.get("shop")
    reviews = request.form.get("reviews")

    #MySQL code for fetching shop ids.
    mycursor = mydb.cursor()
    sql = """
                SELECT sd.shop_id
                FROM shop_details sd
                WHERE sd.shop_name =%(shop_name)s;"""
    mycursor.execute(sql, {'shop_name': shop_name})
    shop_id = mycursor.fetchone()

    # NLP based reviews system classify it as positive, negative, neutral
    sid = SentimentIntensityAnalyzer()
    score = sid.polarity_scores(reviews)
    shop_rating = 1
    if score['compound'] >= 0.05:
        shop_rating = 3
    elif score['compound'] <= -0.05:
        shop_rating = 1
    else:
        shop_rating = 2

    # Insert shop review data to the data
    mycursor = mydb.cursor()
    sql = """INSERT INTO shop_review (shop_id, shop_rating) VALUES (%(shop_id)s, %(shop_rating)s);"""
    mycursor.execute(sql,
                     {'shop_rating': shop_rating, 'shop_id': shop_id[0]})
    mydb.commit()

    return render_template("message.html", message="Review Updated.")


app.debug = True
app.run()
app.run(debug=True)