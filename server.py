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
from pygments.util import ClassNotFound
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
            (r"/about", AboutHandler),
			(r"/upload/nginx", UploadHandler),
			(r"/file_upload", UploadHandler),
			(r"/paste", PasteHandler),
			(r"/default_language", DefaultLanguageHandler),
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
class BaseHandler(tornado.web.RequestHandler):
    @property
    def default_language(self):
        return self.get_secure_cookie("default_language")
    
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
        elif language == "c++":
            mode = "text/x-c++src"
            return mode
        elif language == "c":
            mode = "text/x-csrc"
            return mode
        elif language == "java":
            print "LOL someone used java."
            mode = "text/x-java"
            return mode
class IndexHandler(BaseHandler):
    @tornado.web.asynchronous
    def get(self):
        if self.default_language: default=self.code_mirror_safe_mode(self.default_language)
        else: default="text/plain"
        self.render("static/templates/index.html", mode=default)

class AboutHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("static/templates/about.html")

class UploadHandler(BaseHandler):
    @tornado.web.asynchronous
    def post(self):
        file_name = self.request.arguments['file_name'][0]
        file_path = self.request.arguments['file_path'][0]
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.pipe = p = os.popen("sudo cat " + file_path)
        self.ioloop.add_handler(p.fileno(), self.async_callback(self.on_response), self.ioloop.READ)
    
    def on_response(self, fd, events):
        file_name = self.request.arguments['file_name'][0]
        file_body = ""
        for line in self.pipe:
            file_body = file_body + line        
        try:
            language_guessed = get_lexer_for_filename(file_name).name.lower()
        except Exception:
            language_guessed = guess_lexer(file_body).name.lower()
        codemirror_mode = self.code_mirror_safe_mode(language_guessed)         
        self.ioloop.remove_handler(fd)
        
        self.render("static/templates/codemirror.html", name=file_name,code_html=file_body, language_guessed = codemirror_mode)

class PasteHandler(BaseHandler):
    @tornado.web.asynchronous
    def post(self):
        client = tornado.httpclient.AsyncHTTPClient()
        request_url = "http://api.wordnik.com/v4/words.json/randomWord?includePartOfSpeech=adjective&maxLength=18&minLength=2"
        headers = {"Content-Type" : "application/json", "api_key": VID}
        request = tornado.httpclient.HTTPRequest(request_url, headers=headers)
        client.fetch(request, self.random_callback)

    def random_callback(self, response):
        word = json.loads(response.body)['word']
        file_body = self.request.arguments['body'][0]
        file_name = self.request.arguments['name'][0]
        if file_name is "None": file_name=word
        language_guessed = guess_lexer(file_body).name.lower()
        codemirror_mode = self.code_mirror_safe_mode(language_guessed)
        snippets.insert({'title': file_name, 'mid' : word, 'body' : unicode(file_body, 'utf-8'), 'forks' : [], 'language': codemirror_mode})
        
        if self.default_language: 
            print self.default_language
            show_default_prompt = False
        else: show_default_prompt = True
        
        self.render("static/templates/upload.html", name=file_name, code_html=file_body, mid = word, forked_from = None, language_guessed = codemirror_mode, show_default_prompt=show_default_prompt)

class DefaultLanguageHandler(BaseHandler):
    @tornado.web.asynchronous
    def post(self):
        self.set_secure_cookie("default_language", self.request.arguments['language'][0], expires_days=30)
        print self.request.arguments['language']
        self.finish("")
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
        parent_language = language=snippet_to_be_forked['language']
        name = "Fork of " + snippet_to_be_forked['title']
        self.render("static/templates/fork.html", name=name, raw_text=raw_text, mid=mid, language=parent_language)
    @tornado.web.asynchronous
    def post(self, parent_mid):
        client = tornado.httpclient.AsyncHTTPClient()
        request_url = "http://api.wordnik.com/v4/words.json/randomWord?includePartOfSpeech=adjective&maxLength=18&minLength=2"
        headers = {"Content-Type" : "application/json", "api_key" : VID}
        request = tornado.httpclient.HTTPRequest(request_url, headers=headers)
        client.fetch(request, functools.partial(self.random_callback, parent_mid))

    def random_callback(self, parent_mid, response):
        word = json.loads(response.body)['word']
        text = self.request.arguments['body'][0]
        name = self.request.arguments['name'][0]
        parent_language = snippets.find_one({'mid' : parent_mid}, {'language' : 1})['language']
        _id = snippets.insert({'title': name, 'mid': word, 'language' : parent_language,'body': unicode(text, 'utf-8'), 'forks' : []})
        # `safe` turns on error-checking for the update request, so we print out the response.
        print snippets.update({'mid': parent_mid}, {"$push": {"forks" : ObjectId(_id)}}, safe=True)
        self.render("static/templates/upload.html", name=name, code_html=text, mid = word, forked_from = parent_mid, fork_count=0, language_guessed=parent_language, show_default_prompt=False)

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
