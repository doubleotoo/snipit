#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 Hunter Lang
#
# MIT License
import logging
import base64
import re
import os.path
import sqlite3
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
        tornado.web.Application.__init__(self, handlers, autoescape=None, **settings)   #Disables auto escape in templates so xsrf works


class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("static/index.html")
class UploadHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        db = sqlite3.connect("db.db")
        dbc = db.cursor()
        file_content = self.request.files['file'][0]
        file_body = file_content['body']
        file_name = file_content['filename']
        lexer = guess_lexer(file_body)
        print lexer
        html = highlight(file_body, lexer, HtmlFormatter())
        _id = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase  + string.digits) for x in range(randint(5,10)))
        dbc.execute("insert into snippet values (?,?,?,?,?)", [unicode(file_body, 'utf-8'), file_name, None, None, _id])
        db.commit()
        dbc.close()
        db.close()
        self.render("static/upload.html", lexer=lexer.__class__, code_html=html, id = _id)
class ViewHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, id):
        db = sqlite3.connect("db.db")
        dbc = db.cursor()
        dbc.execute("select body, name, description, password from snippet where id=?", [id])
        results = dbc.fetchone()
        if not results:
            self.finish("Snippet not found.")
            return
        body = results[0]
        name = results[1]
        description = results[2]
        password = results[3]
        lexer = guess_lexer(body)
        html = highlight(body, lexer, HtmlFormatter())        
        self.render("static/view.html", name = name, code_html = html, description = description)
def main():
   	tornado.options.parse_command_line()
   	http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True)      #enables headers so it can be run behind nginx
   	http_server.listen(options.port)
   	tornado.ioloop.IOLoop.instance().start()
if __name__ == "__main__":
    main()
