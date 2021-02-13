# -*- coding: utf-8 -*-

import sys
from PxUILayout import PxUILayout
from PyQt5 import QtCore, QtWidgets
from PxParser import PxParser


class UIController(QtWidgets.QMainWindow, PxUILayout):

    __file_list = set()

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.__setup_actions()
        self.__setup_buttons()
        self.__setup_table()

    def __setup_actions(self):
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

    def __setup_buttons(self):
        self.importButton.clicked.connect(self.__import_file)
        self.importButton.setStatusTip('Import file')
        self.exportButton.clicked.connect(self.__export)
        self.exportButton.setStatusTip('Export files')
        self.deleteButton.clicked.connect(self.__table_remove_selected_items)
        self.deleteButton.setStatusTip('Delete selected files')

    def __setup_table(self):
        self.fileTable.setColumnCount(1)
        header = self.fileTable.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.fileTable.setHorizontalHeaderLabels(['File path'])

    def __table_add_item(self, item):
        rowPosition = self.fileTable.rowCount()
        self.fileTable.insertRow(rowPosition)
        new_item =  QtWidgets.QTableWidgetItem(item)
        new_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.fileTable.setItem(
        rowPosition, 0, new_item)

    def __table_remove_selected_items(self):
        items_to_remove = self.fileTable.selectedItems()
        self.__table_remove_items(items_to_remove)

    def __table_remove_items(self, items_to_remove):
        for item in items_to_remove:
            self.__file_list.remove(item.text())
            self.fileTable.removeRow(item.row())

    def __table_get_all_items(self):
        items = list()
        for col in range(self.fileTable.columnCount()):
            for row in range(self.fileTable.rowCount()):
                items.append(self.fileTable.item(row, col))
        return items

    def __get_file_path(self):
        return QtWidgets.QFileDialog.getOpenFileName(self, 'Select file',
                                                     '.', "Log files (*.bin *.ulg)")[0]
    
    def __get_export_directory(self):
        return QtWidgets.QFileDialog.getExistingDirectory(self, 'Select directory')

    def __export(self):
        self.statusbar.showMessage('Exporting...')
        self.__disable_ui()
        time_msg = "GPS_TimeUS"
        data_msg = "MSG_Message"
        try:
            export_to = self.__get_export_directory()
            export_as = self.__get_selected_file_type()
            selected_items = self.fileTable.selectedItems()
            if selected_items:
                items_to_export = selected_items
            else:
                items_to_export = self.__table_get_all_items()
            files_to_export = [item.text() for item in items_to_export]
            self.progressBar.show()
            progress = 0
            for file in files_to_export:
                output_file_name = file.split('/')[-1].split('.')[0]
                parser = PxParser()
                parser.set_time_msg(time_msg)
                parser.set_data_msg(data_msg)
                parser.set_msg_ignore([time_msg, data_msg])
                parser.set_output_file(export_to + '/' + output_file_name, export_as)
                parser.process(file)
                while parser.completed < 100.0:
                    print(parser.completed)
                self.__table_remove_items(items_to_export)
        except PermissionError:
            pass
        finally:
            self.__enable_ui()

    def __export_thread(self):
        pass

    def __import_file(self):
        file_path = self.__get_file_path()
        if file_path and file_path not in self.__file_list:
            self.__table_add_item(file_path)
            self.__file_list.add(file_path)
 
    def __get_selected_file_type(self):
        if self.txtButton.isChecked():
            return 'txt'
        elif self.csvButton.isChecked():
            return 'csv'
        elif self.xlsxButton.isChecked():
            return 'xlsx'

    def __disable_ui(self):
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
        

    def __enable_ui(self):
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
