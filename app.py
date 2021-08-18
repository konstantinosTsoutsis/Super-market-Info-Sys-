from flask.helpers import total_seconds
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from flask import Flask, request, jsonify, redirect, Response
from bson.objectid import ObjectId
import json
import uuid
import time

# Connect to our local MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Choose database
db = client['DSmarkets']

# Choose collections
products = db['Products']
users = db['Users']

# Initiate Flask App
app = Flask(__name__)

users_sessions = {}

def create_session(email):
    user_uuid = str(uuid.uuid1())
    users_sessions[user_uuid] = (email, time.time())
    return user_uuid  

def is_session_valid(user_uuid):
    return user_uuid in users_sessions


# ΕΡΩΤΗΜΑ 1: Δημιουργία χρήστη
@app.route('/createUser', methods=['POST'])
def create_user():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "username" in data or not "password" in data or not "email" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")

    if users.find({"email":data["email"]}).count() == 0 :
        user = {"username": data['username'], "password": data['password'], "email": data['email'], "category": data['category']}
        users.insert_one(user)

        # Μήνυμα επιτυχίας
        return Response(data['username']+" was added to the MongoDB.\n",status = 200, mimetype='application/json') 
    
    # Διαφορετικά, αν υπάρχει ήδη κάποιος χρήστης με αυτό το username.
    else:
        return Response("A user with the given email already exists. \n",status = 400, mimetype='application/json') 
       


# ΕΡΩΤΗΜΑ 2: Login στο σύστημα
@app.route('/login', methods=['POST'])
def login():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data or not "password" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")

    user = users.find_one({"email":data['email']})
    if user == None : 
        return Response("no user with such email \n",status=500,mimetype='application/json')
    if user["password"] == data['password']:
        user_uuid = create_session(data['email'])
        res = {"uuid": user_uuid, "email": data['email']}
        return Response(json.dumps(res , indent=4) + "\n",status = 200, mimetype='application/json') 

    # Διαφορετικά, αν η αυθεντικοποίηση είναι ανεπιτυχής.
    else:
        # Μήνυμα λάθους (Λάθος email ή password)
        return Response("Wrong email or password.\n",status = 400 , mimetype='application/json') 

