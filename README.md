# PxParser - software for parsing and processing PX4 flight controller log files

## Features:

- UI ***(not perfect, but gets the job done)***
- Import *.log and *.bin files generated by controller
- Export as *.txt, *.csv and *.xlsx
- Select which fields will be exported
- Rename fields (Custom English/Russian namespaces available)
- Constant message frequency
   
## What is  constant message frequency?

PX4's logs have an event driven structure i.e. messages are written as soon as some value somewhere updates. That can make analysis and some other types of work much harder.

That's why I've written a function that interpolates values in such way that there's always a 100ms delay between messages.