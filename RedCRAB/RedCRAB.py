# encoding: utf-8
import os, sys
# shortcut for redcrab.py module in /bin

# adds the bin path to the search path for modules
sys.path.append(os.path.join(os.getcwd(), "bin"))
# changes working directory
os.chdir("./bin")

# # adds the bin path to the search path for modules
# sys.path.append(os.path.join(os.getcwd(), "RedCRAB/bin"))
# # changes working directory
# os.chdir("./RedCRAB/bin")

# calls redcrab code (slightly messy in python 3)
with open("redcrab.py", encoding="utf-8") as f:
    code = compile(f.read(), "redcrab.py", 'exec')
    exec(code, globals())
