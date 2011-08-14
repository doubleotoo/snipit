Snippet Uploader
=================

General
-------

This is a very concise tornado application that basically functions as a pastebin.
However, it has a few defining and unique characteristics.

*	 *Memorable URL's*
	 
    We use the wordnik API to generate a memorable URL, 
    not a random number sequence
*	 *Opensource (obviously)*
*	 *Automatic syntax highlighting*
*	 *Advanced and usable code editor, not a textarea*
	 
    We use CodeMirror, a popular JavaScript code editor with built in syntax highlighting and auto-indentation
*	 *Simple, streamlined user interface*

    Programmers are notorious for designing terrible interfaces, but we think we did a pretty good job with this one
*	*Significantly enhances your vocabulary*

    Since every upload is linked to a unique word, hopefully you'll learn some new terms to flaunt! :D


Technology
-----------
Snippet Uploader is built to scale: it uses the [Tornado Web Framework](http://www.tornadoweb.org) to serve dynamic content.

We also use [MongoDB](http://www.mongodb.org) to store all of our data.

In the production branch, we implement the [nginx](http://nginx.org) web server to serve static files, and the nginx upload module to handle file uploads.

Install and Production
---------------

To install, just download the tarball, cd to the directory, and 

    python server.py

Make sure you have tornado installed, and mongod running on localhost:27017

If you choose to run this app in production, you should load balance behind nginx, and use the nginx upload module.
The tornado support for the upload module is located in the production branch, but the branch doesn't work out of the box, as it requires
a specific nginx configuration. If you would like to see our config file, send me an email at [hunterlang#comcast.net](mailto:hunterlang@comcast.net)

