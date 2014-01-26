#!/usr/bin/python3

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

import sys
from gui_logic import MainWindow
from PySide.QtGui import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wnd = MainWindow()
    sys.exit(app.exec_())
