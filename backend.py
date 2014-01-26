#Copyright (C) 2014 Adrian "APi" Pielech

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PySide.QtNetwork import *
from PySide.QtCore import *
from PySide.QtGui import *
from subprocess import Popen, PIPE


class EPISODE(QListWidgetItem):
    def __init__(self, parent=None, title='<Title>', value='<Value>'):
        super(EPISODE, self).__init__(parent)
        self.title = title
        self.value = value

    def setText(self, title):
        self.title = title
        super(EPISODE, self).setText(self.title)

    def setValue(self, value):
        self.value = value

    def getValue(self):
        return self.value


class DownloadEpisodeThread(QThread):
    saveTo = None
    who_am_i = 0

    def __init__(self, parent, threadId):
        super(DownloadEpisodeThread, self).__init__()
        self.parentObject = parent
        self.who_am_i = threadId

    def run(self):
        qNetMgr = QNetworkAccessManager()
        downloadLoop = QEventLoop()
        loopArg = True
        item = None
        p = self.parentObject
        while(loopArg is True):
            p.downloadMutex.tryLock(-1)
            if(p.lstwToDownload.count() > 0):
                item = p.lstwToDownload.takeItem(0)
                p.appendLogs.emit('Zaczynam pobierać: ' + item.text())
            else:
                loopArg = False
                item = None
                if p.downloadedEps == p.mustDownloadEps:
                    p.btnDownload.setEnabled(True)
                    p.freezeSettings(True)
                    p.btnDownloadEpisodesList.setEnabled(True)
            p.downloadMutex.unlock()
            if not(item is None):
                qReply = qNetMgr.get(QNetworkRequest(QUrl(item.getValue())))
                if item.getValue().count('https://') > 0:
                    qReply.sslErrors.connect(qReply.ignoreSslErrors)
                qReply.metaDataChanged.connect(downloadLoop.quit)

                downloadLoop.exec_()

                if qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 302:
                    redirURL = qReply.attribute(QNetworkRequest.RedirectionTargetAttribute)
                    qReply = qNetMgr.get(QNetworkRequest(QUrl(redirURL)))
                    qReply.metaDataChanged.connect(downloadLoop.quit)
                    downloadLoop.exec_()

                if qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 200:
                    p.lblThreadArray[self.who_am_i].setText(item.text())
                    p.pbThreadArray[self.who_am_i].setEnabled(True)
                    self.saveTo = QFile(item.text())
                    if not self.saveTo.open(QIODevice.WriteOnly):
                        print('Nie moge otworzyc panie ;_;')
                    qReply.downloadProgress.connect(self.saveToFile)
                    qReply.finished.connect(downloadLoop.quit)
                    downloadLoop.exec_()
                    p.pbThreadArray[self.who_am_i].setEnabled(False)
                    self.saveTo.write(qReply.readAll())
                    self.saveTo.close()
                    p.downloadMutex.tryLock(-1)
                    p.downloadedEps = p.downloadedEps + 1
                    p.pbDownloaded.setValue(p.downloadedEps)
                    p.appendLogs.emit(item.text() + ' pobrano!')
                    if p.chkbConvert.isChecked() is True:
                        p.lstwToConvert.addItem(item)
                        p.sigConvert.emit()
                    p.downloadMutex.unlock()
                else:
                    p.downloadMutex.tryLock(-1)
                    p.appendLogs.emit('Nie udało się pobrać ' + item.text() + '! Błąd: ' + str(qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute)) + '.')
                    p.downloadedEps = p.downloadedEps + 1
                    p.pbDownloaded.setValue(p.downloadedEps)
                    p.downloadMutex.unlock()

    def saveToFile(self, received, total):
        if total != self.parentObject.pbThreadArray[self.who_am_i].maximum():
            self.parentObject.pbThreadArray[self.who_am_i].setMaximum(total)
        self.parentObject.pbThreadArray[self.who_am_i].setValue(received)


