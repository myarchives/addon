# -*- coding: utf-8 -*-

import sys
PY3 = False
if sys.version_info[0] >= 3: PY3 = True; unicode = str; unichr = chr; long = int

if PY3:
    import urllib.parse as urlparse                             # Es muy lento en PY2.  En PY3 es nativo
else:
    import urlparse                                             # Usamos el nativo de PY2 que es más rápido

import re
import time
import traceback

from channelselector import get_thumb
from core import httptools
from core import scrapertools
from core import tmdb
from core.item import Item
from platformcode import config, logger
from lib import generictools
from channels import filtertools
from channels import autoplay


IDIOMAS = {'Castellano': 'CAST', 'Latino': 'LAT', 'Version Original': 'VO'}
list_language = list(IDIOMAS.values())
list_quality = []
list_servers = ['torrent']

host = 'https://cinetorrent.net/'
domain = 'cinetorrent.net'
channel = 'cinetorrent'
categoria = channel.capitalize()

__modo_grafico__ = config.get_setting('modo_grafico', channel)
modo_ultima_temp = config.get_setting('seleccionar_ult_temporadda_activa', channel) #Actualización sólo últ. Temporada?
timeout = config.get_setting('timeout_downloadpage', channel)
season_colapse = config.get_setting('season_colapse', channel)                  # Season colapse?
filter_languages = config.get_setting('filter_languages', channel)              # Filtrado de idiomas?


def mainlist(item):
    logger.info()
    itemlist = []
    
    thumb_cartelera = get_thumb("now_playing.png")
    thumb_pelis = get_thumb("channels_movie.png")
    thumb_pelis_hd = get_thumb("channels_movie_hd.png")
    thumb_pelis_VO = get_thumb("channels_vos.png")
    
    thumb_series = get_thumb("channels_tvshow.png")
    thumb_series_hd = get_thumb("channels_tvshow_hd.png")
    thumb_series_VOD = get_thumb("videolibrary_tvshow.png")
    
    thumb_documentales = get_thumb("channels_documentary.png")
    thumb_alfabeto = get_thumb("channels_movie_az.png")
    thumb_genero = get_thumb("genres.png")
    thumb_buscar = get_thumb("search.png")
    thumb_separador = get_thumb("next.png")
    thumb_settings = get_thumb("setting_0.png")
    
    autoplay.init(item.channel, list_servers, list_quality)
    
    itemlist.append(Item(channel=item.channel, title="Películas", action="listado", 
                url=host + "peliculas/page/1", thumbnail=thumb_pelis, extra="peliculas"))
    itemlist.append(Item(channel=item.channel, title="    - por Género", action="genero", 
                url=host, thumbnail=thumb_pelis, extra="peliculas"))
    itemlist.append(Item(channel=item.channel, title="    - por Año", action="anno", 
                url=host, thumbnail=thumb_pelis, extra="peliculas"))
    itemlist.append(Item(channel=item.channel, title="    - por Calidad", action="calidad", 
                url=host, thumbnail=thumb_pelis, extra="peliculas"))
    
    itemlist.append(Item(channel=item.channel, title="Series", action="listado", 
                url=host + "series/page/1", thumbnail=thumb_series, extra="series"))
    itemlist.append(Item(channel=item.channel, title="    - por Año", action="anno", 
                url=host, thumbnail=thumb_pelis, extra="series"))
    
    itemlist.append(Item(channel=item.channel, title="Buscar...", action="search",
                url=host, thumbnail=thumb_buscar, extra="search"))

    itemlist.append(Item(channel=item.channel, url=host, title="[COLOR yellow]Configuración:[/COLOR]", 
                folder=False, thumbnail=thumb_separador))
    itemlist.append(Item(channel=item.channel, action="configuracion", title="Configurar canal", 
                thumbnail=thumb_settings))
    
    autoplay.show_option(item.channel, itemlist)                                #Activamos Autoplay

    return itemlist
    
    
def configuracion(item):
    from platformcode import platformtools
    ret = platformtools.show_channel_settings()
    platformtools.itemlist_refresh()
    return


def anno(item):
    logger.info()
    from platformcode import platformtools
    
    itemlist = []

    year = platformtools.dialog_numeric(0, "Introduzca el Año de búsqueda", default="")
    item.url = '%syears/%s/page/1/' % (host, year)
    item.extra2 = 'anno' + str(year)

    return listado(item)

    
