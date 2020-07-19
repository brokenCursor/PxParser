# -*- coding: utf-8 -*-

from __future__ import print_function

"""Dump binary log generated by PX4's sdlog2 or APM as TXT
    
Usage: python px4parser <log.bin>  [-e] [-d delimiter] [-n] [-m MSG[.field1,field2,...]] [-f file.txt]

	-e	Recover from errors.
    
    -d  Use "delimiter" in file. Default is TAB.
    
    -n  Use custom namespace.

    -c  Use constant clock.
    
    -m MSG[.field1,field2,...]
        Dump only messages of specified type, and only specified fields.
        Multiple -m options allowed.

    -f Output file.
"""

__author__  = "Roman " + "broken_cursor" + " Shvindt. Based on sdlog2_dump"
__version__ = "v0.5_release"

import struct, sys

if sys.hexversion >= 0x030000F0:
    runningPython3 = True
    def _parseCString(cstr):
        return str(cstr, 'ascii').split('\0')[0]
else:
    runningPython3 = False
    def _parseCString(cstr):
        return str(cstr).split('\0')[0]

class SDLog2Parser:
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
    __delim_char = "\t"             # Character to put in between columns
    __null_char = ""                # Charecter to put if there is no data in column 
    __msg_filter = []               # List of messages to output
    __msg_ignore = []               # List of messages to ignore during processing
    __msg_id_ignore = []            # IDs of messages to ignore during processing. Fills automaticaly from data in __msg_ignore
    __time_msg = None               # Name of the message that contains time
    __time_msg_id = 0               # Time message ID. Fills automaticaly
    __status_msg = None             # Name of the status message
    __status_msg_id = 0             # ID of the status message. Fills automaticaly
    __debug_out = False             # Debug output flag
    __correct_errors = False        # Error corrcetion flag
    __file = None                   # Output file name
    __namespace = {}                # Columns names to print instead of __txt_columns
    __prev_data = []                
    __next_data = []
    __constant_clock = False        # Constant message output clock flag
    msg_count = 0                   
    
    def __init__(self):
        return

    
    def reset(self):                # Reset variables default
        self.__msg_descrs = {}      # Message descriptions by message type map
        self.__msg_labels = {}      # Message labels by message name map
        self.__msg_names = []       # Message names in the same order as FORMAT messages
        self.__buffer = bytearray() # Buffer for input binary data
        self.__pointer = 0          # Read pointer in buffer
        self.__txt_columns = []     # CSV file columns in correct order in format "MSG.label"
        self.__txt_data = {}        # Current values for all columns
        self.__txt_updated = False  # Is updated flag
        self.__msg_filter_map = {}  # filter in form of map, with '*" expanded to full list of fields
        self.__prev_data = []       # Previous data buffer 
        self.__next_data = []       # Next data buffer
        self.msg_count = 0          # Printed messages count
    
    def setNamespace(self, namespace):      # Set a custom namespace to print instead of __txt_columns
        self.__namespace = namespace

    def setDelimiterChar(self, csv_delim):  # Set a char to print in between columns
        self.__delim_char = csv_delim
    
    def setNullChar(self, csv_null):        # Set a char to print if there is no data in the column
        self.__null_char = csv_null
    
    def setMsgFilter(self, msg_filter):     # Set a filter of messages to output
        self.__msg_filter = msg_filter
    
    def setTimeMsg(self, time_msg):         # Set time message name
        self.__time_msg = time_msg

    def setDataMsg(self, status_msg):       # Set a status message name
        self.__status_msg = status_msg
    
    def setDebugOut(self, debug_out):       # Set a debug output flag
        self.__debug_out = debug_out

    def setCorrectErrors(self, correct_errors): # Set an error correction flag
        self.__correct_errors = correct_errors

    def setConstantClock(self, constant_clock): # Set a constant clock flag
        self.__constant_clock = constant_clock

    def setMsgIgnore(self, msg_ignore):     # Set a list of messages to ignore during processing
        self.__msg_ignore = msg_ignore

    def setFileName(self, file_name):       # Set an output file's name
    	self.__file_name = file_name
    	if file_name != None:
    		self.__file = open(file_name, 'w+')
    	else:
    		self.__file = None

    
    def process(self, fn): # Main function
        self.reset()
        if self.__debug_out:
            # init __msg_filter_map
            for msg_name, show_fields in self.__msg_filter:
                self.__msg_filter_map[msg_name] = show_fields
        first_data_msg = True
        f = open(fn, "rb")
        bytes_read = 0
        while True:
            chunk = f.read(self.BLOCK_SIZE)
            if len(chunk) == 0:
                break
            self.__buffer = self.__buffer[self.__pointer:] + chunk
            self.__pointer = 0
            while self.__bytesLeft() >= self.MSG_HEADER_LEN:
                head1 = self.__buffer[self.__pointer]
                head2 = self.__buffer[self.__pointer+1]
                if (head1 != self.MSG_HEAD1 or head2 != self.MSG_HEAD2):
                    if self.__correct_errors:
                        self.__pointer += 1
                        continue
                    else:
                        raise Exception("Invalid header at %i (0x%X): %02X %02X, must be %02X %02X" % (bytes_read + self.__pointer, bytes_read + self.__pointer, head1, head2, self.MSG_HEAD1, self.MSG_HEAD2))
                msg_type = self.__buffer[self.__pointer+2]
                if msg_type == self.MSG_TYPE_FORMAT:
                    # parse FORMAT message
                    if self.__bytesLeft() < self.MSG_FORMAT_PACKET_LEN:
                        break
                    self.__parseMsgDescr()
                else:
                    # parse data message
                    msg_descr = self.__msg_descrs[msg_type]
                    if msg_descr == None:
                        raise Exception("Unknown msg type: %i" % msg_type)
                    msg_length = msg_descr[0]
                    if self.__bytesLeft() < msg_length:
                        break
                    if first_data_msg:
                        # build TXT columns and init data map
                        if not self.__debug_out:
                            self.__initOutput()
                        first_data_msg = False
                    self.__parseMsg(msg_descr)
            bytes_read += self.__pointer
            if not self.__debug_out and self.__time_msg != None and self.__txt_updated:
                self.__processData()
        f.close()
    
    def __bytesLeft(self):              # Get an amout of bytes left 
        return len(self.__buffer) - self.__pointer
    
    def __filterMsg(self, msg_name):    # Process filtering
        show_fields = "*"
        if len(self.__msg_filter_map) > 0:
            show_fields = self.__msg_filter_map.get(msg_name)
        return show_fields
    
    def __initOutput(self):             # Init programs output
        if len(self.__msg_filter) == 0: # If filter is impty, fill it with eptyness sings
            for msg_name in self.__msg_names:
                self.__msg_filter.append((msg_name, "*"))

        for msg_name, show_fields in self.__msg_filter:         # Fill in __txt_columns and __txt_data in accrodig to the __msg_filter
            if show_fields == "*":
                show_fields = self.__msg_labels.get(msg_name, [])
            self.__msg_filter_map[msg_name] = show_fields
            for field in show_fields:
                full_label = msg_name + "_" + field
                self.__txt_columns.append(full_label)
                self.__txt_data[full_label] = None

        for i in self.__txt_columns:                            # Fill in __msg_ignore_id in accroding to the __msg_ignore
            if i in self.__msg_ignore:                          # If message name is present in __msg_ignore
                self.__msg_id_ignore.append(self.__txt_columns.index(i)) # Put it's ID from __txt_columns to __msg_ignore_id
        self.__status_msg_id = self.__txt_columns.index(self.__status_msg) # Get status message id from __txt_columns and put it in __status_msg_id
        self.__time_msg_id = self.__txt_columns.index(self.__time_msg)     # Get time message id from __txt_columns and put it in __time_msg_id

        headers = [] # Create a headers list
        if self.__namespace: # If __namespace is not empty (i.e use __namespace instead of __txt_columns in output)
            for column in self.__txt_columns: # Check every column
                if column in self.__namespace: # If it has a custom name, use it
                    headers.append(self.__namespace[column])
                else:
                    headers.append(column) # If there doest have a custom name, use default from __txt_columns 
        else:
            headers = self.__txt_columns # If there isn't 

        if self.__file != None:
            print(self.__delim_char.join(headers), file=self.__file)
        else:
            print(self.__delim_char.join(headers))
    

    def __processData(self): #Process data 
        data = []
        for full_label in self.__txt_columns: #parse into list data
            v = self.__txt_data[full_label]
            if v == None:
                v = self.__null_char
            else:
                v = str(v)
            data.append(v)
        if self.__constant_clock:
            if not self.__next_data: #complicated
                self.__next_data = data[:]
                return 0
            else:
                output = self.__next_data[:]
                prev_data = output[:]
                self.__next_data = data[:]
                if self.__prev_data:
                    diff = ((int(output[0]) - int(self.__prev_data[0])) // 1000)
                    to_round = float((100 - (diff%100)) * 0.0001)
                    diff //= 100
                    for count in range(1, diff + 1):
                        if count == 1 and to_round != 1.0:
                            for i in range(len(output)):
                                if i == self.__time_msg_id or output[i] == self.__prev_data[i] or i in self.__msg_id_ignore:
                                    continue
                                if self.__next_data[i] > output[i]:
                                    output[i] = str(float(output[i]) + (float(output[i]) * to_round))
                                else:
                                    output[i] = str(float(output[i]) - (float(output[i]) * to_round))
                            output[self.__time_msg_id] = str(self.msg_count * 100)
                            self.__printData(output)
                            self.msg_count += 1
                            tmp = output[:]
                        for id in range(len(output)):
                            if id in self.__msg_id_ignore or self.__next_data[id] == output[id]:
                                continue
                            elif self.__next_data[id] > output[id]:
                                tmp[id] = str(float(output[id]) + (((float(self.__next_data[id]) - float(output[id])) / diff) * count))
                            else:
                                tmp[id] = str(float(output[id]) - (((float(output[id]) - float(self.__next_data[id])) / diff) * count))
                        tmp[self.__time_msg_id] = str(self.msg_count * 100)
                        self.__printData(tmp)                
                        self.msg_count += 1
                else:
                    output[0] = str(self.msg_count)
                    self.__printData(output)
                    self.msg_count+=1
                self.__prev_data = prev_data[:]
        else:
           self.__printData(data) 

    def __parseMsgDescr(self):
        if runningPython3:
            data = struct.unpack(self.MSG_FORMAT_STRUCT, self.__buffer[self.__pointer + 3 : self.__pointer + self.MSG_FORMAT_PACKET_LEN])
        else:
            data = struct.unpack(self.MSG_FORMAT_STRUCT, str(self.__buffer[self.__pointer + 3 : self.__pointer + self.MSG_FORMAT_PACKET_LEN]))
        msg_type = data[0]
        if msg_type != self.MSG_TYPE_FORMAT:
            msg_length = data[1]
            msg_name = _parseCString(data[2])
            msg_format = _parseCString(data[3])
            msg_labels = _parseCString(data[4]).split(",")
            # Convert msg_format to struct.unpack format string
            msg_struct = ""
            msg_mults = []
            for c in msg_format:
                try:
                    f = self.FORMAT_TO_STRUCT[c]
                    msg_struct += f[0]
                    msg_mults.append(f[1])
                except KeyError as e:
                    raise Exception("Unsupported format char: %s in message %s (%i)" % (c, msg_name, msg_type))
            msg_struct = "<" + msg_struct   # force little-endian
            self.__msg_descrs[msg_type] = (msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults)
            self.__msg_labels[msg_name] = msg_labels
            self.__msg_names.append(msg_name)
            if self.__debug_out:
                if self.__filterMsg(msg_name) != None:
                    print("MSG FORMAT: type = %i, length = %i, name = %s, format = %s, labels = %s, struct = %s, mults = %s" % (
                                msg_type, msg_length, msg_name, msg_format, str(msg_labels), msg_struct, msg_mults))
        self.__pointer += self.MSG_FORMAT_PACKET_LEN
    
    def __parseMsg(self, msg_descr):
        msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults = msg_descr        
        if not self.__debug_out and self.__time_msg != None and msg_name == self.__time_msg and self.__txt_updated:
            self.__processData()
            self.__txt_updated = False
        show_fields = self.__filterMsg(msg_name)
        if (show_fields != None):
            if runningPython3:
                data = list(struct.unpack(msg_struct, self.__buffer[self.__pointer+self.MSG_HEADER_LEN:self.__pointer+msg_length]))
            else:
                data = list(struct.unpack(msg_struct, str(self.__buffer[self.__pointer+self.MSG_HEADER_LEN:self.__pointer+msg_length])))
            for i in range(len(data)):
                if type(data[i]) is str:
                    data[i] = _parseCString(data[i])
                m = msg_mults[i]
                if m != None:
                    data[i] = data[i] * m
            if self.__debug_out:
                s = []
                for i in range(len(data)):
                    label = msg_labels[i]
                    if show_fields == "*" or label in show_fields:
                        s.append(label + "=" + str(data[i]))
                            
                print("MSG %s: %s" % (msg_name, ", ".join(s)))

            else:
                # update  data buffer
                for i in range(len(data)):
                    label = msg_labels[i]
                    if label in show_fields:
                        self.__txt_data[msg_name + "_" + label] = data[i]
                        if self.__time_msg != None and msg_name != self.__time_msg:
                            self.__txt_updated = True
                if self.__time_msg == None:
                    self.__processData()


        self.__pointer += msg_length
        
    def __printData(self, data): #print to output
        print(data)
        for id in range(len(data)):
            if id == self.__status_msg_id:
                data[self.__status_msg_id] = data[self.__status_msg_id].strip("'").lstrip("b'").strip('\\x00')
                continue

            if len(data[id]) > 10 and id != self.__time_msg_id:
                data[id] = data[id][:8]
            elif len(data[id]) < 8:
                data[id] += '\t'

        if self.__file != None:
            print(self.__delim_char.join(data), file=self.__file)
        else:
            print(self.__delim_char.join(data))
       

def _main():
    if len(sys.argv) < 2:
        print("Usage: python px4parser.py <log.bin> [-v] [-e] [-d delimiter] [-n] [-c] [-m MSG[.field1,field2,...]] [-t TIME_MSG_NAME]\n")
        print("\t-v\tUse plain debug output instead of TXT.\n")
        print("\t-e\tRecover from errors.\n")
        print("\t-d\tUse \"delimiter\" in output. Default is \",\".\n")
        print("\t-n\tUse custom namespace.\n")
        print("\t-c\tUse constant clock.\n")
        print("\t-m MSG[.field1,field2,...]\n\t\tDump only messages of specified type, and only specified fields.\n\t\tMultiple -m options allowed.")
        print("\t-t\tSpecify TIME message name to group data messages by time\n")
        print("\t-f\tPrint to file instead of stdout")
        return
    fn = sys.argv[1]
    debug_out = False
    correct_errors = False
    msg_filter = [('GPS', ['TimeUS', 'Lng', 'Lat', 'Spd']), ('BARO', ['Alt']), ('AHR2', ['Roll', 'Pitch', 'Yaw']), ('MSG', ['Message'])]
    csv_null = ""
    csv_delim = "\t"
    time_msg = "GPS_TimeUS"
    data_msg = "MSG_Message"
    msg_ignore = [time_msg, data_msg]
    file_name = None
    constant_clock = False
    opt = None
    default_namespace = {'GPS_TimeUS':'GPS_TimeUS', 'GPS_Lng':'GPS_Lng\t', 'GPS_Lat':'GPS_Lat\t', 'GPS_Spd':'GPS_Spd\t', 'BARO_Alt':'BARO_Alt', 'AHR2_Roll':'AHR2_Roll', 'AHR2_Pitch':'AHR2_Pitch', 'AHR2_Yaw':'AHR2_Yaw'}
    custom_namespace = {'GPS_TimeUS':'Время\t', 'GPS_Lng':'Долгота\t', 'GPS_Lat':'Широта\t', 'GPS_Spd':'Скорость', 'BARO_Alt':'Высота\t', 'AHR2_Roll':'Крен\t', 'AHR2_Pitch':'Тангаж\t', 'AHR2_Yaw':'Рысканье'}
    use_custom_namespace = False
    for arg in sys.argv[2:]:
        if opt != None:
            if opt == "d":
                csv_delim = arg
            elif opt == "t":
                time_msg = arg

            elif opt == "f":
            	file_name = arg

        else:
            if arg == "-v":
                debug_out = True
            elif arg == "-e":
                correct_errors = True
            elif arg == "-d":
                opt = "d"
            elif arg == "-n":
                use_custom_namespace = True
            elif arg == "-c":
                constant_clock = True
            elif arg == "-t":
                opt = "t"
            elif arg == "-f":
                opt = "f"


    if csv_delim == "\\t":
        csv_delim = "\t"
    parser = SDLog2Parser()
    parser.setDelimiterChar(csv_delim)
    parser.setNullChar(csv_null)
    parser.setMsgFilter(msg_filter)
    parser.setTimeMsg(time_msg)
    parser.setDataMsg(data_msg)
    parser.setFileName(file_name)
    parser.setDebugOut(debug_out)
    parser.setConstantClock(constant_clock)
    parser.setCorrectErrors(correct_errors)
    if use_custom_namespace:
        parser.setNamespace(custom_namespace)
    else:
        parser.setNamespace(default_namespace)
    parser.setMsgIgnore(msg_ignore)
    parser.process(fn)
    print("Done\nParsed " + str(parser.msg_count + 1) + " lines")
    

if __name__ == "__main__":
    _main()