# ΕΡΩΤΗΜΑ 3: Επιστροφή προιοντος βάσει email 
@app.route('/getProductInfo', methods=['GET'])
def get_ProductInfo():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "answer" in data :
        return Response("Information incomplete",status=500,mimetype="application/json")
    
    uuid = request.headers.get('authorization')
    if is_session_valid(uuid) == False :
        return Response("the user is not authorized \n" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης 
        out = []
        
        if data["answer"] == "_id":
            product = products.find({"_id":ObjectId(data['value'])})
        else:
            product = products.find({data["answer"]:data['value']}) 

        if product == None :
            return Response ("no product with such name \n",status=500,mimetype='application/json')
        else :
            
            for i in product:
                i['_id'] = str(i['_id'])
                del i['stock']
                out.append(i)
                

            return Response(json.dumps(out , indent = 4)+ "\n", status=200, mimetype='application/json')
            
# ΕΡΩΤΗΜΑ 3: Εισαγωγή στο καλαθι βάσει id 
@app.route('/addProducts', methods=['PATCH'])
def add_Products():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "id" in data or not "quantity" in data :
        return Response("Information incomplete",status=500,mimetype="application/json")

    uuid = request.headers.get('authorization')
    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης 

        xrhsths = users_sessions.get(uuid)
        email = xrhsths[0]
        totalCost = 0

        user = users.find_one({'email':email})
        product = products.find_one({"_id":ObjectId(data["id"])})
        if user == None :
            msg = "no user with such email. \n"
            return Response(msg,status=500,mimetype='application/json')
        else :
            #product = products.find_one({"_id":ObjectId(data["id"])})
            if product:
                if int(data['quantity']) <= int(product['stock']):

                    if 'productList' in user:
                        document = user['productList']
                        document.update({ data["id"]: data["quantity"]})
                        users.update_one({'email':email},{"$set": {'productList':document }})
                        msg = "product added to " + user["email"] +".\n"

                    else:
                        users.update_one({'email':email},{"$set": {'productList':{data['id']:data['quantity']}}}) 
                        msg = "product added to " + user["email"] +".\n"
                    prodName = "name of product : \n"
                    for productNumber in user['productList']:
                        productX = products.find_one({"_id":ObjectId(productNumber)})
                        cost = productX["price"]
                        totalCost += int(cost) * int(data['quantity']) 
                        productOut = productX["name"] 
                        prodName += productOut +"\n"
                        
                    price = "total price of cart is :" +str(totalCost)+ "\n"  
                    msg += price + prodName   
                else:
                    msg = "out of stock\n"
            else:
                msg = "No product with such id"
            
            return Response(msg, status=200, mimetype='application/json')
            
            
        
# ΕΡΩΤΗΜΑ 3: Επιστροφή καλαθιου βασει email 
@app.route('/getProductList', methods=['GET'])
def get_ProductList():   
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data :
        return Response("Information incomplete",status=500,mimetype="application/json")

    uuid = request.headers.get('authorization')
    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης 
        productList = users.find_one({"email":data['email']})
        p = productList['productList']
    return Response(json.dumps(p , indent = 4), status=200, mimetype='application/json')

#diagrafh ap to kala8i
@app.route('/delete_product_from_cart', methods=['DELETE'])
def delete_product_from_cart():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "id" in data :
        return Response("Information incomplete",status=500,mimetype="application/json")


    uuid = request.headers.get('authorization')
    xrhsths = users_sessions.get(uuid)
    email = xrhsths[0]
    totalCost = 0

    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης

        user = users.find_one({'email':email})
        product = products.find_one({"_id":ObjectId(data["id"])})
        if user == None :
            msg = "no user with such email. \n"
            return Response(msg,status=500,mimetype='application/json')
        else:
            if product:
                if 'productList' in user:
                    #pass product List in var document
                    document = user['productList']
                    #delete specific product from the cart
                    if document[data["id"]]:

                        del document[data["id"]]
                        users.update_one({'email':email},{"$set": {'productList':document }})
                        msg = "product deleted from " + user["email"] +".\n"
                    else:
                        msg="no such product in cart"
                else:
                    msg="No cart found \n"
            else:
                msg="Product not found \n"    
            user = users.find_one({'email':email})
            prodName = "name of product : \n"    
            for productNumber in user['productList']:

                productX = products.find_one({"_id":ObjectId(productNumber)})
                cost = productX["price"]
                quan = user['productList'].get(productNumber)
                totalCost += int(cost) * int(quan)
                productOut = productX["name"] 
                prodName += productOut +"\n"   
            price = "total price of cart is :" +str(totalCost)+ "\n"  
            msg += price + prodName   
        return Response(msg, status=200, mimetype='application/json')
                    




#Αγορά προιόντος 
@app.route('/Buy', methods=['PATCH'])
def Buy():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "cartNumber" in data :
        return Response("Information incomplete",status=500,mimetype="application/json")


    uuid = request.headers.get('authorization')
    xrhsths = users_sessions.get(uuid)
    email = xrhsths[0]
    totalCost = 0

    

    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης

        user = users.find_one({'email':email})
        #περασμα του καλαθιού στην μεταβλητη productCart
        buy = user['productList'].copy()
      
        if len(data['cartNumber']) == 16:

            if 'buy' in user:
                    document = user['buy']
                    document.update(user['productList'])
                    users.update_one({'email':email},{"$set": {'buy':document }})
                    msg = "the products were purchased.\n"
                    EmptyCart = {}
                    users.update_one({'email':email},{"$set": {'productList':EmptyCart }})
            else:
                    users.update_one({'email':email},{"$set": {'buy':user['productList']}})
                    msg = "the products were purchased.\n"
                    EmptyCart = {}
                    users.update_one({'email':email},{"$set": {'productList':EmptyCart }})  
                   
            
              

            prodName = "name of product      quantity       price\n"
            for productNumber in user['buy']:
                        productX = products.find_one({"_id":ObjectId(productNumber)})
                        cost = productX["price"]
                        quan = user['buy'].get(productNumber)
                        printCost = int(cost) * int(quan)
                        totalCost += int(cost) * int(quan)
                        productOut = productX["name"] 
                        prodName += productOut +"                 " + quan +"       " +str(printCost) +"\n"

            price = "total price of cart is :" +str(totalCost)+ "\n" 
            msg += price + prodName

        else:
            msg = "Card is not valid \n"            

    return Response(msg, status=200, mimetype='application/json')
            
@app.route('/getTransactionHistory', methods=['GET'])
def getTransactionHistory():           
        
        uuid = request.headers.get('authorization')
        xrhsths = users_sessions.get(uuid)
        email = xrhsths[0]    
       
        if is_session_valid(uuid) == False :
            return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
        else : #αυθεντικοποιηση αληθης 
            
            buyList = users.find_one({"email":email})
            p = buyList['buy']
        return Response(json.dumps(p , indent = 4), status=200, mimetype='application/json')

@app.route('/deleteUser', methods=['DELETE'])
def delete_user():
    uuid = request.headers.get('authorization')
    xrhsths = users_sessions.get(uuid)
    email = xrhsths[0]

    
    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης 
        user = users.find_one({"email":email})
        if user == None:
            msg = "no user found \n"
        else :
            users.delete_one(user)
            msg = user["username"] + " was deleted. \n"
        return Response(msg, status=200, mimetype='application/json')        
#--------------------------------------------------------------------------------------------------
#                           ADMIN
@app.route('/addNewProduct', methods=['POST'])
def add_New_Products():
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "name" in data or not "category" in data or not "stock" in data or not "description" in data or not "price" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")
    
    uuid = request.headers.get('authorization')
    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης 

        xrhsths = users_sessions.get(uuid)
        email = xrhsths[0]
        user = users.find_one({'email':email})
        #ελεγχος για το αν ειναι admin
        if user['category'] == 'admin':

            document = {"name": data['name'], "category": data['category'], "stock": data['stock'], "description": data['description'], "price": data['price']}
            products.insert_one(document)
            msg = "New product added to DS Market store.\n"
        else:
            msg = "Permission denied.\nThis action is only available for admins.\n"

        return Response(msg, status=200, mimetype='application/json')


@app.route('/delete_product', methods=['DELETE'])
def delete_product():
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "id" in data :
        return Response("Information incomplete",status=500,mimetype="application/json")

    uuid = request.headers.get('authorization')
    xrhsths = users_sessions.get(uuid)
    email = xrhsths[0]
    user = users.find_one({'email':email})

    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης
        if user['category'] == 'admin':

            product = products.find_one({"_id":ObjectId(data["id"])})
            if product:
                    products.delete_one(product)
                    
                    msg = product["name"]+" was deleted .\n"
            
                    
            else:
                msg = "Product not found.\n"
        return Response(msg, status=200, mimetype='application/json')        

#ενημέρωση προιόντος
@app.route('/ProductUdate', methods=['PATCH'])
def ProductUdate():

    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "id" in data :
        return Response("Information incomplete",status=500,mimetype="application/json")

    uuid = request.headers.get('authorization')
    xrhsths = users_sessions.get(uuid)
    email = xrhsths[0]

    if is_session_valid(uuid) == False :
        return Response("the user is not authorized" , status=401 ,mimetype='application/json' )
    else : #αυθεντικοποιηση αληθης
        user = users.find_one({'email':email})
        product = products.find_one({"_id":ObjectId(data["id"])})
        msg = "UPDATES : \n"
        if user['category'] == 'admin':
            if user == None :
                msg = "no user with such email. \n"
                return Response(msg,status=500,mimetype='application/json')
            else:
                if product:
                    if 'name' in data :
                        products.update_one({"_id":ObjectId(data["id"])},{"$set" : {'name': data['name']}})
                        msg += "Name has been changed.\n"

                    if 'category'  in data:
                        products.update_one({"_id":ObjectId(data["id"])},{"$set" : {'category': data['category']}})
                        msg += "Category has been changed.\n"

                    if 'stock' in data:
                        products.update_one({"_id":ObjectId(data["id"])},{"$set" : {'stock': data['stock']}})
                        msg += "Stock has been changed.\n"

                    if 'description' in data:
                        products.update_one({"_id":ObjectId(data["id"])},{"$set" : {'description': data['description']}})
                        msg += "Description has been changed.\n"
                        
                    if 'price' in data:
                        products.update_one({"_id":ObjectId(data["id"])},{"$set" : {'price': data['price']}})    
                        msg += "Price has been changed.\n"
        else:
            msg = "Permission denied.\nThis action is only available for admins.\n"
        return Response(msg, status=200, mimetype='application/json')




#get all users from User collection
@app.route('/getallusers', methods=['GET'])
def get_all_users():
    iterable = users.find({})
    output = []
    for user in iterable:
        user['_id'] = str(user['_id'])
        output.append(user)
    return jsonify(output)

#get all products from Products collection
@app.route('/getallproducts', methods=['GET'])
def get_all_products():
    iterable = products.find({})
    output = []
    for product in iterable:
        
        product['_id'] = str(product['_id'])
        output.append(product)
    return jsonify(output)    

#proion
@app.route('/addLol', methods=['POST'])
def add_New_ProductsLOL():
    products.insert_one ({"_id" : "5e99cb577a781a4aac69da32" , "name": "makaronia", "category": "pasta", "stock": "3", "description": "eykolo mageirema", "price": "3"})
    msg = "ok"
    return Response(msg, status=200, mimetype='application/json')
# Εκτέλεση flask service σε debug mode, στην port 5000. 
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 