class Backend:
    def writeLog(self, log_message):
        self.logDest.setPlainText(log_message + "\n" + self.logDest.toPlainText())

    def convertEpisode(self):
        self.convertMutex.tryLock(-1)
        self.downloadMutex.tryLock(-1)

        workItem = self.lstwToConvert.takeItem(0)

        self.downloadMutex.unlock()

        output_file = workItem.text()[:len(workItem.text()) - 3] + self.cbOutputFormat.currentText()

        file_info = Popen(['ffmpeg', '-i', workItem.text()], stderr=PIPE)
        file_info.wait()
        file_info = file_info.stderr.read(-1).decode('utf-8')
        file_info = file_info[file_info.find('Duration:') + 10:]
        file_info = file_info[:file_info.find(',')]
        file_time_info = file_info.split(':')
        file_time_info = file_time_info + file_time_info[2].split('.')
        length = int(file_time_info[0]) * 3600 + int(file_time_info[1]) * 60 + int(file_time_info[3])
        self.pbConverted.setMaximum(length)
        self.pbConverted.setValue(0)
        self.appendLogs.emit('Zaczynam konwertować: ' + workItem.text())
        '''TO DO Start converting'''

        self.convertMutex.unlock()

    def getEpisodesListFromWeb(self, linkToSeries, lblSeriesName, lstItems, log):
        lstItems.clear()
        self.logDest = log
        if len(linkToSeries) > 15:
            if linkToSeries.find('animeon.pl') >= 0:
                lblSeriesName.setText(self.getAnimeOnList(linkToSeries, lstItems))
            elif linkToSeries.find('anime-shinden.info') >= 0:
                lblSeriesName.setText(self.getAShindenList(linkToSeries, lstItems))
            else:
                self.writeLog("Podano URL do nieobsługiwanego serwisu!")
        else:
            self.writeLog("Nieprawidłowy URL do serii!")

    def getVideoListFromURL(self, get_from):
        ret_val = [None]
        basic_filename = get_from.text()
        episode_page_url = get_from.getValue()

        '''print(episode_page_url)'''
        if episode_page_url.find('animeon.pl') > 0:
            ret_val = self.extractLinksFromAnimeOn(episode_page_url, basic_filename)
        elif (episode_page_url.find('anime-shinden.info') > 0) or (episode_page_url.find('shinden-anime.info') > 0):
            episode_page_url = episode_page_url.replace('shinden-anime.info', 'anime-shinden.info')
            ret_val = self.extractLinksFromAShinden(episode_page_url, basic_filename)
        else:
            self.writeLog('Coś poszło nie tak... Nie rozpoznano serwisu anime.\nCzy przypadkiem nie bawisz się w inżynierię odwrotną?')

        return ret_val

    def extractLinksFromAShinden(self, link, basename):
        ret_val = [None]
        self.writeLog('Pobieranie i parsowanie strony ' + basename + '...')
        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(link)))
        downloadLoop = QEventLoop()
        qReply.finished.connect(downloadLoop.quit)

        downloadLoop.exec_()

        if qReply.error() == 0:
            if qReply.size() < 1024:
                self.writeLog('Serwer zwrócił niepoprawną zawartość...')
                self.writeLog(str(qReply.readAll().data()))
            else:
                done = 0
                data = str(qReply.readAll().data())
                data = data[data.find('video_tabs'):]
                data = data[:data.find('<script')]
                fb_count = int(data.count('http://anime-shinden.info/player/hd.php') / 2)
                sibnet_count = data.count('video.sibnet.ru')
                daily_count = data.count('www.dailymotion.com/embed/video')
                if daily_count == 0:
                    daily_count = int(data.count('www.dailymotion.com/swf/video/') / 2)

                data_backup = data
                '''#jwplayer - fb'''
                if fb_count > 0:
                    done = 1
                    fb_table = [None]
                    for i in range(0, fb_count):
                        data = data[data.find('http://anime-shinden.info/player/hd.php') + 10:]
                        data = data[data.find('http://anime-shinden.info/player/hd.php'):]
                        data = data[data.find('link=') + 5:]
                        vid = data[:data.find('.mp4')]
                        vid = 'https://www.facebook.com/video/embed?video_id=' + vid
                        link_to_face = self.getEmbedFacebookVideoLink(vid)
                        if len(link_to_face) > 0:
                            ep = EPISODE()
                            if fb_count == 1:
                                ep.setText(basename + ".mp4")
                                ep.setValue(link_to_face)
                                fb_table.append(ep)
                            else:
                                ep.setText(basename + chr(97 + i) + ".mp4")
                                ep.setValue(link_to_face)
                                fb_table.append(ep)
                        else:
                            self.writeLog('Nie udało się wydobyć linku do fejsa...')
                            done = 0
                    if done == 1:
                        ret_val = fb_table
                if (done == 0) and (sibnet_count > 0):
                    data = data_backup
                    done = 1
                    sib_table = [None]
                    for i in range(0, sibnet_count):
                        data = data[data.find('http://video.sibnet.ru/'):]
                        data = data[data.find('=') + 1:]
                        vid = data[:data.find('''"''')]
                        link_to_sib = self.getEmbedSibnetRUVideoLink(vid)
                        if len(link_to_sib) > 0:
                            ep = EPISODE()
                            if sibnet_count > 0:
                                ep.setText(basename + ".mp4")
                                ep.setValue(link_to_sib)
                                sib_table.append(ep)
                            else:
                                ep.setText(basename + chr(97 + i) + ".mp4")
                                ep.setValue(link_to_sib)
                                fb_table.append(ep)
                        else:
                            self.writeLog('Nie udało się wydobyć linku do Sibnetu...')
                            done = 0
                    if done == 1:
                        ret_val = sib_table
                    print('Sibnet :D')
                if (done == 0) and (daily_count > 0):
                    print('Daily lol')
                    data = data_backup
                    data = data.replace('http://www.dailymotion.com/swf/video/', 'http://www.dailymotion.com/embed/video/')
                    done = 1
                    daily_table = [None]
                    for i in range(0, daily_count):
                        data = data[data.find('http://www.dailymotion.com/embed/video/'):]
                        daily_temple_link = data[:data.find('''"''')]
                        data = data[data.find('''"'''):]
                        link_to_daily = self.getEmbedDailyVideoLink(daily_temple_link)
                        if len(link_to_daily) > 0:
                            ep = EPISODE()
                            if daily_count == 1:
                                ep.setText(basename + ".mp4")
                                ep.setValue(link_to_daily)
                                daily_table.append(ep)
                            else:
                                ep.setText(basename + chr(97 + i) + ".mp4")
                                ep.setValue(link_to_daily)
                                daily_table.append(ep)
                        else:
                            self.writeLog('Nie udało się wydobyć linku do DailyMotion...')
                            done = 0
                    if done == 1:
                        ret_val = daily_table
                if done == 0:
                    self.writeLog('Wybacz, nie udało mi się znaleźć linku do żadnego działającego serwisu :(')
        return ret_val

    def extractLinksFromAnimeOn(self, link, basename):
        ret_val = [None]
        self.writeLog('Pobieranie i parsowanie strony ' + basename + '...')
        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(link)))
        downloadLoop = QEventLoop()
        qReply.finished.connect(downloadLoop.quit)

        downloadLoop.exec_()

        if qReply.error() == 0:
            if qReply.size() < 1024:
                self.writeLog('Serwer zwrócił niepoprawną zawartość...')
            else:
                data = str(qReply.readAll().data())
                data = data[data.find('float-left player-container'):]
                data = data[:data.find('float-left episode-nav')]
                if data.count('<iframe src=') > 0:
                    counter = data.count('<iframe src=')
                    for i in range(0, data.count('<iframe src=')):
                        data = data[data.find('<iframe src='):]
                        data = data[data.find("""'""") + 1:]
                        the_link = data[:data.find("\\")]
                        data = data[data.find('</iframe>'):]
                        if the_link.find('facebook.com') > 0:
                            link_to_face = self.getEmbedFacebookVideoLink(the_link)
                            if len(link_to_face) > 0:
                                '''link_to_face = download'''
                                ep = EPISODE()
                                if counter == 1:
                                    ep.setText(basename + ".mp4")
                                    ep.setValue(link_to_face)
                                    ret_val.append(ep)
                                else:
                                    ep.setText(basename + chr(97 + i) + ".mp4")
                                    ep.setValue(link_to_face)
                                    ret_val.append(ep)
                            else:
                                self.writeLog('Nie udało się wydobyć linku do fejsa...')
                        elif the_link.find('vk.com') > 0:
                            link_to_vk = self.getEmbedVKVideoLink(the_link)
                            if len(link_to_vk) > 0:
                                ep = EPISODE()
                                if counter == 1:
                                    ep.setText(basename + ".mp4")
                                    ep.setValue(link_to_vk)
                                    ret_val.append(ep)
                                else:
                                    ep.setText(basename + chr(97 + i) + ".mp4")
                                    ep.setValue(link_to_vk)
                                    ret_val.append(ep)
                            else:
                                self.writeLog('Nie udało się wydobyć linku do VK...')
                        else:
                            self.writeLog('I dont know this player...')
                elif data.count('<embed src=') > 0:
                    counter = data.count('<embed src=')
                    for i in range(0, data.count('<embed src=')):
                        data = data[data.find('<embed src='):]
                        data = data[data.find("""'""") + 1:]
                        the_link = data[:data.find("\\")]
                        data = data[data.find('</embed>'):]
                        if the_link.find('video.sibnet.ru') > 0:
                            the_link = the_link[the_link.find('=') + 1:]
                            link_to_sibnet = self.getEmbedSibnetRUVideoLink(the_link)
                            if len(link_to_sibnet) > 0:
                                ep = EPISODE()
                                if counter == 1:
                                    ep.setText(basename + ".mp4")
                                    ep.setValue(link_to_sibnet)
                                    ret_val.append(ep)
                                else:
                                    ep.setText(basename + chr(97 + i) + ".mp4")
                                    ep.setValue(link_to_sibnet)
                                    ret_val.append(ep)
                            else:
                                self.writeLog('Nie udało się wydobyć linku do Sibnetu...')
                        else:
                            self.writeLog('I dont know this player...')
                elif data.count('jwplayer(') > 0:
                    counter = data.count('jwplayer(')
                    for i in range(0, counter):
                        data = data[data.find('jwplayer('):]
                        data = data[data.find('http://'):]
                        jw_link = data[:data.find("""'""") - 1]
                        qReply = qNetMgr.get(QNetworkRequest(QUrl(jw_link)))
                        qReply.metaDataChanged.connect(downloadLoop.quit)
                        downloadLoop.exec_()

                        if not ((qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 200) or (qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 302)):
                            jw_link = ''
                        if len(jw_link) > 0:
                            ep = EPISODE()
                            if counter == 1:
                                ep.setText(basename + ".mp4")
                                ep.setValue(jw_link)
                                ret_val.append(ep)
                            else:
                                ep.setText(basename + chr(97 + i) + ".mp4")
                                ep.setValue(jw_link)
                                ret_val.append(ep)
                else:
                    self.writeLog('No player found.')
        return ret_val

    def getEmbedDailyVideoLink(self, url):
        ret_val = ''
        if url.count('/swf/') > 0:
            url = url.replace('/swf/', '/embed/')
        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(url)))
        downloadLoop = QEventLoop()
        qReply.finished.connect(downloadLoop.quit)

        downloadLoop.exec_()

        if qReply.error() == 0:
            print((qReply.size()))
            data = qReply.readAll().data().decode('UTF-8')
            if data.count('''"stream_h264_hd_url"''') > 0:
                data = data[data.find('''"stream_h264_hd_url"'''):]
                data = data[data.find('http:'):]
                data = data[:data.find('''"''')]
                data = data.replace("\\", '')

                qReply = qNetMgr.get(QNetworkRequest(QUrl(data)))
                qReply.metaDataChanged.connect(downloadLoop.quit)
                downloadLoop.exec_()

                if qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 302:
                    '''302 Found'''
                    ret_val = data
        return ret_val

    def getEmbedSibnetRUVideoLink(self, vid):
        ret_val = ''
        url = 'http://video.sibnet.ru/shell_config_xml.php?videoid=' + vid + '&type=video.sibnet.ru'
        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(url)))
        downloadLoop = QEventLoop()
        qReply.finished.connect(downloadLoop.quit)

        downloadLoop.exec_()

        if qReply.error() == 0:
            data = qReply.readAll().data().decode('UTF-8')
            data = data[data.find('<file>') + 6:data.find('</file>')]

            qReply = qNetMgr.get(QNetworkRequest(QUrl(data)))
            qReply.metaDataChanged.connect(downloadLoop.quit)
            downloadLoop.exec_()

            if qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 302:
                '''302 Found'''
                ret_val = data
        return ret_val

    def getEmbedVKVideoLink(self, url):
        ret_val = ''
        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(url)))
        downloadLoop = QEventLoop()
        qReply.finished.connect(downloadLoop.quit)

        downloadLoop.exec_()

        if qReply.error() == 0:
            data = qReply.readAll().data().decode('windows-1251')
            data = data[data.find('url720=') + 7:]
            data = data[:data.find('&')]

            qReply = qNetMgr.get(QNetworkRequest(QUrl(data)))
            qReply.metaDataChanged.connect(downloadLoop.quit)
            downloadLoop.exec_()
            if qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 200:
                '''200 OK'''
                ret_val = data
        return ret_val

    def getEmbedFacebookVideoLink(self, url):
        ret_val = ''
        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(url)))
        qReply.sslErrors.connect(qReply.ignoreSslErrors)
        downloadLoop = QEventLoop()
        qReply.finished.connect(downloadLoop.quit)

        downloadLoop.exec_()

        if qReply.error() == 0:
            data = qReply.readAll().data().decode('UTF-8')
            if data.count('hd_src') > 0:
                data = data[data.find('hd_src'):]
                data = data[data.find('https'):]
                data = data[:data.find('u002522') - 1]
                data = data.replace("\\", "/")
                data = data.replace("/u00255C", "").replace("/u00252F", "/").replace("/u00253F", "?").replace("/u00253D", "=").replace("/u002526", "&").replace("/u00253A",":")
                qReply = qNetMgr.get(QNetworkRequest(QUrl(data)))
                qReply.sslErrors.connect(qReply.ignoreSslErrors)
                qReply.metaDataChanged.connect(downloadLoop.quit)
                downloadLoop.exec_()
                if qReply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 200:
                    '''200 OK'''
                    ret_val = data
        return ret_val

    def getAShindenList(self, url, items):
        series_name = "-"
        self.writeLog('Trwa pobieranie listy odcinków serii(A-Shinden)...')

        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(url)))
        loop = QEventLoop()
        qReply.finished.connect(loop.quit)

        loop.exec_()

        if qReply.error() == 0:
            if qReply.size() < 1024:
                self.writeLog('Pobieranie danych o liście odcników nie powiodło się!')
            else:
                self.writeLog('Pobrano dane. Trwa parsowanie danych...')
                data = str(qReply.readAll().data())

                series_name = data[data.find('base fullstory'):]
                series_name = series_name[:series_name.find('</a>')]
                series_name = series_name[series_name.find('>', series_name.find('<a href=') + 7) + 1:]
                series_name = series_name[:series_name.find('(') - 1]

                self.writeLog('Pobierana seria: ' + series_name)

                '''Extract episode list'''
                '''Shrink data'''
                data = data[data.find('daj online'):]
                data = data[:data.find('</table>')]
                data = data[data.find('<a href='):]
                data = data[:data.find('</td>')]

                i = data.find('<a href=')

                while i >= 0:
                    ep = EPISODE()
                    ep.setValue(data[i + 9:data.find("\"", i + 9)])
                    data = data[data.find('>') + 1:]
                    ep.setText(data[:data.find('</a>')])

                    if data.find('<a href') >= 0:
                        data = data[data.find('<a href'):]
                    i = data.find('<a href')
                    if (ep.text().lower().find('odcinek') >= 0) or (ep.text().lower().find('ova') >= 0) or (ep.text().lower().find('odc') >= 0):
                        items.addItem(ep)
                self.writeLog('Lista odcinków pobrana.')
        else:
            self.writeLog('Błąd połączenia. Pobieranie danych o liście odcników nie powiodło się!')
        return series_name

    def getAnimeOnList(self, url, items):
        series_name = "-"
        self.writeLog('Trwa pobieranie listy odcinków serii(AnimeOn)...')

        qNetMgr = QNetworkAccessManager()
        qReply = qNetMgr.get(QNetworkRequest(QUrl(url)))
        loop = QEventLoop()
        qReply.finished.connect(loop.quit)

        loop.exec_()

        if qReply.error() == 0:
            if qReply.size() < 1024:
                self.writeLog('Pobieranie danych o liście odcników nie powiodło się!')
            else:
                self.writeLog('Pobrano dane. Trwa parsowanie danych...')
                data = str(qReply.readAll().data())

                series_name = data[data.find('<title>') + 7: data.find(' Anime Online PL')]

                data = data[data.find('episode-table') + 13:]
                data = data[:data.find('</table')]

                i = data.find('http://')

                while i >= 0:
                    ep = EPISODE()
                    data = data[data.find('http://'):]
                    ep.setValue(data[:data.find('\\')])
                    ep.setText(data[data.find('odcinek'):data.find('</a>')])
                    items.addItem(ep)

                    data = data[data.find('</a>'):]
                    i = data.find('http://')

        else:
            self.writeLog('Błąd połączenia. Pobieranie danych o liście odcników nie powiodło się!')
        return series_name
