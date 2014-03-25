#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import urllib
import cgi
import datetime

from google.appengine.api import users
from google.appengine.ext import ndb, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import search
from google.appengine.api import mail
from google.appengine.api import images

import webapp2
import jinja2

DEFAULT_GUESTBOOK_NAME = 'default_guestbook'

def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name)


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])

class Advert(ndb.Model):
    author = ndb.UserProperty()
    is_patron = ndb.BooleanProperty()
    is_closed = ndb.BooleanProperty()
    must_be_done = ndb.TextProperty(indexed=False)
    will_be_given = ndb.TextProperty(indexed=False)
    # periodicity = ndb.StringProperty(indexed=False)
    owner_name = ndb.StringProperty(indexed=False)
    # valid_until = ndb.DateTimeProperty(auto_now_add=False)
    added = ndb.DateTimeProperty(auto_now_add=True)
    contact_email = ndb.StringProperty(indexed=True)
    contact_phone = ndb.StringProperty(indexed=True)
    contact_url = ndb.StringProperty(indexed=True)
    # category = ndb.StructuredProperty(Category, repeated=False)
    category = ndb.StringProperty(indexed=True)
    image = ndb.BlobProperty()

class MainPage(webapp2.RequestHandler):

    def get(self):

        adverts_query = Advert.query().order(-Advert.added)
        adverts = adverts_query.fetch(10)
        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'adverts': adverts,
            'url': url,
            'url_linktext': url_linktext,
            'page': 'index',
            'user': user,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(template_values))

