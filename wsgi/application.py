#!/usr/bin/env python

import os, pymongo, json, hashlib, bson
from bson.json_util import dumps as mongo_dumps
from bottle import Bottle, request, response, HTTPResponse

from db import get_database_connection

from auth import auth_app, jwt_required, admin_required, authenticate
from bottle import route,run
from bson.objectid import ObjectId
from datetime import datetime

application = Bottle()
app = application
app.merge(auth_app)

# atender requisicoes do tipo get para /
@app.get('/')
def index():
	return "Boa sorte!"

# atender requisicoes do tipo post para /api/v1/signin
# curl -H "Content-Type: application/json" -X POST -d '{"email":"scott@gmail.com", "password":"12345"}' http://localhost:8080/api/v1/signin
@app.post('/api/v1/signin')
def login():
	data = request.json
	encoded = authenticate(data['email'], data['password'])
	if encoded:
		return encoded
	else:
		return HTTPResponse(status=401, body="Nao autorizado.")

# atender requisicoes do tipo post para /api/v1/users/create
# curl -i -H "Content-Type: application/json" -X POST -d '{"name": "Eduardo", "email": "xyz@gmail", "password":"xyz"}' http://localhost:8080/api/v1/users/create
@app.post('/api/v1/users/create')
def create_user():
	print("lala");
	response.content_type='application/json'
	data = request.json
	name = data["name"] # obtem nome enviado por parametro postado.
	email = data["email"] # obtem email enviado por parametro postado.
	password = hashlib.md5(data["password"].encode()).hexdigest() # obtem hash md5 da senha enviada.
	db = get_database_connection() # conecta com a base de dados e armazena a conexao em db.
	user = db.users.find_one({'email': email}) # find_one retorna um documento,
											   # ou None se nao encontrar nenhum.
	if user:
		# usuario ja existe. retornar em formato JSON padrao com mensagem.
		return json.dumps({'success': True, 'msg': 'Usuário já existente.'})
	else:
		# usuario nao existe. inserir novo usuario.
		db.users.insert({'name': name, 'email': email, 'password': password,'is_admin':True})
		# retornar em formato JSON padrao com mensagem.
		return json.dumps({'success': True, 'msg': 'Usuário cadastrado.'})


# atender requisicoes do tipo get para /api/v1/users
# curl -i -H "Content-Type: application/json" -X GET  http://localhost:8080/api/v1/users
@app.get('/api/v1/users')
@jwt_required
def list_user(user):
	response.content_type='application/json'
	db = get_database_connection() # conecta com a base de dados e armazena a conexao em db.
	users = db.users.find()
	return mongo_dumps(users)


# atender requisicoes do tipo get para /api/v1/admin/users
# curl -i -H "Content-Type: application/json" -X GET  http://localhost:8080/api/v1/admin/users
@app.get('/api/v1/admin/users')
@admin_required
def list_user_from_admin(user):
	response.content_type='application/json'
	db = get_database_connection() # conecta com a base de dados e armazena a conexao em db.
	users = db.users.find()
	return mongo_dumps(users)


#******* EDIÇÃO DO USUÁRIO ***************
@app.post('/api/v1/user/<user_id>/edit')
@jwt_required
def edit_user(user,user_id):
	response.content_type = 'application/json'
	data = request.json

	if(not "name" in data or not data["name"]):
		return json.dumps({'success': False, 'msg': 'Name is required'})
	if(not "email" in data or not data["email"]):
		return json.dumps({'success': False,'msg':'E-mail is required'})

	name = data["name"]
	email = data["email"]

	db = get_database_connection()  # conecta com a base de dados e armazena a conexao em db.

	if (user["id"] == user_id):
		db.users.update({"_id": ObjectId(user_id)}, {"$set": {'name': name, 'email': email}})
		db.orders.update({"user.id": str(user_id)}, {"$set": {'user.name': name, 'user.email': email}},multi=True)

		return json.dumps({'success': True, 'msg': 'Usuário alterado.'})
	else:
		return json.dumps({'success': False, 'msg': 'Identificadores dos usuários não conferem.'})