def genero(item):
    logger.info()
    itemlist = []

    patron = '<a class="dropdown-toggle header__nav-link"\s*href="#"\s*role="button"'
    patron += '\s*data-toggle="dropdown">Genero<\/a>\s*<ul class="dropdown-menu header__dropdown-menu">'
    patron += '\s*(.*?)\s*<\/ul>\s*<\/li>'

    data, success, code, item, itemlist = generictools.downloadpage(item.url, timeout=timeout,  s2=False, 
                                          patron=patron, item=item, itemlist=[])    # Descargamos la página

    #Verificamos si se ha cargado una página, y si además tiene la estructura correcta
    if not success or itemlist:                                                 # Si ERROR o lista de errores ...
        return itemlist                                                         # ... Salimos

    data = scrapertools.find_single_match(data, patron)
    patron = '<li><a\s*href="([^"]+)"\s*target="[^"]*">([^<]+)\s*<\/a>\s*<\/li>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    #logger.debug(patron)
    #logger.debug(matches)
    #logger.debug(data)

    if not matches:
        logger.error("ERROR 02: SUBMENU: Ha cambiado la estructura de la Web " + 
                        " / PATRON: " + patron + " / DATA: " + data)
        itemlist.append(item.clone(action='', title=item.category + 
                        ': ERROR 02: SUBMENU: Ha cambiado la estructura de la Web.  '
                        + 'Reportar el error con el log'))
        return itemlist                                         #si no hay más datos, algo no funciona, pintamos lo que tenemos

    for scrapedurl, gen in matches:
        itemlist.append(item.clone(action="listado", title=gen.capitalize(), url=scrapedurl + 'page/1/', 
                        extra2='genero'))

    return itemlist


def calidad(item):
    
    logger.info()
    itemlist = []

    patron = '<a class="dropdown-toggle header__nav-link"\s*href="#"\s*role="button"'
    patron += '\s*data-toggle="dropdown">CALIDAD\s*<\/a>\s*<ul class="dropdown-menu header__dropdown-menu">'
    patron += '\s*(.*?)\s*<\/ul>\s*<\/li>'

    data, success, code, item, itemlist = generictools.downloadpage(item.url, timeout=timeout,  s2=False, 
                                          patron=patron, item=item, itemlist=[])    # Descargamos la página

    #Verificamos si se ha cargado una página, y si además tiene la estructura correcta
    if not success or itemlist:                                                 # Si ERROR o lista de errores ...
        return itemlist                                                         # ... Salimos

    data = scrapertools.find_single_match(data, patron)
    patron = '<li><a\s*href="([^"]+)"\s*target="[^"]*">([^<]+)\s*<\/a>\s*<\/li>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    #logger.debug(patron)
    #logger.debug(matches)
    #logger.debug(data)

    if not matches:
        logger.error("ERROR 02: SUBMENU: Ha cambiado la estructura de la Web " + 
                        " / PATRON: " + patron + " / DATA: " + data)
        itemlist.append(item.clone(action='', title=item.category + 
                        ': ERROR 02: SUBMENU: Ha cambiado la estructura de la Web.  '
                        + 'Reportar el error con el log'))
        return itemlist                                         #si no hay más datos, algo no funciona, pintamos lo que tenemos

    for scrapedurl, cal in matches:
        itemlist.append(item.clone(action="listado", title=cal.capitalize(), url=scrapedurl + 'page/1/', 
                        extra2='calidad'))

    return itemlist


