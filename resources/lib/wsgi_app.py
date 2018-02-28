# -*- coding: utf-8 -*-
import os
import re
import json
import requests
from kodibgcommon.utils import *
from urllib import unquote
from bottle import route, default_app, request, HTTPResponse

__DEBUG__ = False
app       = default_app()
port      = int(settings.port)

@route('/%s/playlist' % get_addon_id(), method='GET')
def get_playlist():
  """
    Displays the m3u playlist
    :return: m3u
  """
  headers = {}
  log("get_playlist() started")
  to_json = request.query.get("json")
  if to_json:
    log("to_json: True")
    try:
      with open(os.path.join(get_profile_dir(), '.playlist')) as f:
        body = f.read()
        headers["Content-Type"] = "application/json"
    except Exception as er:
      body = str(er)
      log(er)  
  else:
    body = "#EXTM3U\n"
    try:
      with open(os.path.join(get_profile_dir(), 'playlist.m3u')) as f:
        body = f.read() 
    except Exception as er:
      body = str(er)
      log(er)
 
    if request.query.get("debug"):
      body = "<pre>" + body + "</pre>"
    else:
      headers['Content-Type'] = "audio/mpegurl"
    
  log("get_playlist() ended")
  
  return HTTPResponse(body, 
                      status=200, 
                      **headers)

@route('/%s/stream/<name>' % get_addon_id(), method='HEAD')
def get_stream(name):
  headers = {"Content-Type": "audio/mpegurl"}
  return HTTPResponse(None, 
                      status=200
                      **headers)


@route('/%s/stream/<name>' % get_addon_id(), method='GET')
def get_stream(name):
  '''
    Get the m3u stream url
    Returns 302 redirect
  '''
  headers  = {}
  body     = None
  location = None

  log("get_stream() started.")
  log("User-agent header: %s" % request.headers.get("User-Agent"))
  try:
    is_tvheadend = "TVHeadend" in request.headers.get("User-Agent")
  except:
    is_tvheaded = False
  ### Kodi 17 sends 2 GET requests for a resource which may cause
  ### stream invalidation on some middleware servers. If this is
  ### the first request return a dummy response and handle the 2nd
  log("Is TV Headned: %s" % is_tvheadend)
  if not is_tvheadend and get_kodi_major_version() == 17 and not settings.first_request_sent:
    settings.first_request_sent = True
    headers = {"Content-Type": "audio/mpegurl"}
    log("get_stream() ended. First request handled!")
    return HTTPResponse(body, 
                      status = 200,
                      **headers)
  
  ### If this is the 2nd request by the player
  ### redirect it to the original stream  
  settings.first_request_sent = False

  try:  
    stream_name = unquote(name)
    try:
      # deserialize streams
      file = os.path.join(get_profile_dir(), '.playlist')
      streams = json.load(open(file))
      log("Deserialized %s streams from file %s" % (len(streams), file))
      stream = streams.get(name.decode("utf-8"))
      if stream:
        location = stream["playpath"]
        log("Found location: %s" % location)
    except Exception as er:
      log(er)
    
    if not location:
      notify_error('Channel %s not found' % name)
      return HTTPResponse(body, 
                          status = 404)

    if __DEBUG__:
      notify("URL found for stream %s: %s" % (stream_name, location))
      log("get_stream() ended!")
      return HTTPResponse(location,
                          status = 200)
                      
    headers['Location'] = location

  except Exception as er:
    body = str(er)
    log(str(er), 4)
    
  log("get_stream() ended!")
  return HTTPResponse(body, 
                      status = 302, 
                      **headers)