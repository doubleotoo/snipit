Snippet Uploader
=================

General
-------

This is a very concise tornado application that basically functions as a pastebin.
However, it has a few defining and unique characteristics.

*	 *Memorable URL's*
	 
    We use a custom wrapper around the [Wordnik](http://www.wordnik.com) API to generate a memorable URL, 
    not a random number sequence.
*	 *Opensource (obviously)*
*	 *Automatic syntax highlighting*
*	 *Advanced and usable code editor, _not_ a &lt;textarea&gt;*
	 
    We use [CodeMirror](http://codemirror.net), a popular JavaScript code editor with built in syntax highlighting and auto-indentation.
*	 *Simple, streamlined user interface*

    Programmers are notorious for designing terrible interfaces, but we think we did a pretty good job with this one.
*	*Significantly enhances your vocabulary*

    Since every upload is linked to a unique word, hopefully you'll learn some new terms to flaunt! :D


Technology
-----------
Snippet Uploader is built to scale: it uses the [Tornado Web Framework](http://www.tornadoweb.org) to serve dynamic content.

We also use [MongoDB](http://www.mongodb.org) to store all of our data.

In the production branch, we implement the [nginx](http://nginx.org) web server to serve static files, and the nginx upload module to handle file uploads.

Install and Production
---------------

To install, first make sure you have tornado and mongo installed, and that mongod is running on localhost. Then: 

    curl -L https://github.com/hunterlang/snippet.io/tarball/master | tar zx
    cd hunterlang-snippet.io-889ba8c
    python server.py

The name of the directory in step 2 may vary, just change the text after _cd_ accordingly.

If you choose to run this app in production, you should load balance behind nginx, and use the nginx upload module.
The tornado support for the upload module is located in the production branch, but the branch doesn't work out of the box, as it requires
a specific nginx configuration. If you would like to see our config file, shoot me an email at [hunterlang@comcast.net](mailto:hunterlang@comcast.net)