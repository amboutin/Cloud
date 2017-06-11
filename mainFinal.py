# Programmer: Aaron Boutin, ONID: boutina
# Cites: Much help came from WebApp2 documentation, StackOverFlow, and developers.google.com

from google.appengine.ext import ndb
import webapp2
import json
import logging
from random import randint
from google.appengine.api import urlfetch
import urllib
from webapp2_extras import sessions

import os

def hasInList(list, item):
	for element in list:
		if item == element:
			return True
	return False

class Note(ndb.Model):
	account = ndb.StringProperty(required=True)
	id = ndb.StringProperty()
	name = ndb.StringProperty(required=True)
	note = ndb.StringProperty()
	type = ndb.StringProperty()
	binder = ndb.StringProperty()

class Binder(ndb.Model):
	account = ndb.StringProperty(required=True)
	id = ndb.StringProperty()
	name = ndb.StringProperty()
	type = ndb.StringProperty()
	current_notes = ndb.StringProperty(repeated=True)


class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)

        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session()

def thirdParty(self):
	logging.warning("Are we getting here?")
	string = self.request.headers["Authorization"]
	#logging.warning(string["access_token"])			
	url = 'https://www.googleapis.com/plus/v1/people/me'
	token = "Bearer " + string#string["access_token"]
	try:
		logging.warning("In Try of thirdparty")
		result = urlfetch.fetch(url=url, headers={"Authorization" : token})
		string = json.loads(result.content) # access values like string["id"]
		#self.session['id'] = string["id"]
		#self.response.write(result.content)
		logging.warning(result.status_code)				
		if result.status_code == 200:
			logging.warning("Are we getting here?")
			return string["id"]#self.response.out.write("Process Complete, user data acquired. Data is =" + self.session.get('id')) # remove this
	except urlfetch.Error:
		logging.exception('Caught exception fetching url')
		return None

#################################################################################################################
#################################################################################################################
class NoteHandler(BaseHandler):

	def post(self):
		uniqueid = thirdParty(self)
		note_data = json.loads(self.request.body)
		new_note = Note(account=uniqueid, name=note_data['name'], type=note_data['type'], note=note_data['note'], binder=note_data['binder'])		#instantiate note object
		new_note.put()
		new_note.id = new_note.key.urlsafe()
		new_note.put()																										#Load note object to Google DataStore
		note_dict = new_note.to_dict()
		note_dict['self'] = '/notes/' + new_note.key.urlsafe()
		note_dict['id'] = new_note.key.urlsafe()
		self.response.write(json.dumps(note_dict))

	def get(self, id=None):
		uniqueid = thirdParty(self)
		q = Note.query(Note.account == uniqueid)#q = note.query()
		result = []
		for entry in q:
			dict = {}
			dict['name'] = entry.name
			dict['type'] = entry.type
			dict['note'] = entry.note
			dict['binder'] = entry.binder
			result.append(dict)
		self.response.write(json.dumps(result))	



#################################################################################################################
class ByIdNoteHandler(BaseHandler):

	def get(self, id=None):
		uniqueid = thirdParty(self)
		logging.warning(id)
		if id:
			b = ndb.Key(urlsafe=id).get() # added uniqueid
			if b.account == uniqueid:
				b_d = b.to_dict()
				b_d['self'] = "/notes/" + id
				self.response.write(json.dumps(b_d))
			else:
				self.response.write("Cannot Access Information")	

	def patch(self, id=None):
		uniqueid = thirdParty(self)
		if id:
			b = ndb.Key(urlsafe=id).get()
			if b.account == uniqueid:
				patch_note_data = json.loads(self.request.body) # note
				if patch_note_data['name']:
					b.name = patch_note_data['name']
				if patch_note_data['type']:
					b.type = patch_note_data['type']
				if patch_note_data['note']:
					b.note = patch_note_data['note']
				if patch_note_data['binder']:
					b.binder = patch_note_data['binder']
				else:
					b.binder = None
					if b.binder == None:
						q = Binder.query(getattr(Binder, "current_notes") == b.id)
						if q:
							for entry in q:
								Binder_key = entry.id
								s = ndb.Key(urlsafe=Binder_key).get()
								s.current_notes.remove(b.id)
								s.put()
				b.put()
				note_dict = b.to_dict()
				note_dict['self'] = '/notes/' + b.key.urlsafe()
				note_dict['id'] = b.key.urlsafe()
				self.response.write(json.dumps(note_dict))
			else:
				self.response.write("Cannot Access Information")

	def delete(self, id=None):
		uniqueid = thirdParty(self)
		if id:
			b = ndb.Key(urlsafe=id).get()
			if b.account == uniqueid:
				if b.binder != None:
					logging.warning("In Delete of Note by ID")
					q = Binder.query(getattr(Binder, "current_notes") == b.id)
					for entry in q:
						Binder_key = entry.id
					s = ndb.Key(urlsafe=Binder_key).get()
					s.current_notes.remove(b.id) #= None
					s.put()
				b.key.delete()
			else:
				self.response.write("Cannot Access Information")			
 
	def put(self, id=None):
		uniqueid = thirdParty(self)
		if id:
			b = ndb.Key(urlsafe=id).get()
			if b.account == uniqueid:
				patch_note_data = json.loads(self.request.body)
				b.name = patch_note_data['name']	
				if patch_note_data['type']:
					b.type = patch_note_data['type']
				else:
					b.type = None
				if patch_note_data['note']:
					b.note = patch_note_data['note']
				else:
					b.note = None
				if patch_note_data['binder']:
					b.binder = patch_note_data['binder']
				else:
					b.binder = None
				b.id = b.key.urlsafe()				
				b.put()
				note_dict = b.to_dict()
				note_dict['self'] = '/notes/' + b.key.urlsafe()
				note_dict['id'] = b.key.urlsafe()
				self.response.write(json.dumps(note_dict))
			else:
				self.response.write("Cannot Access Information")
						
