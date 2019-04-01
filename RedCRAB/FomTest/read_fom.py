import os

pathfile = "fom.txt"
if (os.path.isfile(pathfile)) :
    try:
        with open(pathfile, "r") as file:
            list_number = file.readline().strip().split()
            if len(list_number) == 1:
                number = float(list_number[0] )
                print(str(number))
    except Exception as ex:
        print(ex.__traceback__)
        print(ex.args)