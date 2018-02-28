# -*- coding: utf-8 -*-
import sys
import xbmcplugin
from resources.lib.actions import *

params = get_params()
action = params.get("action")
id = params.get("id")

if action == None: 
  show_categories()
elif action == 'show_channels':
  show_channels(id)
elif action == 'show_streams':
  show_streams(id)
elif action == 'update_tvdb':
  update_tvdb()
elif action == 'play_channel':
  play_channel(id)
else:
  generate_playlist()

xbmcplugin.endOfDirectory(int(sys.argv[1]))