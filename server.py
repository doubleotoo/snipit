#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 Hunter Lang, Avi Romanoff
#
# MIT License
import logging
import json
import re
import sys
import os.path
import functools
import tornado.httpserver
import tornado.httpclient
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

# Hi there fellow hacker. VID is Snippet's private API key.
# Don't use it in your own app. Get your own. They're free and 
# available from right here: http://api.wordnik.com/signup/
# Thanks.
VID = "5d7251322785b49fdf58d1f6fed01ada9d31a71c3ae369557"

define("port", default=8888, help="run on the given port", type=int)
define("password", default=None, help="MongoDB password", type=str, metavar="PASSWORD")

# This defines the applications routes
class Application(tornado.web.Application):
    def __init__(self):
        # Using the \w "word-match" regex.
        # The - is because the wordnik words
        # can have dashes in them.
        handlers = [
			(r"/", IndexHandler),
			(r"/upload", UploadHandler),
			(r"/paste", PasteHandler),
			(r"/stats", StatsHandler),
			(r"/viewforks/([\w-]+)", ViewForksHandler),
			(r"/([\w-]+)", ViewHandler),
			(r"/fork/([\w-]+)", ForkHandler),
			
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
        self.render("static/templates/index.html")

class UploadHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        client = tornado.httpclient.AsyncHTTPClient()
        request_url = "http://api.wordnik.com/v4/words.json/randomWord"
        headers = {"Content-Type" : "application/json", "api_key": VID}
        request = tornado.httpclient.HTTPRequest(request_url, headers=headers)
        client.fetch(request, self.random_callback)

    def random_callback(self, response):
        word = json.loads(response.body)['word']
        file_content = self.request.files['file'][0]
        file_body = file_content['body']
        file_name = file_content['filename']
        language_guessed = get_lexer_for_filename(file_name).name.lower()  
        codemirror_mode = self.code_mirror_safe_mode(language_guessed) 
                
        # mid == memorable ID. That's where the Wordnik-given random name goes.
        # "id" is obviously taken, and I didn't want to add another direct
        # spinoff of that token.
        snippets.insert({'title': file_name, 'mid' : word, 'body' : unicode(file_body, 'utf-8'), 'forks' : [], 'language': codemirror_mode})        
        print language_guessed
        self.render("static/templates/upload.html", name=file_name, code_html=file_body, mid = word, forked_from = None, language_guessed = codemirror_mode)
    
    def code_mirror_safe_mode(self, language):
        if language == "python":
            mode = "python"
            return mode
        elif language == "php":
            mode = "application/x-httpd-php"
            return mode
        elif language == "html":
            mode = "text/html"
            return mode
        elif language == "xml":
            mode = "application/xml"
            return mode
        elif language == "javascript":
            mode = "text/javascript"
            return mode
        elif language == "css":
            mode = "text/css"
            return mode
        else:
            return "text/plain"


class PasteHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        client = tornado.httpclient.AsyncHTTPClient()
        request_url = "http://api.wordnik.com/v4/words.json/randomWord"
        headers = {"Content-Type" : "application/json", "api_key": VID}
        request = tornado.httpclient.HTTPRequest(request_url, headers=headers)
        client.fetch(request, self.random_callback)

    def random_callback(self, response):
        word = json.loads(response.body)['word']
        file_body = self.request.arguments['body'][0]
        file_name = self.request.arguments['name'][0]
        snippets.insert({'title': file_name, 'mid' : word, 'body' : unicode(file_body, 'utf-8'), 'forks' : []})
        self.render("static/templates/upload.html", name=file_name, code_html=file_body, mid = word, forked_from = None)

class ViewHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, mid):
        snippet = snippets.find_one({'mid' : mid})
        parent_snippet = snippets.find_one({"forks" : {"$in" : [snippet['_id']]}})
        if parent_snippet:
            forked_from_mid = parent_snippet['mid']
        else:
            forked_from_mid = None
        fork_count = len(snippet['forks'])
        language = snippet['language']
        self.render("static/templates/view.html", name = snippet['title'], code_html = snippet['body'], description = None, mid=mid, fork_count = fork_count, forked_from = forked_from_mid, mode=language)

class ForkHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, mid):
        snippet_to_be_forked = snippets.find_one({'mid' : mid})
        raw_text = snippet_to_be_forked['body']
        name = "Fork of " + snippet_to_be_forked['title']
        self.render("static/templates/fork.html", name=name, raw_text=raw_text, mid=mid)
    @tornado.web.asynchronous
    def post(self, parent_mid):
        client = tornado.httpclient.AsyncHTTPClient()
        request_url = "http://api.wordnik.com/v4/words.json/randomWord"
        headers = {"Content-Type" : "application/json", "api_key" : VID}
        request = tornado.httpclient.HTTPRequest(request_url, headers=headers)
        client.fetch(request, functools.partial(self.random_callback, parent_mid))

    def random_callback(self, parent_mid, response):
        word = json.loads(response.body)['word']
        text = self.request.arguments['body'][0]
        name = self.request.arguments['name'][0]
        _id = snippets.insert({'title': name, 'mid': word, 'body': unicode(text, 'utf-8'), 'forks' : []})
        # `safe` turns on error-checking for the update request, so we print out the response.
        print snippets.update({'_id': parent_mid}, {"$push": {"forks" : ObjectId(_id)}}, safe=True)
        self.render("static/templates/upload.html", name=name, code_html=text, mid = word, forked_from = parent_mid, fork_count=0)

class ViewForksHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	def get(self, mid):
        # We really should look into turning on indexing for the mids.
        # Mongo automatically indexes the ObjectIds, but it also lets 
        # you select multiple other indexes. I'll look into that.
		snippet = snippets.find_one({'mid' : mid})
		print snippet['forks']
		self.finish("")

class StatsHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        # right now this makes a list of *every* snippet. this is obviously inefficient.
        # we need to find a way to query directly with mongo and limit to 10 results.
        top_snippets = []
        for snippet in snippets.find():
            top_snippets.append([len(snippet['forks']), snippet['title'], snippet['mid']])
        top_snippets.sort()
        top_snippets.reverse()
        top_snippets = top_snippets[0:10]
        self.render("static/templates/stats.html", top_snippets=top_snippets)

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
