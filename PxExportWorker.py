from PxParser import PxParser
from PyQt5.QtCore import QObject, pyqtSignal


class PxExportWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(float)

    parser = PxParser()
    target = ''

    def __init__(self, target, filename, export_as='txt', time_msg="GPS_TimeUS",
                 data_msg="MSG_Message", msg_ignore=[]) -> None:
        super(self.__class__, self).__init__()
        self.parser.set_time_msg(time_msg)
        self.parser.set_data_msg(data_msg)
        self.parser.set_msg_ignore(msg_ignore)
        self.parser.set_output_file(filename, export_as)
        self.target = target
        print('init done')

    def run(self):
        print('thread started')
        self.parser.process(self.target)
        while self.parser.completed < 100:
            print(self.parser.completed)
            self.progress.emit(self.parser.completed)
        self.finished.emit()
        print('thread done')