def listado(item):                                                              # Listado principal y de búsquedas
    logger.info()
    
    itemlist = []
    item.category = categoria
    thumb_pelis = get_thumb("channels_movie.png")
    thumb_series = get_thumb("channels_tvshow.png")

    #logger.debug(item)
    
    curr_page = 1                                                               # Página inicial
    last_page = 99999                                                           # Última página inicial
    if item.curr_page:
        curr_page = int(item.curr_page)                                         # Si viene de una pasada anterior, lo usamos
        del item.curr_page                                                      # ... y lo borramos
    if item.last_page:
        last_page = int(item.last_page)                                         # Si viene de una pasada anterior, lo usamos
        del item.last_page                                                      # ... y lo borramos
    
    cnt_tot = 30                                                                # Poner el num. máximo de items por página
    cnt_title = 0                                                               # Contador de líneas insertadas en Itemlist
    inicio = time.time()                                    # Controlaremos que el proceso no exceda de un tiempo razonable
    fin = inicio + 5                                                            # Después de este tiempo pintamos (segundos)
    timeout_search = timeout * 2                                                # Timeout para descargas
    if item.extra == 'search' and item.extra2 == 'episodios':                   # Si viene de episodio que quitan los límites
        cnt_tot = 999
        fin = inicio + 30

    #Sistema de paginado para evitar páginas vacías o semi-vacías en casos de búsquedas con series con muchos episodios
    title_lista = []                                        # Guarda la lista de series que ya están en Itemlist, para no duplicar lineas
    if item.title_lista:                                    # Si viene de una pasada anterior, la lista ya estará guardada
        title_lista.extend(item.title_lista)                                    # Se usa la lista de páginas anteriores en Item
        del item.title_lista                                                    # ... limpiamos
    matches = []
        
    if not item.extra2:                                                         # Si viene de Catálogo o de Alfabeto
        item.extra2 = ''
        
    post = None
    if item.post:                                                               # Rescatamos el Post, si lo hay
        post = item.post
    
    next_page_url = item.url
    # Máximo num. de líneas permitidas por TMDB. Máx de 5 segundos por Itemlist para no degradar el rendimiento
    while (cnt_title < cnt_tot and curr_page <= last_page and fin > time.time()) or item.matches:
    
        # Descarga la página
        data = ''
        cnt_match = 0                                                           # Contador de líneas procesadas de matches
        
        if not item.matches:                                                    # si no viene de una pasada anterior, descargamos
            data, success, code, item, itemlist = generictools.downloadpage(next_page_url, 
                                          timeout=timeout_search, post=post, s2=False, 
                                          item=item, itemlist=itemlist)         # Descargamos la página)
            
            # Verificamos si se ha cargado una página correcta
            curr_page += 1                                                      # Apunto ya a la página siguiente
            if not data or not success:                                         # Si la web está caída salimos sin dar error
                if len(itemlist) > 1:                                           # Si hay algo que pintar lo pintamos 
                    last_page = 0
                    break
                return itemlist                                                 # Si no hay nada más, salimos directamente
        
        #Patrón para búsquedas, pelis y series
        patron = '<div\s*class="[^"]+">\s*<div\s*class="card">\s*<a\s*href="([^"]+)"\s*'
        patron += 'class="card__cover">\s*<img\s*src="([^"]+)"\s*alt="[^"]*">\s*'
        patron += '<div\s*class="card__play">.*?<\/div>\s*<ul\s*class="card__list">\s*'
        patron += '<li>([^<]+)<\/li>\s*<\/ul>\s*<\/a>\s*<div\s*class="card__content">\s*'
        patron += '<h3\s*class="card__title"><a\s*href="[^"]+">([^<]+)<\/a><\/h3>'
        patron += '.*?<\/div>\s*<\/div>\s*<\/div>'

        if not item.matches:                                                    # De pasada anterior?
            matches = re.compile(patron, re.DOTALL).findall(data)
        else:
            matches = item.matches
            del item.matches
            
        #logger.debug("PATRON: " + patron)
        #logger.debug(matches)
        #logger.debug(data)

        if not matches and item.extra != 'search' and not item.extra2:          #error
            logger.error("ERROR 02: LISTADO: Ha cambiado la estructura de la Web " 
                        + " / PATRON: " + patron + " / DATA: " + data)
            itemlist.append(item.clone(action='', title=item.channel.capitalize() + 
                        ': ERROR 02: LISTADO: Ha cambiado la estructura de la Web.  ' 
                        + 'Reportar el error con el log'))
            break                                                               #si no hay más datos, algo no funciona, pintamos lo que tenemos
        
        if not matches and item.extra == 'search':                              #búsqueda vacía
            if len(itemlist) > 0:                                               # Si hay algo que pintar lo pintamos
                last_page = 0
                break
            return itemlist                                                     #Salimos

        #Buscamos la próxima página
        next_page_url = re.sub(r'page\/(\d+)', 'page/%s' % str(curr_page), item.url)
        #logger.debug('curr_page: ' + str(curr_page) + ' / last_page: ' + str(last_page))
        
        #Buscamos la última página
        if last_page == 99999:                                                  #Si es el valor inicial, buscamos
            patron_last = '<ul\s*class="pagination[^"]+">.*?<li>\s*<a\s*class="page-numbers"\s*href="[^"]+">'
            patron_last += '(\d+)<\/a><\/li>\s*<li>\s*<a\s*class="next page-numbers"\s*href="[^"]+">»<\/a><\/li>\s*<\/ul>'
            try:
                last_page = int(scrapertools.find_single_match(data, patron_last))
            except:                                                             #Si no lo encuentra, lo ponemos a 999
                last_page = 1

            #logger.debug('curr_page: ' + str(curr_page) + ' / last_page: ' + str(last_page))
        
        #Empezamos el procesado de matches
        for scrapedurl, scrapedthumb, scrapedquality, scrapedtitle in matches:
            cnt_match += 1
            
            title = scrapedtitle

            title = scrapertools.remove_htmltags(title).rstrip('.')             # Removemos Tags del título
            url = scrapedurl
            
            title_subs = []                                                     #creamos una lista para guardar info importante
            
            title = title.replace("á", "a").replace("é", "e").replace("í", "i")\
                    .replace("ó", "o").replace("ú", "u").replace("ü", "u")\
                    .replace("ï¿½", "ñ").replace("Ã±", "ñ").replace("&#8217;", "'")\
                    .replace("&amp;", "&")

            # Se filtran las entradas para evitar duplicados de Temporadas
            url_list = url
            if url_list in title_lista:                                         #Si ya hemos procesado el título, lo ignoramos
                continue
            else:
                title_lista += [url_list]                                       #la añadimos a la lista de títulos

            # Si es una búsqueda por años, filtramos por tipo de contenido
            if 'anno' in item.extra2 and item.extra == 'series' and '/serie' not in url:
                continue
            elif 'anno' in item.extra2 and item.extra == 'peliculas' and '/serie' in url:
                continue
            
            cnt_title += 1                                                      # Incrementamos el contador de entradas válidas
            
            item_local = item.clone()                                           #Creamos copia de Item para trabajar
            if item_local.tipo:                                                 #... y limpiamos
                del item_local.tipo
            if item_local.totalItems:
                del item_local.totalItems
            if item_local.intervencion:
                del item_local.intervencion
            if item_local.viewmode:
                del item_local.viewmode
            item_local.extra2 = True
            del item_local.extra2
            item_local.text_bold = True
            del item_local.text_bold
            item_local.text_color = True
            del item_local.text_color
            
            # Después de un Search se restablecen las categorías
            if item_local.extra == 'search':
                if '/serie' in url:
                    item_local.extra = 'series'                                 # Serie búsqueda
                else:
                    item_local.extra = 'peliculas'                              # Película búsqueda

            # Procesamos idiomas
            item_local.language = []                                            #creamos lista para los idiomas
            if '[Subs. integrados]' in scrapedquality or '(Sub Forzados)' in scrapedquality \
                        or 'Sub' in scrapedquality:
                item_local.language = ['VOS']                                   # añadimos VOS
            if 'castellano' in scrapedquality.lower() or ('español' in scrapedquality.lower() and not 'latino' in scrapedquality.lower()): 
                item_local.language += ['CAST']                                 # añadimos CAST
            if '[Dual' in title or 'dual' in scrapedquality.lower():
                title = re.sub(r'(?i)\[dual.*?\]', '', title)
                item_local.language += ['DUAL']                                 # añadimos DUAL
            if not item_local.language:
                item_local.language = ['LAT']                                   # [LAT] por defecto
                
            # Procesamos Calidad
            if scrapedquality:
                item_local.quality = scrapertools.remove_htmltags(scrapedquality)   # iniciamos calidad
                if '[720p]' in scrapedquality.lower() or '720p' in scrapedquality.lower():
                    item_local.quality = '720p'
                if '[1080p]' in scrapedquality.lower() or '1080p' in scrapedquality.lower():
                    item_local.quality = '1080p'
                if '4k' in scrapedquality.lower():
                    item_local.quality = '4K'
                if '3d' in scrapedquality.lower() and not '3d' in item_local.quality.lower():
                    item_local.quality += ', 3D'
                if not item_local.quality:
                    item_local.quality = '720p'
                
            item_local.thumbnail = ''                                           #iniciamos thumbnail

            item_local.url = urlparse.urljoin(host, url)                        #guardamos la url final
            item_local.context = "['buscar_trailer']"                           #... y el contexto

            # Guardamos los formatos para series
            if item_local.extra == 'series' or '/serie' in item_local.url:
                item_local.contentType = "tvshow"
                item_local.action = "episodios"
                item_local.season_colapse = season_colapse                      #Muestra las series agrupadas por temporadas?
            else:
                # Guardamos los formatos para películas
                item_local.contentType = "movie"
                item_local.action = "findvideos"

            #Limpiamos el título de la basura innecesaria
            if item_local.contentType == "tvshow":
                title = scrapertools.find_single_match(title, '(^.*?)\s*(?:$|\(|\[|-)')

            title = re.sub(r'(?i)TV|Online|(4k-hdr)|(fullbluray)|4k| - 4k|(3d)|miniserie', '', title).strip()
            item_local.quality = re.sub(r'(?i)proper|unrated|directors|cut|repack|internal|real|extended|masted|docu|super|duper|amzn|uncensored|hulu', 
                        '', item_local.quality).strip()

            #Analizamos el año.  Si no está claro ponemos '-'
            item_local.infoLabels["year"] = '-'
            if 'anno' in item.extra2:
                item_local.infoLabels["year"] = item.extra2.replace('anno', '')
            
            #Terminamos de limpiar el título
            title = re.sub(r'[\(|\[]\s+[\)|\]]', '', title)
            title = title.replace('()', '').replace('[]', '').replace('[4K]', '').replace('(4K)', '').strip().lower().title()
            item_local.from_title = title.strip().lower().title()           #Guardamos esta etiqueta para posible desambiguación de título

            #Salvamos el título según el tipo de contenido
            if item_local.contentType == "movie":
                item_local.contentTitle = title
            else:
                item_local.contentSerieName = title.strip().lower().title()

            item_local.title = title.strip().lower().title()
            
            #Guarda la variable temporal que almacena la info adicional del título a ser restaurada después de TMDB
            item_local.title_subs = title_subs
                
            #Salvamos y borramos el número de temporadas porque TMDB a veces hace tonterias.  Lo pasamos como serie completa
            if item_local.contentSeason and (item_local.contentType == "season" \
                        or item_local.contentType == "tvshow"):
                item_local.contentSeason_save = item_local.contentSeason
                del item_local.infoLabels['season']

            #Ahora se filtra por idioma, si procede, y se pinta lo que vale
            if filter_languages > 0:                                            #Si hay idioma seleccionado, se filtra
                itemlist = filtertools.get_link(itemlist, item_local, list_language)
            else:
                itemlist.append(item_local.clone())                             #Si no, pintar pantalla
            
            cnt_title = len(itemlist)                                           # Recalculamos los items después del filtrado
            if cnt_title >= cnt_tot and (len(matches) - cnt_match) + cnt_title > cnt_tot * 1.3:     #Contador de líneas añadidas
                break
            
            #logger.debug(item_local)
    
        matches = matches[cnt_match:]                                           # Salvamos la entradas no procesadas
    
    #Pasamos a TMDB la lista completa Itemlist
    tmdb.set_infoLabels(itemlist, __modo_grafico__, idioma_busqueda='es')
    
    #Llamamos al método para el maquillaje de los títulos obtenidos desde TMDB
    item, itemlist = generictools.post_tmdb_listado(item, itemlist)

    # Si es necesario añadir paginacion
    if curr_page <= last_page or len(matches) > 0:
        if last_page:
            title = '%s de %s' % (curr_page-1, last_page)
        else:
            title = '%s' % curr_page-1

        itemlist.append(Item(channel=item.channel, action="listado", title=">> Página siguiente " 
                        + title, title_lista=title_lista, url=next_page_url, extra=item.extra, 
                        extra2=item.extra2, last_page=str(last_page), curr_page=str(curr_page), 
                        matches=matches, post=post))

    return itemlist

    
