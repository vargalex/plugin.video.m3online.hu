# -*- coding: utf-8 -*-
'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


from __future__ import absolute_import, unicode_literals
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcplugin, PY2
import sys
from datetime import datetime, timedelta
import time
import re
from resources.lib import client
from resources.lib import parser

try:
    from urlparse import parse_qsl
    from urllib import quote_plus, unquote_plus
except:
    from urllib.parse import parse_qsl, quote_plus, unquote_plus

if PY2:
    bstring = basestring
else:
    bstring = str

_url = sys.argv[0]
_handle = int(sys.argv[1])
__addon__ = xbmcaddon.Addon()
__addon__.setSetting('ver', __addon__.getAddonInfo('version'))
_addonFanart = __addon__.getAddonInfo('fanart')
SITE_URL = 'https://archivum.mtva.hu/'


def root():
    liveMeta = getLivemeta()
    addDirectoryItem('[B]M3  -  ' + liveMeta['title'] + '[/B]  ' + liveMeta['playtime'], 'play&live=true', liveMeta['poster'], isFolder=False, meta=liveMeta)
    addDirectoryItem(u'Visszanézhető műsorok', 'playlist', 'DefaultMovies.png')
    addDirectoryItem(u'Szabadon elérhető műsorok', 'open_media', 'DefaultMovies.png') #TEMPORARY FREE MEDIA
    xbmcplugin.setContent(_handle, 'videos')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)


def getPlaylist():
    programs = getPrograms()
    for item in programs:
        meta = parseMeta(item)
        label = meta['title'] + ' - ' + meta['tagline'] if not meta['tagline'] == '' else meta['title']
        addDirectoryItem(label, 'play&filename=%s&subtitle=%s' % (meta['filename'], meta['hasSubtitle']), meta['poster'], isFolder=False, meta=meta)
    xbmcplugin.setContent(_handle, 'videos')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)


def play(filename, hasSubtitle, isLive):
    target = 'live' if isLive else filename
    streamData = client.request(SITE_URL + 'm3/stream?no_lb=1&target=' + target, headers={'Referer': SITE_URL + 'm3'}, XHR=True)

    PROTOCOL = 'hls'
    KODI_VERSION_MAJOR = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])

    from inputstreamhelper import Helper
    is_helper = Helper(PROTOCOL)
    if is_helper.check_inputstream():
        play_item = xbmcgui.ListItem(path=streamData['url'])
        play_item.setMimeType('application/dash+xml')
        play_item.setContentLookup(False)

        if KODI_VERSION_MAJOR >= 19:
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
        else:
            play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)

        play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)

        if hasSubtitle:
            play_item.setSubtitles([SITE_URL + 'subtitle/' + filename + '.srt'])

        xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

        for i in range(0, 240):
            if xbmc.Player().isPlaying(): break
            xbmc.Monitor().waitForAbort(1)

        showSubtitle = hasSubtitle and __addon__.getSetting('showSubtitle') == 'true'
        xbmc.Player().showSubtitles(showSubtitle)
    
        if isLive:
            while not xbmc.Monitor().abortRequested() and xbmc.Player().isPlaying():
                try:
                    meta = getLivemeta()
                    actFile = meta['filename']
                    try: playFile = live_item.getProperty('filename')
                    except: playFile = ''
                    if actFile == playFile: raise Exception()
                    live_item = xbmcgui.ListItem()
                    live_item.setPath(xbmc.Player().getPlayingFile())
                    live_item.setArt({'icon': meta['poster']})
                    live_item.setInfo('video', meta)
                    live_item.setProperty('filename', actFile)
                    xbmc.Player().updateInfoTag(live_item)
                    xbmcgui.Dialog().notification(u'Aktu\u00E1lis m\u0171sor', meta['title'], xbmcgui.NOTIFICATION_INFO, 5000, sound=False)
                except:
                    pass
                xbmc.Monitor().waitForAbort(10)
          

