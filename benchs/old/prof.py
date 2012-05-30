import pstats

s = pstats.Stats("Profile.prof")
s.strip_dirs().sort_stats("time").print_stats()