def findvideos(item):
    logger.info()
    
    itemlist = []
    itemlist_t = []                                                             #Itemlist total de enlaces
    itemlist_f = []                                                             #Itemlist de enlaces filtrados
    matches = []
    data = ''
    code = 0
    
    #logger.debug(item)

    #Bajamos los datos de la página y seleccionamos el bloque
    patron = '\s*<th\s*class="hide-on-mobile">Total\s*Descargas<\/th>\s*<th>'
    patron += 'Descargar<\/th>\s*<\/thead>\s*<tbody>\s*(.*?<\/tr>)\s*<\/tbody>'
    patron += '\s*<\/table>\s*<\/div>\s*<\/div>\s*<\/div>'
    
    if not item.matches:
        data, success, code, item, itemlist = generictools.downloadpage(item.url, timeout=timeout, 
                                          s2=False, patron=patron, item=item, itemlist=[])      # Descargamos la página)

    #Verificamos si se ha cargado una página, y si además tiene la estructura correcta
    if (not data and not item.matches) or code == 999:
        if item.emergency_urls and not item.videolibray_emergency_urls:         #Hay urls de emergencia?
            matches = item.emergency_urls[1]                                    #Restauramos matches de vídeos
            item.armagedon = True                                               #Marcamos la situación como catastrófica 
        else:
            if item.videolibray_emergency_urls:                                 #Si es llamado desde creación de Videoteca...
                return item                                                     #Devolvemos el Item de la llamada
            else:
                return itemlist                                                 #si no hay más datos, algo no funciona, pintamos lo que tenemos
    elif data:
        # Seleccionamos el bloque y buscamos los apartados
        data = scrapertools.find_single_match(data, patron)

    patron = '<tr>(?:\s*<td>[^<]+<\/td>)?\s*<td>([^<]+)<\/td>\s*<td>([^<]+)<\/td>\s*'
    patron += '<td\s*class=[^<]+<\/td>(?:<td>([^<]+)<\/td>)?\s*<td\s*class=[^<]+<\/td>\s*'
    patron += '<td>\s*<a\s*class="[^"]+"\s*(?:data-row="[^"]+"\s*data-post="[^"]+"\s*)?'
    patron += 'href="([^"]+)"\s*(?:data-season="([^"]+)"\s*data-serie="([^"]+)")?'
    
    if not item.armagedon:
        if not item.matches:
            matches = re.compile(patron, re.DOTALL).findall(data)
        else:
            matches = item.matches
    
    #logger.debug("PATRON: " + patron)
    #logger.debug(matches)
    #logger.debug(data)
    
    if not matches:                                                             #error
        return itemlist

    #Si es un lookup para cargar las urls de emergencia en la Videoteca...
    if item.videolibray_emergency_urls:
        item.emergency_urls = []                                                #Iniciamos emergency_urls
        item.emergency_urls.append([])                                          #Reservamos el espacio para los .torrents locales
        item.emergency_urls.append(matches)                                     #Salvamnos matches de los vídeos...  

    #Llamamos al método para crear el título general del vídeo, con toda la información obtenida de TMDB
    if not item.videolibray_emergency_urls:
        item, itemlist = generictools.post_tmdb_findvideos(item, itemlist)

    #Ahora tratamos los enlaces .torrent con las diferentes calidades
    for scrapedquality, scrapedlanguage, scrapedsize, scrapedurl, season_num, episode_num  in matches:
        scrapedpassword = ''

        #Generamos una copia de Item para trabajar sobre ella
        item_local = item.clone()

        item_local.url = scrapedurl

        # Restauramos urls de emergencia si es necesario
        local_torr = ''
        if item.emergency_urls and not item.videolibray_emergency_urls:
            item_local.torrent_alt = item.emergency_urls[0][0]                  #Guardamos la url del .Torrent ALTERNATIVA
            if item.armagedon:
                item_local.url = item.emergency_urls[0][0]                      #Restauramos la url
                if item_local.url.startswith("\\") or item_local.url.startswith("/"):
                    from core import filetools
                    if item.contentType == 'movie':
                        FOLDER = config.get_setting("folder_movies")
                    else:
                        FOLDER = config.get_setting("folder_tvshows")
                    local_torr = filetools.join(config.get_videolibrary_path(), FOLDER, item_local.url)
            if len(item.emergency_urls[0]) > 1:
                del item.emergency_urls[0][0]
        
        # Procesamos idiomas
        item_local.language = []                                                #creamos lista para los idiomas
        item_local.quality = scrapedquality                                     # Copiamos la calidad
        if '[Subs. integrados]' in scrapedlanguage or '(Sub Forzados)' in scrapedlanguage \
                    or 'Subs integrados' in scrapedlanguage:
            item_local.language = ['VOS']                                       # añadimos VOS
        if 'castellano' in scrapedlanguage.lower() or ('español' in scrapedlanguage.lower() and not 'latino' in scrapedlanguage.lower()):
            item_local.language += ['CAST']                                     # añadimos CAST
        if 'dual' in item_local.quality.lower():
            item_local.quality = re.sub(r'(?i)dual.*?', '', item_local.quality).strip()
            item_local.language += ['DUAL']                                     # añadimos DUAL
        if not item_local.language:
            item_local.language = ['LAT']                                       # [LAT] por defecto
        
        #Buscamos tamaño en el archivo .torrent
        size = ''
        if item_local.torrent_info:
            size = item_local.torrent_info
        elif scrapedsize:
            size = scrapedsize
        if not size and not item.videolibray_emergency_urls and not item_local.url.startswith('magnet:'):
            if not item.armagedon:
                size = generictools.get_torrent_size(item_local.url, local_torr=local_torr) #Buscamos el tamaño en el .torrent desde la web
        if size:
            size = size.replace('GB', 'G·B').replace('Gb', 'G·b').replace('MB', 'M·B')\
                        .replace('Mb', 'M·b').replace('.', ',')
            item_local.torrent_info = '%s, ' % size                             #Agregamos size
        if item_local.url.startswith('magnet:') and not 'Magnet' in item_local.torrent_info:
            item_local.torrent_info += ' Magnet'
        if item_local.torrent_info:
            item_local.torrent_info = item_local.torrent_info.strip().strip(',')
            item.torrent_info = item_local.torrent_info
            if not item.unify:
                item_local.torrent_info = '[%s]' % item_local.torrent_info
   
        # Guadamos la password del RAR
        password = scrapedpassword
        # Si tiene contraseña, la guardamos y la pintamos
        if password or item.password:
            if not item.password: item.password = password
            item_local.password = item.password
            itemlist.append(item.clone(action="", title="[COLOR magenta][B] Contraseña: [/B][/COLOR]'" 
                        + item_local.password + "'", folder=False))
        
        # Guardamos urls de emergencia si se viene desde un Lookup de creación de Videoteca
        if item.videolibray_emergency_urls:
            item.emergency_urls[0].append(item_local.url)                       #guardamos la url y nos vamos
            continue

        #Ahora pintamos el link del Torrent
        item_local.title = '[[COLOR yellow]?[/COLOR]] [COLOR yellow][Torrent][/COLOR] ' \
                        + '[COLOR limegreen][%s][/COLOR] [COLOR red]%s[/COLOR] %s' % \
                        (item_local.quality, str(item_local.language), \
                        item_local.torrent_info)
        
        #Preparamos título y calidad, quitando etiquetas vacías
        item_local.title = re.sub(r'\s?\[COLOR \w+\]\[\[?\s?\]?\]\[\/COLOR\]', '', item_local.title)    
        item_local.title = re.sub(r'\s?\[COLOR \w+\]\s?\[\/COLOR\]', '', item_local.title)
        item_local.title = item_local.title.replace("--", "").replace("[]", "")\
                        .replace("()", "").replace("(/)", "").replace("[/]", "")\
                        .replace("|", "").strip()
        item_local.quality = re.sub(r'\s?\[COLOR \w+\]\[\[?\s?\]?\]\[\/COLOR\]', '', item_local.quality)
        item_local.quality = re.sub(r'\s?\[COLOR \w+\]\s?\[\/COLOR\]', '', item_local.quality)
        item_local.quality = item_local.quality.replace("--", "").replace("[]", "")\
                        .replace("()", "").replace("(/)", "").replace("[/]", "")\
                        .replace("|", "").strip()
        
        item_local.alive = "??"                                                 #Calidad del link sin verificar
        item_local.action = "play"                                              #Visualizar vídeo
        item_local.server = "torrent"                                           #Seridor Torrent
        
        itemlist_t.append(item_local.clone())                                   #Pintar pantalla, si no se filtran idiomas
        
        # Requerido para FilterTools
        if config.get_setting('filter_languages', channel) > 0:                 #Si hay idioma seleccionado, se filtra
            itemlist_f = filtertools.get_link(itemlist_f, item_local, list_language)  #Pintar pantalla, si no está vacío

        #logger.debug("TORRENT: " + scrapedurl + " / title gen/torr: " + item.title + " / " + item_local.title + " / calidad: " + item_local.quality + " / content: " + item_local.contentTitle + " / " + item_local.contentSerieName)
        #logger.debug(item_local)

    #Si es un lookup para cargar las urls de emergencia en la Videoteca...
    if item.videolibray_emergency_urls:
        return item                                                             #... nos vamos
    
    if len(itemlist_f) > 0:                                                     #Si hay entradas filtradas...
        itemlist.extend(itemlist_f)                                             #Pintamos pantalla filtrada
    else:                                                                       
        if config.get_setting('filter_languages', channel) > 0 and len(itemlist_t) > 0: #Si no hay entradas filtradas ...
            thumb_separador = get_thumb("next.png")                             #... pintamos todo con aviso
            itemlist.append(Item(channel=item.channel, url=host, 
                        title="[COLOR red][B]NO hay elementos con el idioma seleccionado[/B][/COLOR]", 
                        thumbnail=thumb_separador, folder=False))
        itemlist.extend(itemlist_t)                                             #Pintar pantalla con todo si no hay filtrado
    
    # Requerido para AutoPlay
    autoplay.start(itemlist, item)                                              #Lanzamos Autoplay
    
    return itemlist
    