def getPrograms(active=False):
    jsonData = client.request(SITE_URL + 'm3/daily-program', headers={'Referer': SITE_URL + 'm3'}, XHR=True, cache=True)
    programs = jsonData['program']
    if active:
        p_list = []
        dtnow = datetime.now()
        programs = [i for i in programs if 'start_startTime_dts' in i and i['start_startTime_dts'] != []]
        for item in programs:
            for pr in item['start_startTime_dts']:
                try:
                    t = datetime.strptime(pr, '%Y-%m-%dT%H:%M:%SZ')
                except TypeError:
                    t = datetime(*(time.strptime(pr, '%Y-%m-%dT%H:%M:%SZ')[0:6]))
                p_list.append((item['id'], t))

        datesorted_list = sorted(p_list, key=lambda x: x[1])

        active_prog = [i for i in datesorted_list if i[1] <= dtnow][-1]
        return [i for i in programs if i['id'] == active_prog[0]][0]
    return programs


#######################################################################################################
# PARSE TEMPORARY FREE MEDIA
#######################################################################################################


def getOpenGenre():
    response = client.request(SITE_URL + 'm3/open', headers={'Referer': SITE_URL + 'm3'})
    result = parser.parseDOM(response, 'div', attrs={'class': 'dp-carousel-container'})
    
    for item in result:
        try:
            query = parser.parseDOM(item, 'div', ret='data-collection')[0]
            if query == 'most_viewed':
                title = parser.parseDOM(item, 'span')[0]
            else:
                title = parser.parseDOM(item, 'a')[0]
            title = re.sub('(\:\s*$)', '', title).encode('utf-8')
            query = parser.parseDOM(item, 'div', ret='data-collection')[0]
            url = SITE_URL + 'm3/get-open?collection=' + query
            addDirectoryItem(title, 'open_series&url={}'.format(url), 'DefaultMovies.png')
        except:
            pass

    xbmcplugin.setContent(_handle, 'videos')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=True)


def getOpenSeries(url):
    response = client.request(url, headers={'Referer': SITE_URL + 'm3/open'}, XHR=True)
    for item in response['docs']:
        try:
            meta = parseMeta(item)
            label = meta['title']
            if meta['isSeries'] == 'false' or 'most_viewed' in url:
                label = label + ' - ' + meta['tagline'] if not meta['tagline'] == '' else label
                addDirectoryItem(label, 'play&filename=%s&subtitle=%s' % (meta['filename'], meta['hasSubtitle']), meta['poster'], isFolder=False, meta=meta)
            else:
                addDirectoryItem(label, 'open_episodes&seriesid={}'.format(meta['seriesId']), meta['poster'], meta=meta)
        except: pass
    xbmcplugin.setContent(_handle, 'videos')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)


def getOpenEpisodes(seriesId, page='1'):
    response = client.request(SITE_URL + 'm3/open?series={0}&page={1}'.format(quote_plus(seriesId), page), headers={'Referer': SITE_URL + 'm3/open'})    
    result = parser.parseDOM(response, 'div', attrs={'class': 'row mb-1'})
    for item in result:
        episode = parser.parseDOM(item, 'p')[0]
        title = parser.parseDOM(item, 'h5')[0]
        plot = parser.parseDOM(item, 'p')[1]
        img = parser.parseDOM(item, 'div', ret='style')[0]
        img = re.search('(http[s]?://[^\)]+)', img).group(1)
        filename = img.rsplit('/', 1)[-1]
        inner = parser.parseDOM(item, 'span')
        try: mpaa = inner[0]
        except: mpaa = ''
        if mpaa.isdigit(): mpaa = 'PG-' + mpaa
        try: hasSubtitle = 'true' if inner[1].lower() == 'cc' else 'false'
        except: hasSubtitle = 'false'
        addDirectoryItem(title, 'play&filename={0}&subtitle={1}'.format(filename, hasSubtitle), img, isFolder=False, meta={'title': title, 'poster': img, 'plot': plot, 'mpaa': mpaa})
    
    try:
        nbuttons = parser.parseDOM(response, 'div', {'class': 'btn-group btn-group-xs'})
        pages = [int(i) for i in parser.parseDOM(nbuttons, 'a') if i.isdigit()]
        if int(page) < max(pages):
            addDirectoryItem(u'K\u00F6vetkez\u0151 oldal  ({0}/{1})'.format(page, str(max(pages))), 'open_episodes&seriesid={0}&page={1}'.format(seriesId, str(int(page)+1)), 'DefaultTVShows.png')
    except:
        pass
    
    xbmcplugin.setContent(_handle, 'videos')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)


