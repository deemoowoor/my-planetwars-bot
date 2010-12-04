python-26 -c "import pstats; pstats.Stats('profile.log').strip_dirs().sort_stats(1).print_stats()"
python-26 -c "import pstats; pstats.Stats('profile.log').strip_dirs().sort_stats(1).print_callers()"