
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QMainWindow, QMessageBox, QAction, QFileDialog


class PxMainUI(QMainWindow):

    def __init__(self):
        super().__init__()

        self.initUI()


    def initUI(self):

        self.setGeometry(0, 0, 600, 250)
        self.center()
        self.setWindowTitle('PxParser')
        self.statusBar().showMessage('Ready')

        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        importAction = QAction('Import', self)
        importAction.setShortcut('Ctrl+I')
        importAction.setStatusTip('Import file')
        importAction.triggered.connect(self.import_file)

        menubar = self.menuBar()

        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)
        fileMenu.addAction(importAction)

        self.show()

    def center(self):

        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def import_file(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', 
   'c:\\',"Image files (*.jpg *.gif)")
        print(fname)


if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = PxMainUI()
    sys.exit(app.exec_())