def episodios(item):
    logger.info()
    
    itemlist = []
    item.category = categoria
    
    #logger.debug(item)

    if item.from_title:
        item.title = item.from_title
    
    #Limpiamos num. Temporada y Episodio que ha podido quedar por Novedades
    season_display = 0
    if item.contentSeason:
        if item.season_colapse:                                                 #Si viene del menú de Temporadas...
            season_display = item.contentSeason                                 #... salvamos el num de sesión a pintar
            item.from_num_season_colapse = season_display
            del item.season_colapse
            item.contentType = "tvshow"
            if item.from_title_season_colapse:
                item.title = item.from_title_season_colapse
                del item.from_title_season_colapse
                if item.infoLabels['title']:
                    del item.infoLabels['title']
        del item.infoLabels['season']
    if item.contentEpisodeNumber:
        del item.infoLabels['episode']
    if season_display == 0 and item.from_num_season_colapse:
        season_display = item.from_num_season_colapse

    # Obtener la información actualizada de la Serie.  TMDB es imprescindible para Videoteca
    try:
        tmdb.set_infoLabels(item, True, idioma_busqueda='es,en')
    except:
        pass
        
    modo_ultima_temp_alt = modo_ultima_temp
    if item.ow_force == "1":                                                    #Si hay una migración de canal o url, se actualiza todo 
        modo_ultima_temp_alt = False
    
    # Vemos la última temporada de TMDB y del .nfo
    max_temp = 1
    if item.infoLabels['number_of_seasons']:
        max_temp = item.infoLabels['number_of_seasons']
    y = []
    if modo_ultima_temp_alt and item.library_playcounts:                        #Averiguar cuantas temporadas hay en Videoteca
        patron = 'season (\d+)'
        matches = re.compile(patron, re.DOTALL).findall(str(item.library_playcounts))
        for x in matches:
            y += [int(x)]
        max_temp = max(y)

    # Si la series tiene solo una temporada, o se lista solo una temporada, guardamos la url y seguimos normalmente
    list_temp = []
    list_temp.append(item.url)

    # Descarga las páginas
    for url in list_temp:                                                       # Recorre todas las temporadas encontradas
        
        data, success, code, item, itemlist = generictools.downloadpage(url, timeout=timeout, s2=False, 
                                          item=item, itemlist=itemlist)         # Descargamos la página
        
        #Verificamos si se ha cargado una página, y si además tiene la estructura correcta
        if not success:                                                         # Si ERROR o lista de errores ...
            return itemlist                                                     # ... Salimos

        patron = '<tr>(?:\s*<td>[^<]+<\/td>)?\s*<td>([^<]+)<\/td>\s*<td>([^<]+)<\/td>\s*'
        patron += '<td\s*class=[^<]+<\/td>(?:<td>([^<]+)<\/td>)?\s*<td\s*class=[^<]+<\/td>\s*'
        patron += '<td>\s*<a\s*class="[^"]+"\s*(?:data-row="[^"]+"\s*data-post="[^"]+"\s*)?'
        patron += 'href="([^"]+)"\s*(?:data-season="([^"]+)"\s*data-serie="([^"]+)")?'
        
        matches = re.compile(patron, re.DOTALL).findall(data)

        #logger.debug("PATRON: " + patron)
        #logger.debug(matches)
        #logger.debug(data)

        # Recorremos todos los episodios generando un Item local por cada uno en Itemlist
        x = 0
        for scrapedquality, scrapedlanguage, scrapedsize, scrapedurl, season_num, episode_num  in matches:
            item_local = item.clone()
            item_local.action = "findvideos"
            item_local.contentType = "episode"
            if item_local.library_playcounts:
                del item_local.library_playcounts
            if item_local.library_urls:
                del item_local.library_urls
            if item_local.path:
                del item_local.path
            if item_local.update_last:
                del item_local.update_last
            if item_local.update_next:
                del item_local.update_next
            if item_local.channel_host:
                del item_local.channel_host
            if item_local.active:
                del item_local.active
            if item_local.contentTitle:
                del item_local.infoLabels['title']
            if item_local.season_colapse:
                del item_local.season_colapse

            item_local.url = url                                                # Usamos las url de la temporada, no hay de episodio
            item.matches = [matches[x]]                                         # Salvado Matches de cada episodio
            x += 1
            item_local.context = "['buscar_trailer']"
            if not item_local.infoLabels['poster_path']:
                item_local.thumbnail = item_local.infoLabels['thumbnail']
            
            # Extraemos números de temporada y episodio
            item_local.contentSeason = season_num
            item_local.contentEpisodeNumber = episode_num

            item_local.title = '%sx%s - ' % (str(item_local.contentSeason), 
                        str(item_local.contentEpisodeNumber).zfill(2))
            
            # Procesamos Calidad
            if scrapedquality:
                item_local.quality = scrapertools.remove_htmltags(scrapedquality)   # iniciamos calidad
                if '[720p]' in scrapedquality.lower() or '720p' in scrapedquality.lower():
                    item_local.quality = '720p'
                if '[1080p]' in scrapedquality.lower() or '1080p' in scrapedquality.lower():
                    item_local.quality = '1080p'
                if '4k' in scrapedquality.lower():
                    item_local.quality = '4K'
                if '3d' in scrapedquality.lower() and not '3d' in item_local.quality.lower():
                    item_local.quality += ', 3D'
                if not item_local.quality:
                    item_local.quality = '720p'
            
            # Comprobamos si hay más de un enlace por episodio, entonces los agrupamos
            if len(itemlist) > 0 and item_local.contentSeason == itemlist[-1].contentSeason \
                        and item_local.contentEpisodeNumber == itemlist[-1].contentEpisodeNumber \
                        and itemlist[-1].contentEpisodeNumber != 0:             # solo guardamos un episodio ...
                if itemlist[-1].quality:
                    if item_local.quality not in itemlist[-1].quality:
                        itemlist[-1].quality += ", " + item_local.quality       # ... pero acumulamos las calidades
                else:
                    itemlist[-1].quality = item_local.quality
                continue                                                        # ignoramos el episodio duplicado
            
            if season_display > 0:                                              # Son de la temporada estos episodios?
                if item_local.contentSeason > season_display:
                    break
                elif item_local.contentSeason < season_display:
                    continue
                    
            if modo_ultima_temp_alt and item.library_playcounts:                # Si solo se actualiza la última temporada de Videoteca
                if item_local.contentSeason < max_temp:
                    continue                                                    # Sale del bucle actual del FOR

            itemlist.append(item_local.clone())

            #logger.debug(item_local)
            
    if len(itemlist) > 1:
        itemlist = sorted(itemlist, key=lambda it: (int(it.contentSeason), int(it.contentEpisodeNumber)))       #clasificamos
        
    if item.season_colapse and not item.add_videolibrary:                       #Si viene de listado, mostramos solo Temporadas
        item, itemlist = generictools.post_tmdb_seasons(item, itemlist, url='episode')

    if not item.season_colapse:                                                 #Si no es pantalla de Temporadas, pintamos todo
        # Pasada por TMDB y clasificación de lista por temporada y episodio
        tmdb.set_infoLabels(itemlist, True, idioma_busqueda='es,en')

        #Llamamos al método para el maquillaje de los títulos obtenidos desde TMDB
        item, itemlist = generictools.post_tmdb_episodios(item, itemlist)
    
    #logger.debug(item)

    return itemlist


