import struct
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
    __delim_char = "\t"
    __null_char = "" 
    __msg_filter = list()
    __msg_ignore = list()
    __msg_id_ignore = list()
    __time_msg = None
    __time_msg_id = 0
    __status_msg = None
    __status_msg_id = 0
    __debug_out = False
    __correct_errors = False
    __file = None
    __namespace = dict()
    __prev_data = list()               
    __next_data = list()
    __constant_clock = False
    __msg_count = 0                   
    
    
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
        self.completed_percentage = 0
    
    def set_namespace(self, namespace):      # Set a custom namespace to print instead of __txt_columns
        self.__namespace = namespace

    def set_delimiter_char(self, csv_delim):  # Set a char to print in between columns
        self.__delim_char = csv_delim
    
    def set_null_char(self, csv_null):        # Set a char to print if there is no data in the column
        self.__null_char = csv_null
    
    def set_msg_filter(self, msg_filter):     # Set a filter of messages to output
        self.__msg_filter = msg_filter
    
    def set_time_msg(self, time_msg):         # Set time message name
        self.__time_msg = time_msg

    def set_data_msg(self, status_msg):       # Set a status message name
        self.__status_msg = status_msg
    
    def set_debug_flag(self, debug_out):       # Set a debug output flag
        self.__debug_out = debug_out

    def set_error_corr_flag(self, correct_errors): # Set an error correction flag
        self.__correct_errors = correct_errors

    def set_constant_clock_flag(self, constant_clock): # Set a constant clock flag
        self.__constant_clock = constant_clock

    def set_msg_ignore(self, msg_ignore):     # Set a list of messages to ignore during processing
        self.__msg_ignore = msg_ignore

    def set_fileanme(self, file_name):       # Set an output file's name
    	self.__file_name = file_name
    	if file_name != None:
    		self.__file = open(file_name, 'w+')
    	else:
    		self.__file = None

    def get_msg_count(self):
        return self.__msg_count

    def __parseCString(self, cstr):
        return str(cstr, 'ascii').split('\0')[0]
    
    def process(self, fn): # Main function
        self.reset()
        if self.__debug_out:
            for msg_name, show_fields in self.__msg_filter:
                self.__msg_filter_map[msg_name] = show_fields
        first_data_msg = True
        f = open(fn, "rb")
        file_size = Path(fn).stat().st_size
        bytes_read = 0
        while True:
            self.completed_percentage = (bytes_read / file_size) * 100 
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
        if not self.__msg_filter: # If filter is impty, fill it with eptyness sings
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

        headers = []
        if self.__namespace: # If __namespace is not empty (i.e use __namespace instead of __txt_columns in output)
            for column in self.__txt_columns: # Check every column
                if column in self.__namespace: # If it has a custom name, use it
                    headers.append(self.__namespace[column])
                else:
                    headers.append(column) # If there doest have a custom name, use default from __txt_columns 
        else:
            headers = self.__txt_columns # If __namesapce is empty, use default columns headers (i.e. __txt_columns)

        if self.__file != None: # Output headers
            print(self.__delim_char.join(headers), file=self.__file)
        else:
            print(self.__delim_char.join(headers))
    

    def __processData(self): # Process raw data 
        data = []

        for full_label in self.__txt_columns: # Fill in data accordigly to __txt_columns
            val = self.__txt_data[full_label]   # Get single string from data dictionary
            if not val:
                val = self.__null_char # Put null character in
            else:
                val = str(val) # If there is some data, convert it to a string
            data.append(val) # Add new string to data list

        if self.__constant_clock:
            if not self.__next_data:
                self.__next_data = data[:]
            else:
                curr_data = self.__next_data[:]
                self.__prev_data = curr_data[:] # Update __prev_data [:]
                self.__next_data = data[:] # Update __next_data
                if self.__prev_data: 
                    time_diffence = ((int(curr_data[self.__time_msg_id]) - int(self.__prev_data[self.__time_msg_id])) // 1000) 
                    to_round_time = float((100 - (time_diffence % 100)) * 0.0001) # Calculate a multiplier based on time difference for __curr_data to reach a round digit time
                    extra_msg_count = time_diffence // 100
                    for count in range(1, extra_msg_count + 1): 
                        if count == 1 and to_round_time != 1.0: # If it's first extra message and time is not a round number
                            for i in range(len(curr_data)): # Multiply every string in list by to_round_time multiplier
                                if i == self.__time_msg_id or curr_data[i] == self.__prev_data[i] or i in self.__msg_id_ignore: # If time message is being processed or curr_data at id [i] and __prev_data at id[i] is equal 
                                    continue
                                if self.__next_data[i] > curr_data[i]: # If __next_data is greater than curr_data
                                    curr_data[i] = str(float(curr_data[i]) + (float(curr_data[i]) * to_round_time)) # Convert string to float, add (curr_data at id i * to_round_time) to curr_data, convert everything back to string and put into curr_data at id i
                                else:
                                    curr_data[i] = str(float(curr_data[i]) - (float(curr_data[i]) * to_round_time)) # Convert string to float, substract (curr_data at id i * to_round_time) from curr_data, convert everything back to string and put into curr_data at id i
                            curr_data[self.__time_msg_id] = str(self.msg_count * 100) # Calculate current time by multiplier amount of messages by clock time (100 ms)
                            self.__printData(curr_data) # Print curr_data
                            self.msg_count += 1
                        tmp = curr_data[:]
                        for id in range(len(curr_data)): # Extrapolate data 
                            if id in self.__msg_id_ignore or self.__next_data[id] == curr_data[id]: # If message in ignore list or equal to __next_data
                                continue
                            elif self.__next_data[id] > curr_data[id]: # If curr_data[id] less than __next_data
                                tmp[id] = str(float(curr_data[id]) + (((float(self.__next_data[id]) - float(curr_data[id])) / extra_msg_count) * count)) # Add extrapolation
                            else:  # If curr_data[id] greater than __next_data
                                tmp[id] = str(float(curr_data[id]) - (((float(curr_data[id]) - float(self.__next_data[id])) / extra_msg_count) * count)) # Substract extrapolation
                        tmp[self.__time_msg_id] = str(self.msg_count * 100)
                        self.__printData(tmp)  # Print data              
                        self.msg_count += 1 # Add extra message
                else:
                    curr_data[self.__time_msg_id] = str(self.msg_count * 100) # Calculate current time by multiplying amount of messages by clock time (100 ms)
                    self.__printData(curr_data) # Print data
        else:
           self.__printData(data)

    def __parseMsgDescr(self): # Get message description
        # How does it work? idunno
        data = struct.unpack(self.MSG_FORMAT_STRUCT, self.__buffer[self.__pointer + 3 : self.__pointer + self.MSG_FORMAT_PACKET_LEN])
        msg_type = data[0]
        if msg_type != self.MSG_TYPE_FORMAT:
            msg_length = data[1]
            msg_name = self.__parseCString(data[2])
            msg_format = self.__parseCString(data[3])
            msg_labels = self.__parseCString(data[4]).split(",")
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
    
    def __parseMsg(self, msg_descr): # Get raw data from file
        msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults = msg_descr  #Disassemble msg_descr    
        if not self.__debug_out and self.__time_msg != None and msg_name == self.__time_msg and self.__txt_updated: 
            self.__processData()
            self.__txt_updated = False
        show_fields = self.__filterMsg(msg_name) # Get data from filter

        if (show_fields != None): # If filter is not empty
            data = list(struct.unpack(msg_struct, self.__buffer[self.__pointer+self.MSG_HEADER_LEN:self.__pointer+msg_length])) # Parse data from file to list

            for i in range(len(data)):
                if type(data[i]) is str:
                    data[i] = self.__parseCString(data[i])
                m = msg_mults[i] # Get multiplier from structure
                if m != None: # If there is a multiplier
                    data[i] = data[i] * m # Multiply

            if self.__debug_out: # If debug is enabled
                s = []
                for i in range(len(data)):
                    label = msg_labels[i]
                    if show_fields == "*" or label in show_fields:
                        s.append(label + "=" + str(data[i]))
                            
                print("MSG %s: %s" % (msg_name, ", ".join(s)))

            else: # If debug is disabled
                # update data buffer
                for i in range(len(data)): # For every column
                    label = msg_labels[i] # Get label
                    if label in show_fields: # If label is in filter
                        self.__txt_data[msg_name + "_" + label] = data[i] # Add parsed raw data to __txt_data
                        if self.__time_msg != None and msg_name != self.__time_msg:
                            self.__txt_updated = True
                if self.__time_msg == None:
                    self.__processData()


        self.__pointer += msg_length
        
    def __printData(self, data):
        for id in range(len(data)):
            if id == self.__status_msg_id:
                data[self.__status_msg_id] = data[self.__status_msg_id].strip("'").lstrip("b'").strip('\\x00')
                continue

            if len(data[id]) > 10 and id != self.__time_msg_id: # If message is longer than 10 characters
                data[id] = data[id][:8] # Trim to 8 characters
            elif len(data[id]) < 8:
                data[id] += '\t'

        if self.__file != None: # Print data
            print(self.__delim_char.join(data), file=self.__file)
        else:
            print(self.__delim_char.join(data))
        self.msg_count += 1
       