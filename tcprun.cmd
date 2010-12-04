rem !/bin/bash

set ip=72.44.46.68
set port=995
set python=C:\Python26\python-26

FOR /L %%I IN (0, 1, 19) DO tools\tcp %ip% %port% dmw29 -p 646464 %python% MyBot.py
