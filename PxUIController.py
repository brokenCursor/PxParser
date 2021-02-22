# -*- coding: utf-8 -*-

from PxExportWorker import PxExportWorker
import sys
import time
from PxUILayout import PxUILayout
from PyQt5 import QtCore, QtWidgets


class UIController(QtWidgets.QMainWindow, PxUILayout):

    __file_list = set()
    progess = 0  # Export progress
    __threads = []

    filter = [('GPS', ['TimeUS', 'Lng', 'Lat', 'Spd']), ('BARO', ['Alt']),
              ('AHR2', ['Roll', 'Pitch', 'Yaw']), ('MSG', ['Message'])]
    ru_namespace = {'GPS_TimeUS': 'Время', 'GPS_Lng': 'Долгота', 'GPS_Lat': 'Широта', 'GPS_Spd': 'Скорость',
                    'BARO_Alt': 'Высота', 'AHR2_Roll': 'Крен', 'AHR2_Pitch': 'Тангаж', 'AHR2_Yaw': 'Рысканье', 'MSG_Message': 'Статус'}
    en_namespace = {'GPS_TimeUS': 'Time', 'GPS_Lng': 'Longitude', 'GPS_Lat': 'Latitude', 'GPS_Spd': 'Speed',
                    'BARO_Alt': 'Altitude', 'AHR2_Roll': 'Roll', 'AHR2_Pitch': 'Pitch', 'AHR2_Yaw': 'Yaw', 'MSG_Message': 'Status'}
    def_namespace = {'GPS_TimeUS': 'GPS_TimeUS', 'GPS_Lng': 'GPS_Lng', 'GPS_Lat': 'GPS_Lat', 'GPS_Spd': 'GPS_Spd',
                     'BARO_Alt': 'BARO_Alt', 'AHR2_Roll': 'AHR2_Roll', 'AHR2_Pitch': 'AHR2_Pitch', 'AHR2_Yaw': 'AHR2_Yaw', 'MSG_Message': 'MSG_Message'}

    def __init__(self):
        """ Initialize UI """

        super().__init__()
        self.setupUi(self)
        self.__setup_actions()
        self.__setup_buttons()
        self.__setup_table()

    def __setup_actions(self) -> None:
        """ Connect actions to their fucntions, set shortcuts and tips """

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

    def __setup_buttons(self) -> None:
        """ Connect buttons to their functions, set tips """

        self.importButton.clicked.connect(self.__import_file)
        self.importButton.setStatusTip('Import file')

        self.exportButton.clicked.connect(self.__export)
        self.exportButton.setStatusTip('Export files')

        self.deleteButton.clicked.connect(self.__table_remove_selected_items)
        self.deleteButton.setStatusTip('Delete selected files')

    def __setup_table(self) -> None:
        """ Create file table, set header """

        self.fileTable.setColumnCount(1)
        header = self.fileTable.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.fileTable.setHorizontalHeaderLabels(['File path'])

    def __table_add_item(self, item) -> None:
        """ Add item (file) to table, disable editing """

        rowPosition = self.fileTable.rowCount()  # Set new row position as last row
        self.fileTable.insertRow(rowPosition)  # Insert row
        new_item = QtWidgets.QTableWidgetItem(item)  # Create item widget
        new_item.setFlags(QtCore.Qt.ItemIsSelectable |
                          QtCore.Qt.ItemIsEnabled)  # Set editing flags
        self.fileTable.setItem(
            rowPosition, 0, new_item)  # Insert item

    def __table_remove_selected_items(self) -> None:
        """ Remove selected items from table """

        items_to_remove = self.fileTable.selectedItems()
        self.__table_remove_items(items_to_remove)

    def __table_remove_items(self, items_to_remove) -> None:
        """ Remove items from items_to_remove from table and file_list"""

        for item in items_to_remove:
            self.__file_list.remove(item.text())
            self.fileTable.removeRow(item.row())

    def __table_get_all_items(self) -> list:
        """ Get all items from table """

        items = list()
        for col in range(self.fileTable.columnCount()):
            for row in range(self.fileTable.rowCount()):
                items.append(self.fileTable.item(row, col))
        return items

    def __get_file_path(self) -> str:
        """ Get path to file for importing """

        return QtWidgets.QFileDialog.getOpenFileName(self, 'Select file',
                                                     '.', "Log files (*.bin *.ulg)")[0]

    def __get_export_directory(self) -> str:
        """ Get path to directoty for exported files """

        return QtWidgets.QFileDialog.getExistingDirectory(self, 'Select directory')

    def updateProgressbar(self, progress) -> None:
        """ Add progress / len(file_list) to progressbar """

        self.progess += int(progress) / len(self.__file_list)
        self.progressBar.setValue(self.progess)

    def __createThread(self, worker) -> PxExportWorker:
        thread = worker
        worker.finished.connect(worker.stop)
        return thread

    def __export(self) -> None:
        """ Export function. Exports all/selected files from table """

        self.statusbar.showMessage('Exporting...')
        self.__disable_ui()
        time_msg = "GPS_TimeUS"
        interpolation = self.__get_interpolation()
        namespace = self.__get_namespace()
        export_as = self.__get_selected_file_type()
        selected_items = self.fileTable.selectedItems()
        items_to_export = selected_items if selected_items else self.__table_get_all_items()
        self.progess = 0
        self.progressBar.setValue(self.progess)
        self.progressBar.show()
        self.__threads.clear()
        export_to = self.__get_export_directory()
        for item in items_to_export:
            file = item.text()
            output_file_name = export_to + '/' +\
                file.split('/')[-1].split('.')[0] # Create full output file name
            worker = PxExportWorker(
                file, output_file_name, namespace, self.filter, export_as,
                time_msg, [time_msg], interpolation) # Create worker object
            thread = self.__createThread(worker) # Create thread with worker
            thread.start() # Start worker thread
            self.__threads.append(thread) # Save thread to list
            prev_progress = thread.parser.completed
            while thread.isRunning(): # Update progress bar. Re-writing needed
                curr_progress = thread.parser.completed
                self.updateProgressbar(curr_progress - prev_progress)
                prev_progress = curr_progress
            self.updateProgressbar(10)
            time.sleep(1)
            self.progressBar.hide()
        self.__table_remove_items(items_to_export) # Remove exported items
        self.statusbar.showMessage("Export done")
        self.__enable_ui()

    def __import_file(self) -> None:
        """ Add file to file_list and file table """

        file_path = self.__get_file_path()
        if file_path and file_path not in self.__file_list:
            self.__table_add_item(file_path)
            self.__file_list.add(file_path)

    def __get_selected_file_type(self) -> str:
        """ Return user-selected file type"""
        if self.txtButton.isChecked():
            return 'txt'
        elif self.csvButton.isChecked():
            return 'csv'
        elif self.xlsxButton.isChecked():
            return 'xlsx'

    def __get_interpolation(self) -> bool:
        """ Get interpolation flag from UI """

        if self.OnButton.isChecked():
            return True
        elif self.OffButton.isChecked():
            return False

    def __get_namespace(self):
        if self.defaultButton.isChecked():
            return self.def_namespace
        elif self.russianButton.isChecked():
            return self.ru_namespace
        elif self.englishButton.isChecked():
            return self.en_namespace

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

        self.OnButton.setEnabled(False)
        self.OffButton.setEnabled(False)

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

        self.OnButton.setEnabled(True)
        self.OffButton.setEnabled(True)

        self.menuFile.setEnabled(True)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = UIController()
    window.statusBar().showMessage('Ready')
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
