#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 Hunter Lang, Avi Romanoff
#
# MIT License
import logging
import re
import json
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

define("port", default=8888, help="run on the given port", type=int)

# This defines the applications routes
class Application(tornado.web.Application):
    def __init__(self):
        # Using the \w "word-match" regex.
        # The - is because the wordnik words
        # can have dashes in them.
        handlers = [

            (r"/updates/live/([\w-]+)", LiveHandler),
            (r"/updates/([\w-]+)", UpdatesHandler),
            (r"/updates/cache/([\w-]+)", CacheHandler),
			
        ]
        settings = dict(
            debug = True, # For auto-reload
        )
        tornado.web.Application.__init__(self, handlers, **settings)

# BEGIN LIVE COLLAB BLOCK

class LiveMixin(object):

    waiters = []
    cache = []
    cache_size = 200
    
    def wait_for_text(self, callback, wid, cursor=None):
        cls = LiveMixin
        if cursor:
            index = 0
            for i in xrange(len(cls.cache)):
                index = len(cls.cache) - i - 1
                if cls.cache[index]["id"] == cursor: break
            recent = cls.cache[index + 1:]
            if recent:
                callback(recent)
                return
        cls.waiters.append([callback, wid])

    def new_text(self, text):
        cls = LiveMixin
        for callback in cls.waiters:
            try:
                for x in text:
                    if callback[1] == x["wid"]:
                            callback[0]([x])
            except:
                logging.error("Error in waiter callback", exc_info=True)
        cls.waiters = []
        cls.cache.extend(text)
        if len(cls.cache) > self.cache_size:
            cls.cache = cls.cache[-self.cache_size:]

class LiveHandler(tornado.web.RequestHandler, LiveMixin):
    @tornado.web.asynchronous
    def get(self, wid):
        snippet = snippets.find_one({'mid':wid})
        self.render('static/templates/live.html', word=wid, code = snippet['body'], mode=snippet['language'], poster_id=str(uuid.uuid4()))

    def post(self, wid):
        print wid
        try:
            body = self.request.arguments['body'][0]
        except KeyError:
            body = ""
        post = {
            "body": body,
            "wid": wid,
            "poster_id": self.request.arguments['poster_id'][0]
        }
        self.new_text([post])

class UpdatesHandler(tornado.web.RequestHandler, LiveMixin):
    @tornado.web.asynchronous
    def post(self, wid):
        cursor = self.get_argument('cursor', None)
        self.wait_for_text(self.async_callback(self.on_new_text), wid, cursor=cursor)
    def on_new_text(self, post):
        self.finish(post[0])


class CacheHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, wid):
        whole_cache = LiveMixin.cache
        try:
            rel_cache = [update for update in whole_cache if update['wid'] == wid][-1]
        except IndexError:
            rel_cache = """{ "body":"" }"""
        finish_data = {
            "cache": rel_cache,
        }
        self.finish(json.dumps(finish_data))

# END LIVE COLLAB BLOCK
def main():
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    logging.info("Port: %s" % options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    tornado.options.parse_command_line()
    main()