#################################################################################################################
class NoteAndBinderHandler(BaseHandler):
	def get(self, BinderID=None, noteID=None):
		uniqueid = thirdParty(self)
		if BinderID:
			if noteID == None:
				s = ndb.Key(urlsafe=BinderID).get()
				if s.account == uniqueid:
					b_d_list = []
					for notes in s.current_notes:
						b = ndb.Key(urlsafe=notes).get()
						b_d = b.to_dict()
						b_d_list.append(b_d)
					#b_d['self'] = "/Binders/" + BinderID + "/" + b.id
					self.response.write(json.dumps(b_d_list))
				else:
					b = ndb.Key(urlsafe=noteID).get()
					if b.account == uniqueid:
						b_d = b.to_dict()
						b_d['self'] = "/Binders/" + BinderID + "/" + noteID
						self.response.write(json.dumps(b_d))

	def patch(self, BinderID=None, noteID=None):
		uniqueid = thirdParty(self)
		if BinderID and noteID: 
			Binder = ndb.Key(urlsafe=BinderID).get()
			note = ndb.Key(urlsafe=noteID).get()
			if Binder.account == uniqueid:
				Binder.current_notes.append(note.id)
				note.binder=BinderID
				Binder.put()
				note.put()
				s_d = Binder.to_dict()
				s_d['self'] = "/Binders/" + BinderID + "/" +noteID
				self.response.write(json.dumps(s_d))



#################################################################################################################
class BinderHandler(BaseHandler):
	def post(self):
		#logging.warning(self.session.get('id'))
		uniqueid = thirdParty(self)
		binder_data = json.loads(self.request.body)
		new_binder = Binder(account=uniqueid, current_notes=[], name=binder_data['name'], type=binder_data['type'])
		new_binder.put()
		new_binder.id = new_binder.key.urlsafe()
		new_binder.put()	
		binder_dict = new_binder.to_dict()
		binder_dict['self'] = '/Binders/' + new_binder.key.urlsafe()
		binder_dict['id'] = new_binder.key.urlsafe()
		self.response.write(json.dumps(binder_dict))

	def get(self, id=None):
		uniqueid = thirdParty(self)
		logging.warning("FROM REGULAR HANDLER")
		logging.warning(id)
		if id:
			s = ndb.Key(urlsafe=id).get()
			if s.account == uniqueid:
				s_d = s.to_dict()
				s_d['self'] = "/Binders/" + id
				self.response.write(json.dumps(s_d))
		else:
			q = Binder.query(Binder.account == uniqueid)
			result = []
			for entry in q:
				if entry.account == uniqueid:
					dict = {}
					dict['name'] = entry.name
					dict['type'] = entry.type
					dict['current_notes'] = entry.current_notes
					dict['id'] = entry.id
					result.append(dict)
			self.response.write(json.dumps(result))

	def delete(self, id=None):
		uniqueid = thirdParty(self)
		if id:
			s = ndb.Key(urlsafe=id).get()
			if s.account == uniqueid:
				if s.current_notes:
					for note in s.current_notes:
						q = Note.query(getattr(Note, "binder") == s.id)
						for entry in q:
							note_key = entry.id
						b = ndb.Key(urlsafe=note_key).get()
						b.binder = None
						b.put()
				s.key.delete()

	def patch(self, id=None):
		uniqueid = thirdParty(self)
		if id:
			s = ndb.Key(urlsafe=id).get()
			if s.account == uniqueid:
				patch_binder_data = json.loads(self.request.body)
				if patch_binder_data['name']:
					s.name = patch_binder_data['name']
				if patch_binder_data['current_notes']:
					s.current_notes = patch_binder_data['current_notes']
				if patch_binder_data['type']:
					s.type = patch_binder_data['type']
				s.put()
				binder_dict = s.to_dict()
				binder_dict['self'] = '/notes/' + s.key.urlsafe()
				binder_dict['id'] = s.key.urlsafe()
				self.response.write(json.dumps(binder_dict))	

	def put(self, id=None):
		uniqueid = thirdParty(self)
		if id:
			s = ndb.Key(urlsafe=id).get()
			if s.account == uniqueid:
				patch_binder_data = json.loads(self.request.body)
				s.name = patch_binder_data['name']	
				if patch_binder_data['current_notes']:
					s.current_notes = patch_binder_data['current_notes']
				else:
					s.current_notes = []
				if patch_binder_data['type']:
					s.type = patch_binder_data['type']
				else:
					s.type = None
				s.id = s.key.urlsafe()				
				s.put()
				binder_dict = s.to_dict()
				binder_dict['self'] = '/notes/' + s.key.urlsafe()
				binder_dict['id'] = s.key.urlsafe()
				self.response.write(json.dumps(binder_dict))

