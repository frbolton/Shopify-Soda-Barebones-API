import flask
from flask import *
import sqlite3

app = flask.Flask(__name__)
app.config["DEBUG"] = True


def convertToDict(cursor, row):
	'''Creates dictionary from database rows which will be retrieved using sqlite3. Makes json product list output a little more readable.'''
	prodDict = {}
	for item, column in enumerate(cursor.description):
		prodDict[column[0]] = row[item]
	return prodDict

@app.route('/shopify', methods =['GET'])
def landingPage():
	return "This is a barebones API for perusing by Shopify recruiters. Enjoy!"

@app.route('/shopify/products', methods=['GET'])
def displayProducts():
	'''Establishes connection to database and returns all rows in json format'''
	available = request.args.get('available')
	connection = sqlite3.connect('products.db') #connection to the db must be created in each function because SQLite objects created in a thread can only be used in that thread
	connection.row_factory = convertToDict
	cursor = connection.cursor() #creates cursor object which can be thought of as the "hand" that will look through our database
	if available=="": #argument can be added to query only for items in stock
		productList = cursor.execute('SELECT * FROM products WHERE inventory_count > 0').fetchall()
	else:
		productList = cursor.execute('SELECT * FROM products;').fetchall()
	return jsonify(productList)


#curl -X POST "http://127.0.0.1:5000/shopify/products/purchaseItem?productTitle=Pepsi&qty=3"
@app.route('/shopify/products/purchaseItem', methods=['POST'])
def purchaseItem():
	'''"Purchase" items directly from the database in specified quantities without going through the cart. Products out of stock cannot be purchased. 
	If the request argument specifies a higher quantity than what is in stock, the purchase is not completed. Has basic error handling for invalid arguments.'''
	productTitle = request.args.get('productTitle')
	qty = request.args.get('qty')
	connection = sqlite3.connect('products.db')
	cursor = connection.cursor()
	try:
		inventoryCount = cursor.execute("SELECT inventory_count FROM products WHERE title = ?", (productTitle,)).fetchone()[0]
		if inventoryCount > 0 and str(qty) == "all":
			cursor.execute("UPDATE products SET inventory_count = 0 WHERE title = ?", (productTitle,))
		elif inventoryCount > 0 and qty != None and int(qty) <= inventoryCount:
			cursor.execute("UPDATE products SET inventory_count = inventory_count-? WHERE title = ?", (qty, productTitle,))
		elif inventoryCount > 0 and qty == None:
			cursor.execute("UPDATE products SET inventory_count = inventory_count-1 WHERE title = ?", (productTitle,))
		productList = cursor.execute('SELECT * FROM products;').fetchall()
		connection.commit()
		return jsonify(productList)
	except:
		return jsonify("An error has occurred and the request could not be completed (most likely invalid product name).")
	

cart = [0] #creates cart as a list containing only one index with value of 0, which we will use to manipulate total dollar amount in the cart. Because this API isn't really secure
#and doesn't use session keys, there is also only one cart available at a time. I call this the People's Cart.

@app.route('/shopify/products/viewCart', methods=['GET'])
def viewCart():
	'''Simple function to view cart contents'''
	if cart[0] == 0:
		return jsonify("The cart is empty.")
	else:
		return jsonify(cart)

@app.route('/shopify/products/addToCart', methods=['POST'])
def addToCart():
	'''Adds items to the cart by matching request argument with database entry title. Adds price amount of queried item to the total. Only one of a given item may be added to the cart.
	Quantity is not adjustable.'''
	try:
		connection = sqlite3.connect('products.db')
		cursor = connection.cursor()
		productTitle = request.args.get('productTitle')
		selectedItem = cursor.execute('SELECT title, price FROM products WHERE title=?', (productTitle,)).fetchone()
		priceAmount = cursor.execute('SELECT price FROM products WHERE title = ?', (productTitle,)).fetchone()[0]
		if selectedItem not in cart:
			cart[0] += priceAmount #we use the first element in the cart, the aforementioned 0, as reference to calculate our total when the first item is added
			cart.append(selectedItem)
		return jsonify(cart)
	except:
		return jsonify("An error has occurred (most likely invalid product name).")

@app.route('/shopify/products/removeFromCart', methods=['POST'])
def removeFromCart():
	'''Removes items from the cart and adjusts price accordingly. Only one item may be removed from the cart at a time (in a single request).'''
	try:
		connection = sqlite3.connect('products.db')
		cursor = connection.cursor()
		productTitle = request.args.get('productTitle')
		selectedItem = cursor.execute('SELECT title, price FROM products WHERE title=?', (productTitle,)).fetchone()
		itemPrice = cursor.execute('SELECT price FROM products WHERE title=?', (productTitle,)).fetchone()[0]
		if selectedItem in cart:
			cart[0] -= itemPrice
			cart.remove(selectedItem)
			return viewCart()
		else:
			return jsonify(f"There was no {productTitle} in your cart!")
	except:
		return jsonify("An error has occurred (most likely invalid product name).")

@app.route('/shopify/products/dumpCart', methods=['POST'])
def dumpCart():
	'''Removes all items in the cart and resets total amount to 0.'''
	connection = sqlite3.connect('products.db')
	cursor = connection.cursor()
	for i in range(0, len(cart)):
		cart.remove(cart[0])
	cart.append(0)
	return viewCart()

@app.route('/shopify/products/checkout', methods =['POST'])
def checkout():
	'''Reads items in the cart and matches them to database entries. The selected rows are then updated to lower inventory count by one (the cart only allows qty=1 for any item).
	Changes to the database are committed only when checking out through this method when using the cart.'''
	connection = sqlite3.connect('products.db')
	cursor = connection.cursor()
	for i in range(1, len(cart)):
		productTitle = cart[i][0]
		inventoryCount = cursor.execute("SELECT inventory_count FROM products WHERE title = ?", (productTitle,)).fetchone()[0]
		if inventoryCount > 0:
			cursor.execute("UPDATE products SET inventory_count = inventory_count-1 WHERE title = ?", (productTitle,))
	productList = cursor.execute('SELECT * FROM products;').fetchall()
	connection.commit()
	dumpCart()
	return jsonify(productList)

app.run()