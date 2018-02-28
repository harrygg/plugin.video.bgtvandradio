# -*- coding: utf-8 -*-
from xbmc import executebuiltin, Monitor
from resources.lib.server import create_server
from resources.lib.wsgi_app import *
from kodibgcommon.utils import get_addon_id, settings

executebuiltin('RunPlugin("plugin://%s/?action=generate_playlist")' % get_addon_id())

monitor = Monitor()

httpd = create_server('0.0.0.0', app, port=port)
httpd.timeout = 0.1
starting = True

while not monitor.abortRequested():
  httpd.handle_request()
  if starting:
    notify_success("%s started on port %s" % (get_addon_id(), port))
    starting = False

httpd.socket.close()
settings.first_request_sent = False
log("%s started listening on %s" % (get_addon_id(), port))