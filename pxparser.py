import struct
import xlsxwriter
from io import TextIOWrapper
from xlsxwriter.worksheet import Worksheet
from pathlib import Path


class PxParser:
    BLOCK_SIZE = 8192
    MSG_HEADER_LEN = 3
    MSG_HEAD1 = 0xA3
    MSG_HEAD2 = 0x95
    MSG_FORMAT_PACKET_LEN = 89
    MSG_FORMAT_STRUCT = "BB4s16s64s"
    MSG_TYPE_FORMAT = 0x80
    FORMAT_TO_STRUCT = {
        "a": ("a", None),
        "b": ("b", None),
        "B": ("B", None),
        "h": ("h", None),
        "H": ("H", None),
        "i": ("i", None),
        "I": ("I", None),
        "f": ("f", None),
        "d": ("d", None),
        "n": ("4s", None),
        "N": ("16s", None),
        "Z": ("64s", None),
        "c": ("h", 0.01),
        "C": ("H", 0.01),
        "e": ("i", 0.01),
        "E": ("I", 0.01),
        "L": ("i", 0.0000001),
        "M": ("b", None),
        "q": ("q", None),
        "Q": ("Q", None),
    }

    __msg_filter = list()
    __msg_ignore = list()
    __msg_labels = dict()
    __msg_descrs = dict()
    __msg_names = list()
    __msg_filter_map = dict()
    __txt_columns = list()
    __txt_data = dict()
    __namespace = dict()
    __prev_data = list()
    __next_data = list()
    __buffer = bytearray()
    __msg_id_ignore = set()
    __pointer = 0
    __delim_char = '\t'
    __null_char = ''
    __time_msg = ""
    __file = ""
    __txt_updated = False
    __time_msg_id = 0
    __status_msg = ""
    __debug_out = False
    __correct_errors = False
    __interpolation = False
    __workbook = None
    completed = 0
    msg_count = 0

    # Set a custom namespace to print instead of __txt_columns
    def set_namespace(self, namespace):
        self.__namespace = namespace

    # Set a char to print if there is no data in the column
    def set_null_char(self, csv_null):
        self.__null_char = csv_null

    # Set a message header filter for output
    def set_msg_filter(self, msg_filter):
        self.__msg_filter = msg_filter

    # Set name for message to parse time from
    def set_time_msg(self, time_msg):
        self.__time_msg = time_msg

    # Set a status message name. Defaulted to log
    def set_data_msg(self, status_msg):
        self.__status_msg = status_msg

    # Set enable/disable debug output
    def enable_debug_out(self):
        self.__debug_out = True

    # Enable error correction. If enabled tries to bypass errors error
    def enable_err_correct(self):
        self.__correct_errors = True

    def enable_interpolation(self):  # Set a constant clock flag
        self.__interpolation = True

    # Set a list of messages to ignore during processing
    def set_msg_ignore(self, msg_ignore):
        self.__msg_ignore = msg_ignore

    #
    def set_output_file(self, file_name, file_type):
        if file_type == 'txt' or file_type == 'csv':
            self.__file = open(file_name + '.' + file_type, "w+")
            self.__delim_char = ',' if file_type == 'csv' else '\t'
        elif file_type == 'xlsx':
            self.__workbook = xlsxwriter.Workbook(
                file_name + '.' + file_type, {'nan_inf_to_errors': True})
            self.__file = self.__workbook.add_worksheet()

    # Convert Cstring to string object
    def __to_utf8(self, cstr):
        """ Convert ASCII to UTF-8 """
        return str(cstr, 'ascii').split('\0')[0]

    def process(self, fn):  # Main function
        file_size = Path(fn).stat().st_size  # Get file size
        if self.__debug_out:
            for msg_name, show_fields in self.__msg_filter:
                self.__msg_filter_map[msg_name] = show_fields
        first_data_msg = True
        f = open(fn, "rb")  # Open log file
        bytes_read = 0
        while True:
            chunk = f.read(self.BLOCK_SIZE)  # Get chunk
            if len(chunk) == 0:  # Quit if block is empty
                break
            # Add chunk to buffer
            self.__buffer = self.__buffer[self.__pointer:] + chunk
            self.__pointer = 0  # Rest pointer
            while self.__bytesLeft() >= self.MSG_HEADER_LEN:  # If past header
                head1 = self.__buffer[self.__pointer]
                head2 = self.__buffer[self.__pointer+1]
                if (head1 != self.MSG_HEAD1 or head2 != self.MSG_HEAD2):  # Check header integrity
                    if self.__correct_errors:  # If correction enabled, skip chunk
                        self.__pointer += 1
                        continue
                    else:  # If correction disabled, raise exception
                        raise Exception("Invalid header at %i (0x%X): %02X %02X, must be %02X %02X" % (
                            bytes_read + self.__pointer, bytes_read + self.__pointer, head1, head2, self.MSG_HEAD1, self.MSG_HEAD2))
                # Get message type
                msg_type = self.__buffer[self.__pointer + 2]
                if msg_type == self.MSG_TYPE_FORMAT:  # If it's format description
                    if self.__bytesLeft() < self.MSG_FORMAT_PACKET_LEN:  # If remaining lenght less than format message
                        break  # Quit
                    self.__parseMsgDescr()  # Parse it
                else:  # Parse data message
                    # Get message discription
                    msg_descr = self.__msg_descrs[msg_type]
                    if msg_descr == None:
                        # If type unknown, raise exception
                        raise Exception("Unknown msg type: %i" % msg_type)
                    msg_length = msg_descr[0]  # Set message length
                    if self.__bytesLeft() < msg_length:
                        break  # Quit if remaining length lesser than msg_length
                    if first_data_msg:  # If it's first data message
                        if not self.__debug_out:
                            self.__initOutput()  # Initialize file
                        first_data_msg = False
                    # Get data from message by it's description
                    self.__parseMsg(msg_descr)
            bytes_read += self.__pointer  # Move pointer
            self.completed = bytes_read / file_size * 100  # Update completion status
            if not self.__debug_out and self.__time_msg != None and self.__txt_updated:  # Ignore this
                self.__processData()  # Process data
        f.close()  # Close log file
        if type(self.__file) is Worksheet:  # If writing to .xlsx, close file
            self.__workbook.close()

    def __bytesLeft(self):
        """ Get amout of bytes left in file being processed """
        return len(self.__buffer) - self.__pointer

    def __filterMsg(self, msg_name):
        """ Create message filter """
        show_fields = "*"
        if self.__msg_filter_map:
            show_fields = self.__msg_filter_map.get(msg_name)
        return show_fields

    def __initOutput(self):
        """ Create output file, write column headers """
        if not self.__msg_filter:  # If filter is empty, enable all messages
            for msg_name in self.__msg_names:
                self.__msg_filter.append((msg_name, "*"))

        # Fill __txt_columns and __txt_data in accrodig to the __msg_filter
        for msg_name, show_fields in self.__msg_filter:
            if show_fields == "*":
                show_fields = self.__msg_labels.get(msg_name, [])
            self.__msg_filter_map[msg_name] = show_fields
            for field in show_fields:
                full_label = msg_name + "_" + field
                self.__txt_columns.append(full_label)
                self.__txt_data[full_label] = None

        # Fill in __msg_ignore_id in accroding to the __msg_ignore
        for col in self.__txt_columns:
            if col in self.__msg_ignore:  # If message col is in __msg_ignore
                self.__msg_id_ignore.add(self.__txt_columns.index(col))
        self.__status_msg_id = self.__txt_columns.index(self.__status_msg)
        self.__time_msg_id = self.__txt_columns.index(self.__time_msg)
        self.__msg_id_ignore.add(self.__time_msg_id)

        headers = []

        if self.__namespace:
            for column in self.__txt_columns:  # Check every column
                if column in self.__namespace:  # If it has a custom name, use it
                    headers.append(self.__namespace[column])
                else:
                    # If there doest have a custom name, use default from __txt_columns
                    headers.append(column)
        else:
            # If __namesapce is empty, use default columns headers
            headers = self.__txt_columns

        if type(self.__file) is TextIOWrapper:  # Output headers
            print(self.__delim_char.join(headers), file=self.__file)
        elif type(self.__file) is Worksheet:
            for h in headers:
                self.__file.write(0, headers.index(h), h)
        else:
            print(self.__delim_char.join(headers))

    def __processData(self):  # Process raw data
        """ Convert to correct type, apply interpolation if needed """
        data = []
        for full_label in self.__txt_columns:  # Fill in data accordigly to __txt_columns
            # Get single string from data dictionary
            val = self.__txt_data[full_label]
            if not val:  # If string is empty
                val = self.__null_char  # Put null char in
            else:  # If there is some data
                if str(val).isnumeric():
                    val = int(val)
                elif str(val).replace('.', '').isnumeric():
                    try:
                        val = float(val)
                    except ValueError:
                        val = str(val)
                else:
                    val = str(val)

            data.append(val)

        if self.__interpolation:
            if not self.__next_data:
                self.__next_data = data[:]
                return
            else:  # If __next_data contains something
                curr_data = self.__next_data[:]
                prev_data = curr_data[:]
                self.__next_data = data[:]  # Update __next_data
                if self.__prev_data:
                    time_diff = (
                        (curr_data[self.__time_msg_id] - self.__prev_data[self.__time_msg_id]) // 1000)
                    # Calculate a multiplier based on time difference for curr_data to reach a round digit time
                    to_round_time = (100 - (time_diff % 100)) * 0.0001
                    extra_msg_count = time_diff // 100
                    for count in range(extra_msg_count):
                        if count == 0 and to_round_time > 0:  # If it's first extra message and time is not a round number
                            # Multiply every string in list by to_round_time multiplier
                            for i in range(len(curr_data)):
                                if type(curr_data[i]) is str or i in self.__msg_id_ignore or curr_data[i] == self.__prev_data[i]:
                                    continue
                                elif self.__next_data[i] > curr_data[i]:
                                    curr_data[i] += curr_data[i] * \
                                        to_round_time
                                else:
                                    curr_data[i] -= curr_data[i] * \
                                        to_round_time
                            curr_data[self.__time_msg_id] = self.msg_count * 100
                            self.__printData(curr_data)
                        tmp = curr_data[:]  # Create a temporary data list
                        for id in range(len(curr_data)):  # Interpolate data
                            if type(tmp[id]) is str or id in self.__msg_id_ignore or self.__next_data[id] == curr_data[id]:
                                continue
                            elif self.__next_data[id] > curr_data[id]:
                                tmp[id] = curr_data[id] + (
                                    ((self.__next_data[id] - curr_data[id]) / extra_msg_count) * count)
                            else:
                                tmp[id] = curr_data[id] - (
                                    ((curr_data[id] - self.__next_data[id]) / extra_msg_count) * count)
                        tmp[self.__time_msg_id] = self.msg_count * 100
                        self.__printData(tmp)  # Print data
                else:  # If __prev_data empty
                    # Calculate current time by multiplying amount of messages by clock time (100 ms)
                    curr_data[self.__time_msg_id] = 0
                    self.__printData(curr_data)  # Print data
                self.__prev_data = prev_data[:]
        else:
            self.__printData(data)

    def __parseMsgDescr(self):

        data = struct.unpack(
            self.MSG_FORMAT_STRUCT, self.__buffer[self.__pointer + 3: self.__pointer + self.MSG_FORMAT_PACKET_LEN])
        msg_type = data[0]
        if msg_type != self.MSG_TYPE_FORMAT:
            msg_length = data[1]
            msg_name = self.__to_utf8(data[2])
            msg_format = self.__to_utf8(data[3])
            msg_labels = self.__to_utf8(data[4]).split(",")
            msg_struct = ""
            msg_mults = []
            for c in msg_format:
                try:
                    f = self.FORMAT_TO_STRUCT[c]
                    msg_struct += f[0]
                    msg_mults.append(f[1])
                except KeyError as e:
                    raise Exception("Unsupported format char: %s in message %s (%i)" % (
                        c, msg_name, msg_type))
            msg_struct = "<" + msg_struct   # force little-endian
            self.__msg_descrs[msg_type] = (
                msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults)
            self.__msg_labels[msg_name] = msg_labels
            self.__msg_names.append(msg_name)
            if self.__debug_out:
                if self.__filterMsg(msg_name) != None:
                    print("MSG FORMAT: type = %i, length = %i, name = %s, format = %s, labels = %s, struct = %s, mults = %s" % (
                        msg_type, msg_length, msg_name, msg_format, str(msg_labels), msg_struct, msg_mults))
        self.__pointer += self.MSG_FORMAT_PACKET_LEN

    def __parseMsg(self, msg_descr):
        """ Get raw data from file """
        # Disassemble msg_descr
        msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults = msg_descr
        show_fields = self.__filterMsg(msg_name)  # Get filter

        if show_fields:   # Parse data from file to list
            data = list(struct.unpack(
                msg_struct, self.__buffer[self.__pointer+self.MSG_HEADER_LEN:self.__pointer+msg_length]))

            for i in range(len(data)):
                if type(data[i]) is str:
                    data[i] = self.__to_utf8(data[i])
                if msg_mults[i]:
                    data[i] *= msg_mults[i]  # apply multuplyer if needed
                label = msg_labels[i]
                if label in show_fields:  # If label is in filter
                    # Add parsed raw data to __txt_data
                    self.__txt_data[msg_name + "_" + label] = data[i]
                    if self.__time_msg != None and msg_name != self.__time_msg:
                        self.__txt_updated = True
            if self.__time_msg == None:
                self.__processData()

        self.__pointer += msg_length

    def __printData(self, data):
        """ Write data to file/output """

        data = list(map(lambda val: val.strip("'").strip(
            "b'").strip("\\x00") if type(data) is str and "\\x00" in data else val, data))  # Clear null termination if needed

        if type(self.__file) is TextIOWrapper:  # Convert to str, join with delim and write to file
            print(self.__delim_char.join(list(map(str, data))), file=self.__file)

        elif type(self.__file) is Worksheet:
            for d in data:
                try:  # Try converting to float
                    self.__file.write(self.msg_count + 1,
                                      data.index(d), float(d))
                except ValueError:  # If failed, convert to string
                    self.__file.write(self.msg_count + 1, data.index(d), d)
        else:  # If no output file set, write to stdout
            print(self.__delim_char.join(data))
        self.msg_count += 1
