# -*- coding: utf-8 -*-

from typing import List
from PxExportWorker import PxExportWorker
import sys
import time
from PxUILayout import PxUILayout
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread


class UIController(QtWidgets.QMainWindow, PxUILayout):

    __file_list = set()
    progess = 0  # Exporting progress
    __threads = []

    def __init__(self):  # Initialize UI
        super().__init__()
        self.setupUi(self)
        self.__setup_actions()
        self.__setup_buttons()
        self.__setup_table()

    def __setup_actions(self):  # Setup actions' connections
        self.actionExit.setShortcut('Ctrl+Q')
        self.actionExit.setStatusTip('Quit PxParser')
        self.actionExit.triggered.connect(self.close)

        self.actionImport.setShortcut('Ctrl+I')
        self.actionImport.setStatusTip('Import file')
        self.actionImport.triggered.connect(self.__import_file)

        self.actionExport.setShortcut('Ctrl+E')
        self.actionExport.setStatusTip('Export files')
        self.actionExport.triggered.connect(self.__export)

        self.actionDeleteItem.setShortcut('Del')
        self.actionDeleteItem.setStatusTip('Delete selected files')
        self.actionDeleteItem.triggered.connect(
            self.__table_remove_selected_items)

    def __setup_buttons(self):  # Setup buttons' actions
        self.importButton.clicked.connect(self.__import_file)
        self.importButton.setStatusTip('Import file')
        self.exportButton.clicked.connect(self.__export)
        self.exportButton.setStatusTip('Export files')
        self.deleteButton.clicked.connect(self.__table_remove_selected_items)
        self.deleteButton.setStatusTip('Delete selected files')

    def __setup_table(self):  # Setup table of files
        self.fileTable.setColumnCount(1)
        header = self.fileTable.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.fileTable.setHorizontalHeaderLabels(['File path'])

    def __table_add_item(self, item):  # Add file to table of files
        rowPosition = self.fileTable.rowCount()
        self.fileTable.insertRow(rowPosition)
        new_item = QtWidgets.QTableWidgetItem(item)
        new_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.fileTable.setItem(
            rowPosition, 0, new_item)

    # Remove selected items from table
    def __table_remove_selected_items(self):
        items_to_remove = self.fileTable.selectedItems()
        self.__table_remove_items(items_to_remove)

    # Remove items from table o files and list if files
    def __table_remove_items(self, items_to_remove):
        for item in items_to_remove:
            self.__file_list.remove(item.text())
            self.fileTable.removeRow(item.row())

    def __table_get_all_items(self):  # Get a list of items from table
        items = list()
        for col in range(self.fileTable.columnCount()):
            for row in range(self.fileTable.rowCount()):
                items.append(self.fileTable.item(row, col))
        return items

    def __get_file_path(self):  # Get path to file for importing
        return QtWidgets.QFileDialog.getOpenFileName(self, 'Select file',
                                                     '.', "Log files (*.bin *.ulg)")[0]

    def __get_export_directory(self):  # Select the directory to export to
        return QtWidgets.QFileDialog.getExistingDirectory(self, 'Select directory')

    # Update progress bar by thread_progress / number_of_threads
    def updateProgressbar(self, progress):
        self.progess += progress / len(self.__file_list)
        self.progressBar.setValue(self.progess)

    def __createThread(self, worker):  # Create worker thread
        thread = QThread()
        worker.moveToThread(thread)
        worker.progress.connect(self.updateProgressbar)
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(thread.terminate)
        worker.finished.connect(worker.deleteLater)
        return thread

    def __export(self):  # Export files
        self.statusbar.showMessage('Exporting...')
        self.__disable_ui()
        time_msg = "GPS_TimeUS"
        data_msg = "MSG_Message"
        try:
            export_to = self.__get_export_directory()
            export_as = self.__get_selected_file_type()
            selected_items = self.fileTable.selectedItems()
            items_to_export = selected_items if selected_items else self.__table_get_all_items()
            self.progess = 0
            self.progressBar.setValue(0)
            self.progressBar.show()
            self.__threads.clear()
            for item in items_to_export:
                file = item.text()
                output_file_name = export_to + '/' +\
                    file.split('/')[-1].split('.')[0]
                worker = PxExportWorker(
                    file, output_file_name, export_as, time_msg, data_msg,
                    msg_ignore=[time_msg, data_msg])
                thread = self.__createThread(worker)
                thread.start()
                self.__threads.append(thread)
                print('file done')
            self.__table_remove_items(items_to_export)
        except PermissionError:
            self.statusbar('Export aborted')
        finally:
            self.__enable_ui()

    def __import_file(self):  # Import files
        file_path = self.__get_file_path()
        if file_path and file_path not in self.__file_list:
            self.__table_add_item(file_path)
            self.__file_list.add(file_path)

    def __get_selected_file_type(self):  # Get selected export filetype
        if self.txtButton.isChecked():
            return 'txt'
        elif self.csvButton.isChecked():
            return 'csv'
        elif self.xlsxButton.isChecked():
            return 'xlsx'

    def __disable_ui(self):  # Disable almost every element of the UI
        self.importButton.setEnabled(False)
        self.exportButton.setEnabled(False)
        self.deleteButton.setEnabled(False)

        self.txtButton.setEnabled(False)
        self.xlsxButton.setEnabled(False)
        self.csvButton.setEnabled(False)

        self.russianButton.setEnabled(False)
        self.englishButton.setEnabled(False)
        self.defaultButton.setEnabled(False)

        self.actionExit.setEnabled(False)
        self.actionImport.setEnabled(False)
        self.actionExport.setEnabled(False)
        self.actionDeleteItem.setEnabled(False)

        self.menuFile.setEnabled(False)

    def __enable_ui(self):  # Enable all disabled elements
        self.importButton.setEnabled(True)
        self.exportButton.setEnabled(True)
        self.deleteButton.setEnabled(True)

        self.txtButton.setEnabled(True)
        self.xlsxButton.setEnabled(True)
        self.csvButton.setEnabled(True)

        self.russianButton.setEnabled(True)
        self.englishButton.setEnabled(True)
        self.defaultButton.setEnabled(True)

        self.actionExit.setEnabled(True)
        self.actionImport.setEnabled(True)
        self.actionExport.setEnabled(True)
        self.actionDeleteItem.setEnabled(True)

        self.menuFile.setEnabled(True)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = UIController()
    window.statusBar().showMessage('Ready')
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
