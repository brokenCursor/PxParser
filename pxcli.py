import sys
from PxParser import PxParser 




def _main():
    if len(sys.argv) < 2:
        print("Usage: python px4parser.py <log.bin> [-v] [-e] [-d delimiter] [-def] [-eng] [-rus] [-c] [-m MSG[.field1,field2,...]] [-t TIME_MSG_NAME]\n")
        print("\t-v\tUse plain debug output instead of TXT.\n")
        print("\t-e\tRecover from errors.\n")
        print("\t-d\tUse \"delimiter\" in output. Default is TAB.\n")
        print("\t-def\tUse default namespace.\n")
        print("\t-eng\tUse customized English namespace.\n")
        print("\t-rus\tUse customized Russian namespace.\n")
        print("\t-c\tUse constant clock.\n")
        print("\t-m MSG[.field1,field2,...]\n\t\tDump only messages of specified type, and only specified fields.\n\t\tMultiple -m options allowed.\n")
        print("\t-t\tSpecify TIME message name to group data messages by time\n")
        print("\t-f\tPrint to file instead of stdout")
        return
    fn = sys.argv[1]

    ### Settings ###
    debug_out = False
    correct_errors = False
    file_name = None
    constant_clock = True
    custom_namespace = None
    null_char = ""
    time_msg = "GPS_TimeUS"
    data_msg = "MSG_Message"
    msg_ignore = [time_msg, data_msg]
    msg_filter = [('GPS', ['TimeUS', 'Lng', 'Lat', 'Spd']), ('BARO', ['Alt']), ('AHR2', ['Roll', 'Pitch', 'Yaw']), ('MSG', ['Message'])]
    default_namespace = {'GPS_TimeUS':'GPS_TimeUS', 'GPS_Lng':'GPS_Lng', 'GPS_Lat':'GPS_Lat', 'GPS_Spd':'GPS_Spd', 'BARO_Alt':'BARO_Alt', 'AHR2_Roll':'AHR2_Roll', 'AHR2_Pitch':'AHR2_Pitch', 'AHR2_Yaw':'AHR2_Yaw','MSG_Message':'MSG_Message'}
    custom_rus_namespace = {'GPS_TimeUS':'Время', 'GPS_Lng':'Долгота', 'GPS_Lat':'Широта', 'GPS_Spd':'Скорость', 'BARO_Alt':'Высота', 'AHR2_Roll':'Крен', 'AHR2_Pitch':'Тангаж', 'AHR2_Yaw':'Рысканье','MSG_Message':'Статус'}
    custom_eng_namespace = {'GPS_TimeUS':'Time', 'GPS_Lng':'Longitude', 'GPS_Lat':'Latitude', 'GPS_Spd':'Speed', 'BARO_Alt':'Altitude', 'AHR2_Roll':'Roll', 'AHR2_Pitch':'Pitch', 'AHR2_Yaw':'Yaw','MSG_Message':'Status'}

    opt = None
    for arg in sys.argv[2:]:
        if opt != None:
            if opt == "d":
                delim_char = arg
            elif opt == "t":
                time_msg = arg
            elif opt == "n":
                custom_namespace = arg 
            elif opt == "f":
            	file_name = arg
        else:
            if arg == "-v":
                debug_out = True
            elif arg == "-e":
                correct_errors = True
            elif arg == "-d":
                opt = "d"
            elif arg == "-def":
                custom_namespace = "def"
            elif arg == "-eng":
                custom_namespace = "eng"
            elif arg == "-rus":
                custom_namespace = "rus"
            elif arg == "-c":
                constant_clock = True
            elif arg == "-t":
                opt = "t"
            elif arg == "-f":
                opt = "f"


    parser = PxParser()
    parser.set_null_char(null_char)
    parser.set_msg_filter(msg_filter)
    parser.set_time_msg(time_msg)
    parser.set_data_msg(data_msg)
    parser.set_output_file('test', 'csv')
    parser.set_debug_flag(False)
    parser.set_constant_clock_flag(constant_clock)
    parser.set_error_corr_flag(correct_errors)
    if custom_namespace == "def":
        parser.set_namespace(default_namespace)
    elif custom_namespace == "rus":
        parser.set_namespace(custom_rus_namespace)
    elif custom_namespace == "eng":
        parser.set_namespace(custom_eng_namespace)
    parser.set_msg_ignore(msg_ignore)
    parser.process(fn)
    

if __name__ == "__main__":
    _main()
