#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 Hunter Lang, Avi Romanoff -XVII
#
# MIT License
import logging
import re
import sys
import os.path
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
from pymongo.errors import ConfigurationError

define("port", default=8888, help="run on the given port", type=int)
define("password", default=None, help="MongoDB password", type=str, metavar="PASSWORD")

# This defines the applications routes
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
			(r"/", IndexHandler),
			(r"/upload", UploadHandler),
			(r"/stats", StatsHandler),
			(r"/([A-Za-z0-9]+)", ViewHandler),
			(r"/fork/([A-Za-z0-9]+)", ForkHandler),
			
        ]
        
        settings = dict(
            debug = True, # For auto-reload
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret = "72-OrTzKXeAGaYdkL5gEmGeKSFumh7Ec+p2XdTP1o/Vo=",
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
        html = highlight(file_body, lexer, HtmlFormatter())
        # It's schemaless, so we don't need to specify null values for unused fields.
        _id = snippets.insert({'title': file_name, 'body' : unicode(file_body, 'utf-8'), 'forks' : []})
        self.render("static/upload.html", name=file_name, code_html=html, id = _id, forked_from = None)

class ViewHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, __id):
        # Yes, the mongodb ObjectId is really _id in PyMongo..
        snippet = snippets.find_one({'_id' : ObjectId(__id)})
        lexer = guess_lexer(snippet['body'])
        html = highlight(snippet['body'], lexer, HtmlFormatter())
        parent_snippet = snippets.find_one({"forks" : {"$in" : [snippet['_id']]}})
        if parent_snippet:
            forked_from_id = parent_snippet['_id']
        else:
            forked_from_id = None
        fork_count = len(snippet['forks'])
        self.render("static/view.html", name = snippet['title'], code_html = html, description = None, id=__id, fork_count = fork_count, forked_from = forked_from_id)

class ForkHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, __id):
        snippet_to_be_forked = snippets.find_one({'_id' : ObjectId(__id)})
        raw_text = snippet_to_be_forked['body']
        name = "Fork of " + snippet_to_be_forked['title']
        self.render("static/fork.html", name=name, raw_text=raw_text, id=__id)
    def post(self, __id):
        text = self.request.arguments['body'][0]
        name = self.request.arguments['name'][0]
        parent_id = __id
        lexer = guess_lexer(text)
        html = highlight(text, lexer, HtmlFormatter())
        _id = snippets.insert({'title': name, 'body': unicode(text, 'utf-8'), 'forks' : []})
        # `safe` turns on error-checking for the update request, so we print out the response.
        print snippets.update({'_id': ObjectId(parent_id)}, {"$push": {"forks" : ObjectId(_id)}}, safe=True)
        self.render("static/upload.html", name=name, code_html=html, id = _id, forked_from = parent_id, fork_count=0)

class StatsHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        top_snippets = []
        for snippet in snippets.find():
            top_snippets.append([len(snippet['forks']), snippet['title'], snippet['_id']])
        top_snippets.sort()
        top_snippets = top_snippets[0:10]
        top_snippets.reverse()
        self.render("static/stats.html", top_snippets=top_snippets)

def main():
    http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True) # enables headers so it can be run behind nginx
    http_server.listen(options.port)
    logging.info("Serving on port %s" % options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    tornado.options.parse_command_line()
    MONGO_SERVER = "mongodb://aroman:%s@dbh23.mongolab.com:27237/struts" % options.password
    try:
        connection = Connection(MONGO_SERVER)
        db = connection['struts'] # ~= database name
        snippets = db['snippets'] # ~= database table
        logging.info("Connected to database")
    except ConfigurationError:
        logging.critical("Can't connect to database with password \"%s\"" % options.password)
        # Terminate program with error return code.
        sys.exit(1)
    main()
