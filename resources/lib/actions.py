import os
import sys
import time
import xbmc
import sqlite3
from assets import Assets
from playlist import *
from kodibgcommon.utils import *
from xbmcplugin import setResolvedUrl, endOfDirectory
from xbmcgui import ListItem, Dialog, DialogProgressBG

if settings.use_local_db and settings.db_file_path != '' and os.path.isfile(settings.db_file_path):
  db_file = settings.db_file_path
else:
  db_file = os.path.join( get_profile_dir(), 'tv.db' )
backup_db_file = os.path.join( get_resources_dir() , 'tv.db' )

def show_categories():
  update('browse', 'Categories')
  log("Loading data from DB file: %s" % db_file)
  
  try:
    conn = sqlite3.connect(db_file)
    cursor = conn.execute('''SELECT * FROM categories''')
    
    li = ListItem('Всички')
    url = make_url({"id": 0, "action": "show_channels"})
    add_listitem_folder(li, url) 

    #Add categories
    for row in cursor:
      li = ListItem(row[1])
      url = make_url({"id": row[0], "action": "show_channels"})
      add_listitem_folder(li, url) 
  
    li = ListItem('******** Обнови плейлиста ********')
    url = make_url({"action": "generate_playlist"})
    add_listitem(li, url)
    
  except sqlite3.DatabaseError:
    notify_error("Файлът с базата данни е повреден!")
    log_last_exception()

  except Exception as er:
    notify_error(er)
    log_last_exception()
  
  if not settings.use_local_db:
    li = ListItem('******** Обнови базата данни ********')
    url = make_url({"action": "update_tvdb"})
    add_listitem(li, url)
  
  endOfDirectory(addon_handle)

def show_channels(id):
  channels = get_channels(id)
  for c in channels:      
    if c.disabled:
      c.name = '[COLOR brown]%s[/COLOR]' % c.name
    playable = c.streams == 1 and c.playpath != ''
    li = ListItem(c.name, iconImage = c.logo, thumbnailImage = c.logo)
    li.setInfo( type = "Video", infoLabels = { "Title" : c.name } )
    li.setProperty("IsPlayable", str(playable))
    # self.playable = False if self.streams > 1 or self.player_url != '' else True

    if playable:
      url = c.playpath
    else:
      url_items = {"id": c.id, "action": "show_streams"}
      url = make_url(url_items)
    
    add_listitem_folder(li, url)

def get_channels(id):
  log("Getting channel with id: %s" % id)
  channels = []
  
  try:
    conn = sqlite3.connect(db_file)
    sign = "="
    no_radio_rule = ""
    
    if id == str(0):
      sign = "<>"
      no_radio_rule = "AND c.category_id <> 7"
    
    disabled_query = '''AND s.disabled = 0''' if not settings.show_disabled else ''

    query = '''
    SELECT c.id, c.disabled, c.name, cat.name AS category, c.logo, COUNT(s.id) AS streams, s.stream_url, s.page_url, s.player_url, c.epg_id, u.string, c.ordering
    FROM channels AS c 
    JOIN streams AS s ON c.id = s.channel_id 
    JOIN categories as cat ON c.category_id = cat.id
    JOIN user_agents as u ON u.id = s.user_agent_id
    WHERE c.category_id %s %s %s %s
    GROUP BY c.id, c.name 
    ORDER BY c.ordering''' % (sign, id, no_radio_rule, disabled_query)
    
    cursor = conn.execute(query)
    
    for row in cursor:
      c = Channel(row)
      channels.append(c)
      
  except Exception, er:
    log_last_exception()
    notify_error(er)
    
  return channels

def show_streams(id):

  streams = get_streams(id)
  select = 0

  if len(streams) > 1:
    dialog = Dialog()
    select = dialog.select('Изберете стрийм', [s.comment for s in streams])
    if select == -1: 
      return False

  url = streams[select].url
  log('resolved url %s' % url)

  item = ListItem(path=url)
  item.setInfo( type = "Video", infoLabels = { "Title" : ''} )
  item.setProperty("IsPlayable", str(True))
  
  setResolvedUrl(handle = addon_handle, 
                succeeded = True, 
                listitem = item)
  
def get_streams(id):
  streams = []

  try:
    conn = sqlite3.connect(db_file)
    query = '''SELECT s.*, u.string AS user_agent FROM streams AS s JOIN user_agents as u ON s.user_agent_id==u.id WHERE channel_id=%s''' % id
    if not settings.show_disabled:
     query += ''' AND s.disabled=0''' 
    cursor = conn.execute(query)
    
    for row in cursor:
      c = Stream(row)
      streams.append(c)

  except Exception, er:
    log_last_exception()
    notify_error(er)
    
  return streams  

def play_channel(channel_id, stream_index = 0):
  urls = get_streams(id)
  s = urls[stream_index]
  
  li = ListItem(s.name, iconImage=s.logo, thumbnailImage=s.logo, path=s.stream_url)
  li.setInfo( type = "Video", infoLabels = { "Title" : s.name } )
  li.setProperty("IsPlayable", 'True')
  
  setResolvedUrl(handle = addon_handle, 
                succeeded = True, 
                listitem = li)
  