#######################################################################################################################################################################



class LoginPage(BaseHandler):
	def get(self):
		self.session['oauth'] = False
		destination = "https://accounts.google.com/o/oauth2/v2/auth"
		amp = "&"
		eq = "="
		clientID = "client_id=912572776426-7pn8b0fbuuvkfnppjr79cn9upd8c516t.apps.googleusercontent.com"
		secretCode = "TotesASecret" + str(randint(0,99999999))
		state = "state=" + secretCode
		self.session['state'] = secretCode
		redirect = "redirect_uri=http://localhost:8080/redirect"
		uri = destination + "?" + "response_type=code" + amp + "scope=email" + amp + state + amp + clientID + amp + redirect
		#self.response.out.write("Originaly hyperlinked ->" + uri + "<- here.")
		result = urlfetch.fetch(uri)
		#print out returned values
		#string = json.loads(result.content)
		self.response.out.write(result.content)
		# https://accounts.google.com/o/oauth2/v2/auth?response_type=code&scope=email&state=TotesASecret&client_id=548315109344-jacnggnkqf6n8l5t03jcusfti0gjno7b.apps.googleusercontent.com&redirect_uri=http://localhost:8080/redirect

class RedirectPage(BaseHandler):
	def get(self):
#		code = self.request.get('code')
#		stateVer = self.request.get('state')
#		if self.session.get('state') == stateVer:
#			self.session['oauth'] = True
#			logging.warning(self.session.get('state'))
#			string = "hello"
#			if code != '':
#				payload = {'grant_type': 'authorization_code',
#				 'code': code,
#				 'client_id': '548315109344-jacnggnkqf6n8l5t03jcusfti0gjno7b.apps.googleusercontent.com',
#				 'client_secret': '7wZEjBrf1NQWzNyTfiQ25ZPu',
#				 'redirect_uri': 'http://localhost:8080/redirect'}
#
#				try:
#					form_data = urllib.urlencode(payload)
#					headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#					result = urlfetch.fetch(url='https://www.googleapis.com/oauth2/v4/token',payload=form_data,method=urlfetch.POST,headers=headers)
#					string = json.loads(result.content)
#
#				except urlfetch.Error:
#					logging.exception('Caught exception fetching url')
#
#				logging.warning("Are we getting here?")
#				logging.warning(string["access_token"])			
#				url = 'https://www.googleapis.com/plus/v1/people/me'
#				token = "Bearer " + string["access_token"]
#				try:
#					logging.warning("In Try")
#					result = urlfetch.fetch(url=url, headers={"Authorization" : token})
#					string = json.loads(result.content) # access values like string["id"]
#					self.session['id'] = string["id"]
#					#self.response.write(result.content)
#					logging.warning(result.status_code)				
#					if result.status_code == 200:
#						logging.warning("Are we getting here?")
#						self.response.out.write("Process Complete, user data acquired. Data is =" + self.session.get('id')) # remove this
#				except urlfetch.Error:
#					logging.exception('Caught exception fetching url')
#		else:
		self.response.out.write("got here")

class blob(BaseHandler):
	def get(self):
		self.response.out.write("made it")


config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'boutina',
}
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods
app = webapp2.WSGIApplication([
	('/login', LoginPage),
	('/Binders/', BinderHandler), #added last
	#('/Binders/(.*)', BinderHandler),	
	('/Notes/', NoteHandler),
	('/Notes/(.*)', ByIdNoteHandler),
	#('/(.*)', MainPage),
	('/redirect', RedirectPage),
	('/Binders/(.{48})/(.{48})', NoteAndBinderHandler),
	('/Binders/(.{48})/Note', NoteAndBinderHandler),
	('/Binders/(.{48})', BinderHandler),	
	('/blob', blob)
], debug=True, config=config)