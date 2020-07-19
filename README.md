# PX4 Log Parser
A PX4 Log parser with customazable namespaces and constant clock functionality.

## How to use:
    python px4parser <log.bin>  [-v] [-e] [-d delimiter] [-def] [-eng] [-rus] [-c] [-m MSG[.field1,field2,...]] [-f file.txt]
Commands:

    -v     Use plain debug output instead of TXT
     
    -e	   Recover from errors.
    
    -d     Use "delimiter" in file. Default is TAB.
    
    -def   Use default namespace.

    -eng   Use customized English namespace.

    -rus   Use customized Russian namespace.
    
    -c     Use constant clock.
    
    -m     MSG[.field1,field2,...]
            Parse only messages of specified type, and only specified fields.
            Multiple -m options allowed.

    -f     Set output file name.