def update(name, location, crash=None):
  lu = settings.last_update
  day = time.strftime("%d")
  if lu == "" or lu != day:
    import ga
    settings.last_update = day
    p = {}
    p['an'] = get_addon_name()
    p['av'] = get_addon_version()
    p['ec'] = 'Addon actions'
    p['ea'] = name
    p['ev'] = '1'
    p['ul'] = xbmc.getLanguage()
    p['cd'] = location
    ga.ga('UA-79422131-7').update(p, crash)

def update_tvdb():
  progress_bar = DialogProgressBG()
  progress_bar.create(heading="Downloading database...")
  msg = "Базата данни НЕ бе обновена!"
  try:
    log('Force-updating tvdb')
    # recreated the db_file in case db_file is overwritten by use_local_db
    __db_file__ = os.path.join( get_resources_dir(), 'tv.db' )
    asset = Assets( __db_file__, backup_db_file )
    progress_bar.update(1, "Downloading database...")
    
    errors = asset.update(settings.url_db)
    if errors:
      notify_error(msg + "\n" + errors)
      
    if settings.use_local_db:
      notify_success("Използвате локална база данни!")

  except Exception as ex:
    log(ex, 4)
  
  if progress_bar:
    progress_bar.close()
  
def generate_playlist():
  '''
  Function executed by scheduler to generate a playlist
  ''' 
  progress_bar = DialogProgressBG()
  debug = settings.debug
  is_manual_run = False if len(sys.argv) > 1 and sys.argv[1] == 'False' else True

  if not is_manual_run:
    log('Автоматично генериране на плейлиста')

  if debug or is_manual_run:
    progress_bar.create( heading = get_addon_name() )

  def show_progress(percent, msg):
    if debug or is_manual_run:
      heading = "%s %s%%" % (get_addon_name().encode('utf-8'), str(percent))
      progress_bar.update(percent, heading, msg)
      log(msg)
  
  try:  
    if not settings.use_local_db:
      asset = Assets(db_file, backup_db_file)
      if asset.is_old():
        errors = asset.update(settings.url_db)
        if errors:
          notify_error('Базата данни не бе обновена! %s' % errors)      

    show_progress(10, 'Зареждане на канали от базата данни %s ' % db_file)

    conn = sqlite3.connect(db_file)
    cursor = conn.execute(
      '''SELECT c.id, c.disabled, c.name, cat.name AS category, c.logo, 
        COUNT(s.id) AS streams, s.stream_url, s.page_url, s.player_url, c.epg_id, u.string, c.ordering 
      FROM channels AS c 
      JOIN streams AS s ON c.id = s.channel_id 
      JOIN categories as cat ON c.category_id = cat.id
      JOIN user_agents as u ON u.id = s.user_agent_id
      WHERE c.disabled <> 1
      GROUP BY c.name, c.id
      ORDER BY c.ordering''')
      
    show_progress(20,'Генериране на плейлиста')
    update('generation', 'PlaylistGenerator')

    pl = Playlist(settings.include_radios)
    show_progress(25,'Търсене на потоци')
    n = 26

    for row in cursor:
      try:
        c = Channel(row)
        n += 1
        show_progress(n,'Търсене на поток за канал %s' % c.name)

        cursor = conn.execute(
          '''SELECT s.*, u.string AS user_agent 
          FROM streams AS s 
          JOIN user_agents as u ON s.user_agent_id == u.id 
          WHERE disabled <> 1 AND channel_id = %s AND preferred = 1''' % c.id)
        s = Stream(cursor.fetchone())
        
        c.playpath = s.url
        if c.playpath is None:
          xbmc.log('Не е намерен валиден поток за канал %s ' % c.name)
        else:
          pl.channels.append(c)
          
      except Exception, er:
        xbmc.log('Грешка при търсене на поток за канал %s ' % c.name)
        log_last_exception()
        
    show_progress(90,'Записване на плейлиста')
    pl.save(get_profile_dir())

    ###################################################
    ### Apend/Prepend another playlist if specified
    ###################################################
    apf = settings.additional_playlist_file
    # if settings.concat_playlist and os.path.isfile(apf):
      # show_progress(92,'Обединяване с плейлиста %s' % apf)
      # pl.concat(apf, settings.append == '1')
      # pl.save(get_profile_dir())
      
    ###################################################
    ### Copy playlist to additional folder if specified
    ###################################################
    ctf = settings.copy_to_folder
    if settings.copy_playlist and os.path.isdir(ctf):
      show_progress(95,'Копиране на плейлиста')
      pl.save(ctf)

    ####################################################
    ### Set next run
    ####################################################
    show_progress(98,'Генерирането на плейлистата завърши!')
    roi = int(settings.run_on_interval) * 60
    show_progress(99,'Настройване на AlarmClock. Следващото изпълнение на скрипта ще бъде след %s часа' % (roi / 60))
    command = "plugin://%s/?action=generate_playlist" % get_addon_id()
    xbmc.executebuiltin('AlarmClock(%s, RunScript(%s, False), %s, silent)' % (get_addon_id(), command, roi))
  
  except:
    log_last_exception()
    
  if progress_bar:
    progress_bar.close()