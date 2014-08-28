pyrequest
===

HTTP GET/POST function based on Python 2

####Forked form MultipartPostHandler and thanks for their great work!
####Feature: Simple interface and supports Non-ASCII values/dict and filenames well.
####Author: lemori@foxmail.com
```
Usage:
    webutil.request(url, data=None, has_files=False|True)
When has_files is False:
    data can be a relatively complicated structure, e.g.
    { "user": { "name": "bob", "age": "18"},
        "colors": ["red", "blue", "green"] }
When has_files is True:
    it POST with contenttype = multipart/form-data
    and data should be a simple dict, e.g.
    { "username" : "bob", "password" : "riviera",
        "file" : open("filepath", "rb") }
When data is None and has_files is False:
    it GET resources from the url
```
