@echo off
set MyBotDebug="python-26 MyBot.py -d -p"
set MyBot="python-26 MyBot.py -p"
set MyPrevBot13="python-26 previous/MyBot.13/MyBot.py"
set MyPrevBot16="python-26 previous/MyBot.16/MyBot.py"
set MyPrevBot20="python-26 previous/MyBot.20/MyBot.py"
set MyPrevBot23="python-26 previous/MyBot.23/MyBot.py"
set MyPrevBot25="python-26 previous/MyBot.25/MyBot.py"

java -jar tools/PlayGame-1.2.jar %1 5000 199 plog.txt %MyPrevBot25% %MyBot%
python-26 -c "import pstats; pstats.Stats('profile.log').strip_dirs().sort_stats('total').print_stats()"
