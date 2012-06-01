import pstats

s = pstats.Stats("server.prof")
s.strip_dirs().sort_stats("time").print_stats()