#******* FIM EDIÇÃO DO USUÁRIO ***********
#*****************************************


#******* ALTERAÇÃO DE SENHA ***************
@app.post('/api/v1/user/<user_id>/change_password')
@jwt_required
def change_password(user,user_id):
	response.content_type = 'aplication/json'
	data = request.json

	if (not "password" in data or not data["password"]):
		return json.dumps({'success': False, 'msg': 'password is required'})
	if (not "new_password" in data or not data["new_password"]):
		return json.dumps({'success': False, 'msg': 'new password is required'})

	password =  hashlib.md5(data["password"].encode()).hexdigest()
	new_password = hashlib.md5(data["new_password"].encode()).hexdigest()

	db = get_database_connection()

	if (user["id"] == user_id):
		#checa a senha do usuário
		user_valid = db.users.find_one({"_id": ObjectId(user_id), 'password': password})

		if user_valid:
			db.users.update({"_id":ObjectId(user_id)},{"$set":{"password":new_password}})
			return json.dumps({"success":True,"msg":"Senha alterada com sucesso"})
		else:
			return json.dumps({"success":False,"msg":"Senha incorreta"})
	else:
		return json.dumps({'success': False, 'msg': 'Identificadores dos usuários não conferem.'})
#******* FIM ALTERAÇÃO DE SENHA ***********
#******************************************


#******* RETORNA ITENS DO MENU ***************
@app.get('/api/v1/menu/items')
def list_menu_item():
	response.content_type = 'application/json'

	db = get_database_connection()

	items = db.menu_items.find().sort("name_session",pymongo.ASCENDING)

	items_session = {}
	session_controle = ""
	items_retorno = []
	cont = 0;

	if items:
		for item in items:
			key = item["name_session"]

			if session_controle != key and cont > 0:
				items_retorno.append({session_controle:items_session[session_controle]})

			if (not key in items_session):
				items_session[key] = []
			items_session[key].append({'name':item['name'], 'price':item['price']})
			cont = cont+1
			session_controle = key

		items_retorno.append({session_controle: items_session[session_controle]})

	return json.dumps({"success": True, "items": items_retorno})
#******* FIM RETORNA ITENS DO MENU***********
#********************************************


#******* CRIA PEDIDO USUARIO ****************
@app.post('/api/v1/user/<user_id>/orders/create')
@jwt_required
def create_order(user,user_id):
	response.content_type = 'application/json'
	data = request.json
	if (user["id"] == user_id):

		if not len(data) > 0:
			return json.dumps({'success': False, 'msg': 'Necessário pelo menos um item.'})

		items = data
		db = get_database_connection()

		date_now = datetime.now()
		total = 0.0

		for item in items:
			total += item['price']

		db.orders.insert({
			"date": date_now,
			"total": total,
			"user":user,
			"items": items
		})

		return json.dumps({"success":True, "msg":"Pedido criado com sucesso"})
	else:
		return json.dumps({'success': False, 'msg': 'Identificadores dos usuários não conferem.'})
#******* FIM CRIA PEDIDO USUARIO ************
#********************************************


#******* EXIBE PEDIDOS USUARIO ****************w
@app.get('/api/v1/user/<user_id>/orders')
@jwt_required
def list_order(user,user_id):
	if (user["id"] == user_id):
		db = get_database_connection()
		listOrders = db.orders.find({"user.id": user_id},{"date":1, "total":1})
		if listOrders._Cursor__empty :
			return json.dumps({'success': False, 'msg': 'Não existem pedidos para o usuario ' + user + "."})
		else:
			arrayRetorno = []
			for item_list in listOrders:
				arrayRetorno.append({"id":str(item_list["_id"]),"date":str(item_list["date"]),"total":item_list["total"]})
			return json.dumps(arrayRetorno)
	else:
		return json.dumps({'success': False, 'msg': 'Identificadores dos usuários não conferem.'})
