Snippet Uploader
=================

General
-------

This is a tornado application that functions as a pastebin.
However, it has a few defining characteristics.

*	 <b>Live Collaboration</b>

	 Easy to collaborate in real time on a snippet.

*	 <b>Memorable URL's</b>
	 
    We use a custom wrapper around the [Wordnik](http://www.wordnik.com) API to generate a memorable URL, 
    not a random number sequence.

*	 <b>Side-by-side Comparison</b>
	 
 	View two snippets right next to each other for maximum comparison functionality.

*	 <b>Github-style Forking</b>
	 
    All snippets can be forked by other users, allowing them to create their own unique versions of a snippet.

*	 <b>Advanced and usable code editor, _not_ a &lt;textarea&gt;</b>
	 
    We use [CodeMirror](http://codemirror.net), a popular JavaScript code editor with built in syntax highlighting and auto-indentation.
*	 <b>Simple, streamlined user interface</b>

    Programmers are notorious for designing terrible interfaces, but we think we did a decent job with this one.
*	<b>Significantly enhances your vocabulary</b>

    Since every snippet is linked to a unique word, hopefully you'll learn some new terms to flaunt! :D

*	 <b>Open source (obviously)</b>
*	 <b>Automatic syntax highlighting</b>



Technology and Infrastructure
-----------
Snippet Uploader uses the [Tornado Web Framework](http://www.tornadoweb.org) to serve dynamic content.

It also uses [MongoDB](http://www.mongodb.org) to store all of the data.

In the production branch, we implement the [nginx](http://nginx.org) web server to serve static files, and the nginx upload module to handle file uploads.

Our production infrastructure is as follows:
![Infrastructure Diagram](http://snip.hunterlang.com/static/img/diagram2.png)