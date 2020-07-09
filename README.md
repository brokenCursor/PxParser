# PX4-Log-Parser
A PX4 log parser 

# How to use:
    python px4parser <log.bin>  [-v] [-e] [-d delimiter] [-n] [-c] [-m MSG[.field1,field2,...]] [-f file.txt]
Commands:

     -v Use plain debug output instead of TXT
     
     -e	Recover from errors.
    
     -d  Use "delimiter" in file. Default is TAB.
    
     -n  Use custom namespace.
    
     -c  Use constant clock.
    
     -m  MSG[.field1,field2,...]
        Dump only messages of specified type, and only specified fields.
        Multiple -m options allowed.

     -f  Output file.
