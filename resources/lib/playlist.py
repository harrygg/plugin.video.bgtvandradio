# -*- coding: utf8 -*-
import os
import re
import sys
import json
import urllib
from kodibgcommon.utils import log, settings
import requests

reload(sys)  
sys.setdefaultencoding('utf8')

class Playlist:
  name = 'playlist.m3u'
  channels = []
  raw_m3u = None
  append = True
  include_radios = True
  
  def __init__(self, include_radios = True, name = ''):
    if name != '':
      self.name = name
    self.include_radios = include_radios
  
  def save(self, path, type="to_string"):
    if type == "to_string":
      file_path = os.path.join(path, self.name)
    else:
      file_path = os.path.join(path, '.playlist')
      
    log("Запазване на плейлистата: %s " % file_path)
    if os.path.exists(path):
      with open(file_path, 'w') as f:
        if type == "to_string":
          content = self.to_string().encode('utf-8', 'replace')
        else:
          content = json.dumps(self.to_json(), ensure_ascii=False)
        f.write(content)
        
  
  def concat(self, new_m3u, append = True, raw = True):
    if raw: #TODO implement parsing playlists
      self.append = append
      if os.path.isfile(new_m3u):
        with open(new_m3u, 'r') as f:
          self.raw_m3u = f.read().replace('#EXTM3U', '')
      elif new_m3u:
        self.raw_m3u = new_m3u.replace('#EXTM3U', '')
 
  def set_static_stream_urls(self):
    '''
    Replaces all stream urls with static ones
    That point to our proxy server
    '''
    port = settings.port
    channels_dict = self.to_json()
    for channel in self.channels:
      name = urllib.quote(channel.name.encode("utf-8"))
      channel.playpath = 'http://127.0.0.1:%s/plugin.video.freebgtvs/stream/%s' % (port, name)
      if channels_dict.get(channel.name) and channels_dict[channel.name].get("useragent"):
        channel.playpath += "|User-Agent=%s" % channels_dict[channel.name].get("useragent")
 
  def to_string(self):
    output = ''
    for channel in self.channels:
      if not self.include_radios and channel.is_radio:
        continue
      output += channel.to_string()
      
    if self.raw_m3u != None:
      if self.append:
        output += self.raw_m3u
      else:
        output = self.raw_m3u + output
    
    return '#EXTM3U\n' + output
    
  def to_json(self):
    '''
    returns a dict of all channels
    '''
    channels = {}
    useragent = None
    for channel in self.channels:
      split = channel.playpath.split("|User-Agent=")
      if len(split) > 1:
        playpath = split[0]
        useragent = split[1]
      channels[channel.name] = {"name": channel.name, "playpath": playpath, "useragent": useragent}
    return channels
    
class Channel:
  id = None
  disabled = False
  name = None
  category = None
  streams = 1
  playpath = None
  epg_id = None
  user_agent = None
  is_radio = False
  
  def __init__(self, attr = False):
    if attr:
      self.id = attr[0]
      self.disabled = attr[1] == 1
      self.name = attr[2]
      self.category = attr[3]
      self.is_radio = True if self.category == "Радио" else False
      self.logo = attr[4]
      self.streams = attr[5]
      self.playpath = '' if attr[6] == None else attr[6]
      self.epg_id = '' if attr[9] == None else attr[9]
      self.user_agent = False if attr[10] == None else attr[10]

  def to_string(self):
    output = '#EXTINF:-1 radio="%s" tvg-shift=0 group-title="%s" tvg-logo="%s" tvg-id="%s",%s\n' % (self.is_radio, self.category, self.logo, self.epg_id, self.name)
    output += '%s\n' % self.playpath
    return output

 
class Stream:
  def __init__(self, attr):
    self.id = attr[0] 
    self.channel_id = attr[1] 
    self.url = attr[2]
    self.page_url = attr[3]
    self.player_url = attr[4]
    self.disabled = attr[5] == 1
    self.comment = attr[6]
    self.user_agent = False if attr[9] == None else attr[9]
    if self.url == None:
      self.url = self.resolve()
    else:
      log('Извлечен видео поток %s' % self.url)
    if self.url != '' and self.user_agent: 
      self.url += '|User-Agent=%s' % self.user_agent

  def resolve(self):
    headers = {'User-agent': self.user_agent, 'Referer':self.page_url}
    res = requests.get(self.player_url, headers=headers)
    m = re.compile('(//.*\.m3u.*?)[\s\'"]+').findall(res.text)
    if len(m) == 0:
        log(res.text)
    else:
      if not m[0].startswith("http:") and not m[0].startswith("https:"): #some links omit the http prefix
        m[0] = "http:" + m[0]
    log('Намерени %s съвпадения в %s' % (len(m), self.player_url))
    stream = None if len(m) == 0 else m[0]
    log('Извлечен видео поток %s' % stream)
    return stream
