# PX4-Log-Parser
A PX4 log parser 

# How to use:
    python px4parser <log.bin>  [-e] [-d delimiter] [-n] [-m MSG[.field1,field2,...]] [-f file.txt]
Commands:

     -e	Recover from errors.
    
    -d  Use "delimiter" in file. Default is TAB.
    
    -n  Use custom namespace.
    
    -c  Use constant clock.
    
    -m  MSG[.field1,field2,...]
        Dump only messages of specified type, and only specified fields.
        Multiple -m options allowed.

    -f  Output file.
