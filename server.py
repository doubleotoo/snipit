#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 Hunter Lang, Avi Romanoff
#
# MIT License
import logging
import json
import re
import sys
import uuid
import os.path
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
from pymongo import ASCENDING, DESCENDING

# Hi there fellow hacker. VID is Snippet's private API key.
# Don't use it in your own app. Get your own. They're free and 
# available from right here: http://api.wordnik.com/signup/
# Thanks.

define("port", default=8888, help="run on the given port", type=int)

VID = "5d7251322785b49fdf58d1f6fed01ada9d31a71c3ae369557"
wordnik_request_url = "http://api.wordnik.com/v4/words.json/randomWord?includePartOfSpeech=adjective&maxLength=18&minLength=2"

# This defines the applications routes
class Application(tornado.web.Application):
    def __init__(self):
        # Using the \w "word-match" regex.
        # The - is because the wordnik words
        # can have dashes in them.
        handlers = [

            (r"/", IndexHandler),
            (r"/about", AboutHandler),
	    (r"/file_upload", UploadHandler),
	    (r"/paste", PasteHandler),
	    (r"/stats", StatsHandler),
	    (r"/viewforks/([\w-]+)", ViewForksHandler),
	    (r"/([\w-]+)", ViewHandler),
	    (r"/fork/([\w-]+)", ForkHandler),
            (r"/live/([\w-]+)", LiveHandler),
            (r"/side/([\w-]+)\+([\w-]+)", SideHandler),
            (r"/body/([\w-]+)", BodyHandler)
			
        ]
        settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
        )
        tornado.web.Application.__init__(self, handlers, autoescape=None, **settings) 

class BaseHandler(tornado.web.RequestHandler):
    #should i put @tornado.web.asynchronous here?
    def code_mirror_safe_mode(self, language):
        if language == "python":mode = "python"
        elif language == "php":mode = "application/x-httpd-php"
        elif language == "html":mode = "text/html"
        elif language == "xml":mode = "application/xml"
        elif language == "javascript":mode = "text/javascript"
        elif language == "css":mode = "text/css"
        elif language == "c++":mode = "text/x-c++src"
        elif language == "c":mode = "text/x-csrc"
        elif language == "java":mode = "text/x-java"
        elif language == "perl":mode = "python"
        elif language == "objc":mode = "text/x-csrc"
        else: mode="text/plain"
        return mode
    #should i put @tornado.web.asynchronous here?
    def external_api_request(self, callback, request_url):
        client = tornado.httpclient.AsyncHTTPClient()
        headers = {"Content-Type" : "application/json", "api_key" : VID}
        request = tornado.httpclient.HTTPRequest(request_url, headers=headers)
        client.fetch(request, callback)
        
class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("static/templates/index.html")

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
        self.ioloop.add_handler(p.fileno(), 
                    self.async_callback(self.on_response), self.ioloop.READ)
    
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
        
        self.render("static/templates/codemirror.html", name=file_name,
                    code_html=file_body, language_guessed = codemirror_mode)

class PasteHandler(BaseHandler):
    @tornado.web.asynchronous
    def post(self):
        self.external_api_request(self.random_callback, wordnik_request_url)

    def random_callback(self, response):
        word = json.loads(response.body)['word']
        file_body = self.request.arguments['body'][0]
        file_name = self.request.arguments['name'][0]
        try:
            language_guessed = get_lexer_for_filename(file_name).name.lower()
        except Exception:
            language_guessed = guess_lexer(file_body).name.lower()
        
        file_name=word
        codemirror_mode = self.code_mirror_safe_mode(language_guessed)        
        snippets.insert({'title': file_name, 'mid' : word, 'body' : unicode(file_body, 'utf-8'), 
                         'forks' : [], 'language': codemirror_mode})
        
        self.finish(word)
        
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
        self.render("static/templates/view.html", name = snippet['title'], code_html = snippet['body'], 
                    description = None, mid=mid, fork_count = fork_count, 
                    forked_from = forked_from_mid, mode=language)

class ForkHandler(BaseHandler):
    @tornado.web.asynchronous
    def post(self, parent_mid):
        self.external_api_request(self.random_callback, wordnik_request_url)

    def random_callback(self, response):
        parent_mid = self.request.uri.split('/')[2]
        word = json.loads(response.body)['word']
        text = self.request.arguments['body'][0]
        parent_language = snippets.find_one({'mid' : parent_mid}, {'language' : 1})['language']
        _id = snippets.insert({'title': word, 'mid': word, 'language' : parent_language,
                               'body': unicode(text, 'utf-8'), 'forks' : []})
        print snippets.update({'mid': parent_mid}, {"$push": {"forks" : ObjectId(_id)}}, safe=True)
        self.finish("/" + word)

class ViewForksHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	def get(self, mid):
        # We really should look into turning on indexing for the mids.
        # Mongo automatically indexes the ObjectIds, but it also lets 
        # you select multiple other indexes. I'll look into that.
        
        # 8/19/2011 - I turned on indexing for the mid key.
        # It's now a B-Tree index. We should see a performance boost.
            fork_list = []
            the_snippet = snippets.find_one({'mid' : mid})
            for thing in the_snippet['forks']:
                snippet = snippets.find_one({'_id' : thing})
                fork_list.append([snippet['title'], snippet['mid']])
            self.render("static/templates/viewforks.html", forks=fork_list, title=the_snippet['title'])

# BEGIN LIVE COLLAB BLOCK
class LiveHandler(BaseHandler):
    @tornado.web.asynchronous
    # This is the only method still needed. All other live-related actions are forwarded to live.py
    # by nginx.
    def get(self, wid):
        self.external_api_request(self.on_response, "http://localhost:9300/updates/cache/" + wid)

    def on_response(self, response):
        wid = self.request.uri.split("/")[2]
        try:
            body = json.loads(response.body)['cache']['body']
        except TypeError:
            body = ""
        snippet = snippets.find_one({ 'mid':wid })
        stored_body = snippet['body']
        if not body is "" and not body == stored_body:
            stored_body = body
        self.render('static/templates/live.html', word=wid, code = stored_body, 
                    mode=snippet['language'], poster_id=str(uuid.uuid4()))

# END LIVE COLLAB BLOCK

class SideHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, forked_from_wid, fork_wid):
        forked_from =  snippets.find_one({"mid":forked_from_wid})
        fork = snippets.find_one({"mid":fork_wid})
        self.render("static/templates/side.html", forked_from_dict=forked_from, fork_dict=fork)
        

class StatsHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        top_snippets = snippets.find().sort("forks", DESCENDING).limit(10)
        total_snippets = snippets.count()
        self.render("static/templates/stats.html", 
                    top_snippets=top_snippets, total_snippets=total_snippets)

# This class simply returns a JSON object containing
# the body of a requested snippet.
class BodyHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, mid):
        try:
            snippet = snippets.find_one({"mid" : mid})["body"]
            self.finish(json.dumps({"body":snippet}))
        except TypeError:
            self.finish("No snippet with mid " + mid + " found.")
def main():
    # enables headers so it can be run behind nginx
    http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True) 
    http_server.listen(options.port)
    logging.info("Serving on port %s" % options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    tornado.options.parse_command_line()
    connection = Connection('localhost', 27017)
    db = connection['struts'] # ~= database name
    snippets = db['snippets'] # ~= database table
    logging.info("Connected to database")
    main()