#######################################################################################################
# END PARSE TEMPORARY FREE MEDIA
#######################################################################################################


def parseMeta(item, isLive=False):
    title = item['title']
    try: plot = item['description']
    except: plot = ''
    try: tagline = item['subtitle'] if 'subtitle' in item and isinstance(item['subtitle'], bstring) else ''
    except: tagline = ''
    try: cast = item['creators']
    except: cast = []
    try: country = item['country']
    except: country = ''
    id = item['id']
    img = SITE_URL + 'images/m3/' + id
    try: duration = item['duration'].split(':')[:3]
    except: duration = ''
    if isLive:
        dtnow = datetime.now()
        start_times = []
        for i in item['start_startTime_dts']:
            try:
                t = datetime.strptime(i, '%Y-%m-%dT%H:%M:%SZ')
            except TypeError:
                t = datetime(*(time.strptime(i, '%Y-%m-%dT%H:%M:%SZ')[0:6]))
            start_times.append(t)
        start_times = sorted(start_times)
        t1 = [i for i in start_times if dtnow > i][-1]
        h,m,s = duration
        td = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
        t2 = t1 + td

        strt1 = datetime.strftime(t1, '%H:%M')
        strt2 = datetime.strftime(t2, '%H:%M')
    try:
        if isLive == True: raise Exception()
        duration = sum(x * int(t) for x, t in zip([3600, 60, 1], duration))
    except: duration = '0'
    try: year = item['year']
    except: year = ''
    try: mpaa = item['pg']
    except: mpaa = ''
    if mpaa.isdigit(): mpaa = 'PG-' + mpaa
    try: genre = item['genre']
    except: genre = ''
    hasSubtitle = 'true' if item['hasSubtitle'] else 'false'
    try: isSeries = 'true' if item['isSeries'] == True else 'false'
    except: isSeries = 'false'
    seriesId = item['seriesId'] if isSeries == 'true' else ''
    
    meta = {'title': title, 'plot': plot, 'tagline': tagline, 'year': year, 'duration': duration, 'mpaa': mpaa, 'genre': genre, 'cast': cast, 'mediatype': 'video', 'poster': img, 'filename': id, 'hasSubtitle': hasSubtitle, 'isSeries': isSeries, 'seriesId': seriesId}
    
    if isLive:
        meta.update({'playtime': '[{0} - {1}]'.format(strt1, strt2)})
    
    return meta


def getLivemeta():
    data = getPrograms(active=True)
    return parseMeta(data, isLive=True)


def addDirectoryItem(name, query, icon, context=None, queue=False, isFolder=True, meta=None):
    url = '%s?action=%s' % (_url, query)
    isPlayable = 'true' if isFolder == False else 'false'
    cm = []
    if queue == True: cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % _url))
    if not context == None: cm.append((context[0], 'RunPlugin(%s?action=%s)' % (_url, context[1])))
    item = xbmcgui.ListItem(label=name)
    item.addContextMenuItems(cm)
    item.setArt({'icon': icon, 'poster': icon})
    item.setProperty('Fanart_Image', _addonFanart)
    item.setProperty('IsPlayable', isPlayable)
    if meta:
        meta.pop('filename', None)
        meta.pop('seriesid', None)
        meta.pop('poster', None)
        meta.pop('isseries', None)
        meta.pop('hassubtitle', None)
        item.setInfo(type='video', infoLabels = meta)
    xbmcplugin.addDirectoryItem(handle=_handle, url=url, listitem=item, isFolder=isFolder)


if __name__ == '__main__':
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get('action')
    live = params.get('live', 'false') == 'true'
    filename = params.get('filename')
    subtitle = params.get('subtitle', 'false') == 'true'
    seriesId = params.get('seriesid')
    url = params.get('url')
    page = params.get('page', '1')
  
    if not action:
        root()
    elif action == 'playlist':
        getPlaylist()
    elif action == 'play':
        play(filename, subtitle, live)
    elif action == 'open_media':
        getOpenGenre()
    elif action == 'open_series':
        getOpenSeries(url)
    elif action == 'open_episodes':
        getOpenEpisodes(seriesId, page)
