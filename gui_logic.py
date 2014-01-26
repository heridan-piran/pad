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

from gui import Ui_AnimuWidget
from backend import *
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtNetwork import *


class MainWindow(Ui_AnimuWidget, Backend, QTabWidget):
    appendLogs = Signal(str)
    sigConvert = Signal()
    lblThreadArray = [None]
    pbThreadArray = [None]

    def __init__(self):
        super(MainWindow, self).__init__()
        '''Initialize main window and its layout'''
        super(MainWindow, self).setupMe(self)
        self.createUiArrays()
        self.setSignals()
        self.downloadMutex = QMutex()
        self.convertMutex = QMutex()
        self.show()

    def createUiArrays(self):
        self.lblThreadArray = [self.lblThread0, self.lblThread1, self.lblThread2, self.lblThread3, self.lblThread4, self.lblThread5, self.lblThread6, self.lblThread7, self.lblThread8]
        self.lblThreadArray = self.lblThreadArray + [self.lblThread9, self.lblThreadA, self.lblThreadB, self.lblThreadC, self.lblThreadD, self.lblThreadE, self.lblThreadF]
        self.pbThreadArray = [self.pbThread0, self.pbThread1, self.pbThread2, self.pbThread3, self.pbThread4, self.pbThread5, self.pbThread6, self.pbThread7, self.pbThread8, self.pbThread9]
        self.pbThreadArray = self.pbThreadArray + [self.pbThread10, self.pbThread11, self.pbThread12, self.pbThread13, self.pbThread14, self.pbThread15]

    def setSignals(self):
        self.chkbConvert.toggled.connect(self.toggleConvertSettings)
        self.btnDownloadEpisodesList.clicked.connect(self.getEpList)
        self.btnSelectAll.clicked.connect(self.selectAllEpisodes)
        self.btnDownload.clicked.connect(self.downloadSelectedEpisodes)
        self.appendLogs.connect(self.writeLog)
        self.sigConvert.connect(self.convertEpisode)

    def downloadSelectedEpisodes(self):
        if len(self.lstwEpisodesToDownload.selectedItems()) > 0:
            download_list = [None]
            download_list.pop(0)
            self.freezeSettings(False)
            self.btnDownload.setEnabled(False)
            self.btnDownloadEpisodesList.setEnabled(False)
            link_list = self.lstwEpisodesToDownload.selectedItems()
            for i in link_list:
                received = self.getVideoListFromURL(i)
                '''Get download list and merge with current'''
                if len(received) > 1:
                    received.pop(0)
                    download_list = download_list + received

            if len(download_list) > 0:
                self.lstwToDownload.clear()
                self.lstwToConvert.clear()
                for i in download_list:
                    self.lstwToDownload.addItem(i)
                self.downloadedEps = 0
                self.mustDownloadEps = self.lstwToDownload.count()
                self.pbDownloaded.setValue(0)
                self.pbDownloaded.setMaximum(self.mustDownloadEps)
                self.downloadThreadList = [DownloadEpisodeThread(self, 0)]
                for i in range(1, self.sbDownloadThreads.value()):
                    self.downloadThreadList.append(DownloadEpisodeThread(self, i))
                for i in range(0, self.sbDownloadThreads.value()):
                    self.downloadThreadList[i].start()
            else:
                self.freezeSettings(True)
                self.btnDownload.setEnabled(True)
                self.btnDownloadEpisodesList.setEnabled(True)

    '''Enable/Disable converting settings by (un)checking box'''
    def toggleConvertSettings(self):
        state = False
        if False == self.lineConvVideoSize.isEnabled():
            state = True
        self.lineConvVideoSize.setEnabled(state)
        self.cbOutputFormat.setEnabled(state)
        self.sbConvThreads.setEnabled(state)

    def selectAllEpisodes(self):
        if len(self.lstwEpisodesToDownload.selectedItems()) == self.lstwEpisodesToDownload.count():
            self.lstwEpisodesToDownload.clearSelection()
        else:
            self.lstwEpisodesToDownload.selectAll()

    def getEpList(self):
        self.btnDownloadEpisodesList.setEnabled(False)
        self.btnSelectAll.setEnabled(False)
        self.btnDownload.setEnabled(False)

        self.getEpisodesListFromWeb(self.lineLinkToSeries.text(), self.lblWhatAreWeDownloading, self.lstwEpisodesToDownload, self.txtLogs)

        if self.lstwEpisodesToDownload.count() > 0:
            self.lblEpisodesCount.setText(str(self.lstwEpisodesToDownload.count()))
            self.btnSelectAll.setEnabled(True)
            self.btnDownload.setEnabled(True)
        else:
            self.lblEpisodesCount.setText('-')

        self.btnDownloadEpisodesList.setEnabled(True)

    def freezeSettings(self, enabled):
        self.sbDownloadThreads.setEnabled(enabled)
        self.chkbConvert.setEnabled(enabled)
        if enabled is False:
            self.lineConvVideoSize.setEnabled(enabled)
            self.cbOutputFormat.setEnabled(enabled)
            self.sbConvThreads.setEnabled(enabled)
        else:
            if self.chkbConvert.isChecked() is True:
                self.lineConvVideoSize.setEnabled(enabled)
                self.cbOutputFormat.setEnabled(enabled)
                self.sbConvThreads.setEnabled(enabled)
