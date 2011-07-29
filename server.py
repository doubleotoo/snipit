#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 Hunter Lang, Avi Romanoff I
#
# MIT License
import logging
import base64
import re
import os.path
import uuid
import string
import random
from random import randint
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.template as template
from tornado.options import define, options
from pygments import highlight
from pygments.lexers import *
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name
from pymongo import Connection
from pymongo.objectid import ObjectId

MONGO_SERVER = "localhost"
MONGO_PORT = 27017

connection = Connection(MONGO_SERVER, MONGO_PORT)
db = connection['struts'] # ~= database name
snippets = db['snippets'] # ~= database table

define("port", default=8888, help="run on the given port", type=int)

# This defines the applications routes
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
			(r"/", IndexHandler),
			(r"/upload", UploadHandler),
			(r"/([A-Za-z0-9]+)", ViewHandler)
        ]
        
        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret = "72-OrTzKXeAGaYdkL5gEmGeKSFumh7Ec+p2XdTP1o/Vo=",
            login_url = "/login",
            xsrf_cookies = True,
        )
        tornado.web.Application.__init__(self, handlers, autoescape=None, **settings) # Disables auto escape in templates so xsrf works


class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("static/index.html")

class UploadHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        file_content = self.request.files['file'][0]
        file_body = file_content['body']
        file_name = file_content['filename']
        lexer = guess_lexer(file_body)
        print lexer
        html = highlight(file_body, lexer, HtmlFormatter())
        # It's schemaless, so we don't need to specify null values for unused fields.
        _id = snippets.insert({'title': file_name, 'body' : unicode(file_body, 'utf-8')})
        self.render("static/upload.html", lexer=lexer.__class__, code_html=html, id = _id)

class ViewHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, __id):
        # Yes, the mongodb ObjectId is really _id in PyMongo..
        snippet = snippets.find_one({'_id' : ObjectId(__id)})
        lexer = guess_lexer(snippet['body'])
        html = highlight(snippet['body'], lexer, HtmlFormatter())        
        # Description is missing since mongo can't handle the truth (that the dict
        # key doesn't exist).
        self.render("static/view.html", name = snippet['title'], code_html = html, description = None)

def main():
   	tornado.options.parse_command_line()
   	http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True) # enables headers so it can be run behind nginx
   	http_server.listen(options.port)
   	tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