#******* FIM EXIBE PEDIDOS USUARIO ************
#**********************************************


#******* DETALHAMENTO PEDIDO *****************
@app.get('/api/v1/user/<user_id>/orders/<order_id>')
@jwt_required
def order(user,user_id,order_id):
	if (user["id"] == user_id):
		if (order_id == ""):
			return json.dumps({'success': False, 'msg': 'Código do pedido não foi informado.'})
		else:
			db = get_database_connection()
			order =  db.orders.find_one({"_id": ObjectId(order_id),"user.id": user_id})

			if order is None:
				return json.dumps({'success': False, 'msg': 'Pedido não foi localizado para o código informado.'})
			else:
				return json.dumps({"id":str(order["_id"]),"user":order["user"],"total":order["total"],"items":order["items"],"data":str(order["date"])})
	else:
		return json.dumps({'success': False, 'msg': 'Identificadores dos usuários nao conferem.'})
#******* FIM DETALHAMENTO PEDIDO *************
#*********************************************


#*************** CRIA SESSAO *****************
@app.post('/api/v1/admin/menu/sessions/create')
@admin_required
def create_session(user):
	response.content_type = 'application/json'
	data = request.json

	if(not 'name_session' in data or not data["name_session"]):
		return json.dumps({'success': False, 'msg': 'Nome da sessão não informado.'})
	else:
		db = get_database_connection();
		nameSession = data["name_session"]
		session = db.session.find_one({'name_session': nameSession})
		if not session is None :
			return json.dumps({'success': False, 'msg': 'Sessão já cadastrada.'})
		else:
			db.session.insert({
				"name_session": data["name_session"],
			})
			return json.dumps({"success": True, "msg": "Sessão criada com sucesso"})

#************ FIM CRIA SESSAO ****************
#*********************************************


#*************** NOVO ITEM CARDAPIO **********
@app.post('/api/v1/admin/menu/items/create')
@admin_required
def create_menu_item(user):
	response.content_type = 'application/json'
	data = request.json

	if (not "name" in data or not data["name"]):
		return json.dumps({'success': False, 'msg': 'Name is required'})
	if (not "price" in data or not data["price"]):
		return json.dumps({'success': False, 'msg': 'Price is required'})
	if (not "name_session" in data or not data["name_session"]):
		return json.dumps({'success': False, 'msg': 'Name session is required'})

	db = get_database_connection()

	name = data["name"]
	price = data["price"]
	name_session = data['name_session']

	item_cad = db.menu_items.find_one({"name": name});
	if item_cad:
		return json.dumps({'success': False, 'msg': 'Item do menu já existente.'})
	else:
		db.menu_items.insert({'name': name,'price':price,'name_session':name_session})
		return json.dumps({'success':True,'msg':'Item do menu cadastrado com sucesso.'})
#******** FIM NOVO ITEM CARDAPIO **************
#**********************************************



# LINK CHAMADAS POSTMAN: https://app.getpostman.com/run-collection/cda5179b0745beb3bc6b

# **************************************************
#************** ENTIDADES **************************
# users:{
# 	_id: "57b4f1e43162731724f15de4",
# 	name: "dayane",
# 	password: "abc",
# 	email: "dayane@puc.com"
# }
#
# menu_items:{
# 	_id: "57b50450316273152ccbdd55",
# 	name: "sprite",
# 	price: 10.6,
# 	name_session: "bebidas"
# }
#
# session:{
# 	_id: "57b506be316273152ccbdd57",
# 	name: "bebidas"
# }
#
# orders:{
# 	_id: "57b50702316273152ccbdd59",
# 	date: "2016-08-19 23:00:00",
# 	total: 100.00,
# 	user: {
# 		_id: "57b4f1e43162731724f15de4"
# 	}
# 	items: [
# 		{
# 			name: "sprite"
# 		},
# 		{
# 			name: "coca-cola"
# 		},
# 	]
# }
#**************************************************
#**************************************************