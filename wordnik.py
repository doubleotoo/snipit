# -*- coding: utf-8 -*-
# Copyright 2011 Avi Romanoff
#
# MIT License
import tornado.httpclient
import tornado.ioloop

# Hi there fellow hacker. VID is Snippet's private API key.
# Don't use it in your own app. Get your own. They're free and 
# available from right here: http://api.wordnik.com/signup/
# Thanks.
VID = "5d7251322785b49fdf58d1f6fed01ada9d31a71c3ae369557"
BASE_URL = "http://api.wordnik.com/v4/"

class WordnikServant():

    def __init__(self):
        self.client = tornado.httpclient.AsyncHTTPClient()

    def fetch_base(self, query):

        request_url = "%swords.json/%s" % BASE_URL, query
        headers = {"Content-Type" : "application/json", "api_key" : VID}
        self.client.HTTPRequest(request_url, headers=headers)

    def fetch_random(self):
        pass

    def get_random(self):
        pass
