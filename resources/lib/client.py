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
from kodi_six import xbmc, xbmcvfs, xbmcaddon
import os
import requests
import requests_cache

try:
    transPath = xbmcvfs.translatePath
except:
    transPath = xbmc.translatePath

addon = xbmcaddon.Addon()
addonUserDataFolder = transPath(addon.getAddonInfo('profile'))
CACHE_FILE = os.path.join(addonUserDataFolder, 'requests_cache')

def request(url, headers=None, XHR=False, cache=False):

    requests_cache.install_cache(CACHE_FILE, backend='sqlite', expire_after=3600)

    if url == 'clear_cache':
        requests_cache.clear()
        return

    try: headers.update(headers)
    except: headers = {}
    if 'User-Agent' in headers:
        pass
    else:
        headers['User-Agent'] = get_user_agent()
    if not 'Accept-Language' in headers:
        headers['Accept-Language'] = 'en-US'
    if 'X-Requested-With' in headers:
        pass
    elif XHR == True:
        headers['X-Requested-With'] = 'XMLHttpRequest'

    if cache == False:
        with requests_cache.disabled():
            response = requests.get(url, headers=headers)
    else:
        response = requests.get(url, headers=headers)

    if XHR == True:
        result = response.json()
    else:
        result = response.text

    return result


def get_user_agent():
    return 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0'