class AdvertList(webapp2.RequestHandler):

    def get(self):
        category = self.request.get('category')
        my = self.request.get('my')

        user = users.get_current_user()
        # search = self.request.get('search')
        search = None
        if search:
            # TODO padaryti indexą ir paiešką
            adverts_query = Advert.query(Advert.is_closed==False).order(-Advert.added)
        elif category and category != '-':
            adverts_query = Advert.query(Advert.is_closed==False,Advert.category==category).order(-Advert.added)
        elif my:
            adverts_query = Advert.query(Advert.is_closed==False,Advert.author==user).order(-Advert.added)
        else:
            adverts_query = Advert.query(Advert.is_closed==False).order(-Advert.added)

        adverts = adverts_query.fetch()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        if my:
            page = 'myads'
        else:
            page = 'adlist'
        template_values = {
            'adverts': adverts,
            'url': url,
            'url_linktext': url_linktext,
            'category': category,
            'page': page,
            'user': user,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/adlist.html')
        self.response.write(template.render(template_values))

class AdvertSingle(webapp2.RequestHandler):

    def get(self, advert_id):

        advert = Advert.get_by_id(int(advert_id))
        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        
        editable = False
        if user == advert.author:
            editable = True

        template_values = {
            'advert': advert,
            'url': url,
            'url_linktext': url_linktext,
            'editable': editable,
            'page': 'adlist',
            'user': user,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/advert.html')
        self.response.write(template.render(template_values))


class ContactAd(webapp2.RequestHandler):

    def get(self, advert_id):

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        if advert_id:
            advert = Advert.get_by_id(int(advert_id))
            template_values = {
                'url': url,
                'url_linktext': url_linktext,
                'page': 'adlist',
                'user': user,
                'adid': advert_id,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/contact_ad.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('')


    def post(self, advert_id):

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        if advert_id:
            advert = Advert.get_by_id(int(self.request.get('adid')))

            sender_name = self.request.get('sender_name')
            sender_email = self.request.get('sender_email')
            sender_phone = self.request.get('sender_phone')
            sender_web = self.request.get('sender_web')
            additional_text = self.request.get('text')

            if advert.is_patron:
                subject = u'Someone wants you to be his patron'
            else:
                subject = u'Someone wants you to be your patron'
            
            # sender = u'%s <%s>' % (sender_name,sender_email)
            sender = u'Get a Mentor <kroitus@gmail.com>'

            message = mail.EmailMessage(sender=sender, subject=subject)

            message.to = advert.contact_email
            message.reply_to = sender_email
            message.body = """
Helo,

Someone saw your patronage ad (http://getpatronus.appspot.com//advert/%(adid)s), and was interested in it.

%(text)s

Here are contacts:
Name: %(sender_name)s,
Email: %(sender_email)s,
Phone: %(sender_phone)s,
Website: %(sender_web)s,
""" % {'adid':advert.key.id(),
        'sender_name':sender_name,
        'sender_phone':sender_phone,
        'sender_email':sender_email,
        'sender_web':sender_web,
        'text':additional_text,
}

            message.send()

            template_values = {
                'url': url,
                'url_linktext': url_linktext,
                'page': 'adlist',
                'user': user,
                'adid': advert_id,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/thankyou.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('')


class ContactMe(webapp2.RequestHandler):

    def post(self):

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        sender_name = self.request.get('name')
        sender_email = self.request.get('email')
        additional_text = self.request.get('text')

        subject = u'Someone is contacting from get a patronus'

        sender = u'Get a Mentor <kroitus@gmail.com>'

        message = mail.EmailMessage(sender=sender, subject=subject)

        message.to = u'kroitus@gmail.com'
        message.reply_to = sender_email

        message.body = """
Someone is trying to contact.

%(text)s

Here are contacts:
Name: %(sender_name)s,
Email: %(sender_email)s,
""" % {
    'sender_name':sender_name,
    'sender_email':sender_email,
    'text':additional_text,
}

        message.send()

        template_values = {
            'url': url,
            'url_linktext': url_linktext,
            'page': 'about',
            'user': user,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/thankyou.html')
        self.response.write(template.render(template_values))



class AdvertAdd(webapp2.RequestHandler):


    def get(self):

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        ad_data = {'must_be_done':'',
            'owner_name':'',
            'is_patron':'',
            'will_be_given':'',
            'contact_email':'',
            'contact_phone':'',
            'category':'',
            'contact_url':'',
            'adid':'',
        }

        advert_id = self.request.get('adid')
        if advert_id:
            advert = Advert.get_by_id(int(advert_id))
            if advert.author == user:
                ad_data['must_be_done'] = advert.must_be_done
                if advert.is_patron:
                    ad_data['is_patron'] = 'patron'
                else:
                    ad_data['is_patron'] = 'artist'

                if advert.is_closed:
                    ad_data['is_closed'] = 'closed'
                else:
                    ad_data['is_closed'] = 'active'

                ad_data['owner_name'] = advert.owner_name
                ad_data['will_be_given'] = advert.will_be_given
                ad_data['contact_email'] = advert.contact_email
                ad_data['contact_phone'] = advert.contact_phone
                ad_data['category'] = advert.category
                ad_data['contact_url'] = advert.contact_url
                ad_data['adid'] = advert.key.id()

        if user:
            template_values = {
                'url': url,
                'url_linktext': url_linktext,
                'ad_data':ad_data,
                'page': 'addnew',
                'user': user,
            }

            template = JINJA_ENVIRONMENT.get_template('templates/add_new.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

    def post(self):
        # import pdb; pdb.set_trace()

        if self.request.get('adid'):
            advert = Advert.get_by_id(int(self.request.get('adid')))
        else:
            advert = Advert()

        user = users.get_current_user()

        if user:
            save_it = False
            if advert.author:
                if advert.author == user:
                    save_it = True
            else:
                save_it = True
            if save_it:
                advert.author = users.get_current_user()

                advert.must_be_done = self.request.get('must_be_done')
                is_patron = self.request.get('is_patron')
                is_closed = self.request.get('is_closed')
                if is_patron == 'patron':
                    advert.is_patron = True
                else:
                    advert.is_patron = False

                if is_closed == 'closed':
                    advert.is_closed = True
                else:
                    advert.is_closed = False

                advert.owner_name = self.request.get('owner_name')
                advert.will_be_given = self.request.get('will_be_given')
                advert.contact_email = self.request.get('contact_email')
                advert.contact_phone = self.request.get('contact_phone')
                advert.category = self.request.get('category')
                contact_url = self.request.get('contact_url').replace('http://','')
                advert.contact_url = contact_url
                advert.is_closed = False
                
                if self.request.get('picture'):
                    raw_image = images.Image(self.request.POST['picture'].file.read())
                    raw_image.resize(width=600)
                    final_image = raw_image.execute_transforms(output_encoding=images.JPEG)
                    advert.image = final_image
                    

                advert.put()
        else:
            self.redirect(users.create_login_url(self.request.uri))

        self.redirect('/adlist/')

class AboutPage(webapp2.RequestHandler):
    def get(self):

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'url': url,
            'url_linktext': url_linktext,
            'page': 'about',
            'user': user,
        }

        template = JINJA_ENVIRONMENT.get_template('templates/about.html')
        self.response.write(template.render(template_values))


class AdImage(webapp2.RequestHandler):
    def get(self, key):
        advert = Advert.get_by_id(int(key))

        self.response.headers['Content-Type'] = 'image/jpg'
        self.response.out.write(advert.image)


app = webapp2.WSGIApplication(routes=[
    ('/', MainPage),
    ('/add_new/', AdvertAdd),
    ('/adlist/', AdvertList),
    ('/advert/(\d+)', AdvertSingle),
    ('/contact/(\d+)', ContactAd),
    ('/contact/', ContactMe),
    ('/about/', AboutPage),
    ('/adimage/(.*)', AdImage),
], debug=True)
