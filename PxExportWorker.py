from PxParser import PxParser
from PyQt5.QtCore import QThread, pyqtSignal


class PxExportWorker(QThread):
    """
    Class for threaded exportting
    """

    finished = pyqtSignal()

    parser = PxParser()
    target = ''

    def __init__(self, target, filename, namespace=dict(), filter=[], export_as='txt', time_msg="GPS_TimeUS",
                 data_msg="MSG_Message", msg_ignore=[], use_interpolation=False) -> None:
        super(self.__class__, self).__init__()
        self.parser.set_namespace(namespace)
        self.parser.set_time_msg(time_msg)
        self.parser.set_data_msg(data_msg)
        self.parser.set_msg_ignore(msg_ignore)
        self.parser.set_output_file(filename, export_as)
        if use_interpolation:
            self.parser.enable_interpolation()
        self.parser.set_msg_filter(filter)
        self.target = target

    def run(self):
        self.parser.process(self.target)
        self.finished.emit()

    def stop(self):
        self.threadactive = False
        self.terminate()