def actualizar_titulos(item):
    logger.info()
    
    #Llamamos al método que actualiza el título con tmdb.find_and_set_infoLabels
    item = generictools.update_title(item)
    
    #Volvemos a la siguiente acción en el canal
    return item

    
def search(item, texto):
    logger.info()
    texto = texto.replace(" ", "+")
    
    try:
        item.url = host + 'buscar/page/1/?buscar=' + texto
        item.extra = 'search'

        if texto:
            return listado(item)
        else:
            return []
    except:
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        logger.error(traceback.format_exc(1))
        return []
 
 
def newest(categoria):
    logger.info()
    itemlist = []
    item = Item()

    item.title = "newest"
    item.category_new = "newest"
    item.channel = channel
    
    try:
        if categoria == 'peliculas':
            item.url = host + "peliculas/page/1/"
            item.extra = "peliculas"
            item.extra2 = "novedades"
            item.action = "listado"
            itemlist = listado(item)
                
        elif categoria == 'series':
            item.url = host + "series/page/1/"
            item.extra = "series"
            item.extra2 = "novedades"
            item.action = "listado"
            itemlist = listado(item)

        if ">> Página siguiente" in itemlist[-1].title or "Pagina siguiente >>" in itemlist[-1].title:
            itemlist.pop()

    # Se captura la excepción, para no interrumpir al canal novedades si un canal falla
    except:
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        logger.error(traceback.format_exc(1))
        return []

    return itemlist
