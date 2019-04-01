# coding: utf8
import ast
import os
#MarcoR 09.05.2018

def readconfigfile(ConfigFileName_inclPath):
    global log_id
    # Reads in all configurations/ parameters/ ... from text file in ./userInputs
    #if DebugMode == 1:
    #    print('--- READING configuration data of RedCrab config file at: ' + NewPathFilename + ' ---')

    # #open config file with number ConfigFileNum
    # ConfigFileName = 'CfgNo' + str(ConfigFileNum) + '.txt'
    # ConfigFileName_inclPath = 'not_found'
    # for root, dirs, files in os.walk("./userInputs"):
    #     for file in files:
    #         if file == ConfigFileName:
    #             ConfigFileName_inclPath = os.path.join(root, file)
    #             print('Opening File ' + ConfigFileName_inclPath)

    #ConfigFileName_inclPath = NewPathFilename
    #
    #config_name = ""
    # Reads from prebuilt file
    pulsenr = -1 #counts the number of pulses and is important for ordering the results
    paranr = -1 #counts the (current) number of parameter and is important for ordering the results
    vartype = -1 #0 = flags, 1 = mandatory/optional variables, 2 = flagged variables, 3 = algorithmic variables
    splitstring = ":=" #by which string should the lines that are read be split

    mainpars = {}  # mandatory and optional variables for the main program
    algpars = {} #contains algorithmic parameters. Could also be shifted in mainpars if needed
    mainflags = [] #flags for the main program
    mainflagged = {} #flagged variables for the main program
    pulsepars = []  # mandatory and optional parameters for the pulses
    pulseflagged = []  #flagged parameters for the pulses
    pulseflags = []  # flags for the pulses
    parapars = [] # parameters for the parameter ;)
    paraflagged = [] # flagged parameters for the parameter
    paraflags = [] # flags for the parameters
    d = {} #dummy dictionary
    returnValue = 0 #correctness checker

    if ConfigFileName_inclPath == 'not_found':
        #print('WARNING: COULD NOT FIND CONFIG FILE NUMBER ' + str(ConfigFileNum))
        returnValue += 1
        return (-1,-1,-1,-1,-1,returnValue)
    else:
        with open(ConfigFileName_inclPath) as f:
            for line in f:
                if line[0] == '#':
                    continue
                #Blocks that check for keywords in the file, ENDPHYSPARS; ENDFLAGS ; ENDALGPARS ; ENDFLAGGED ; ENDPULSE
                # And write in the corresponding dictionary/list the data that has been read out
                if "ENDPHYSPARS" in str(line):
                    if pulsenr == -1: #checks if parameters are for the main program
                            mainpars = d
                    elif pulsenr >= 0: #checks if these parameters are for the pulses
                            if paranr == -1: # still in pulse region
                                pulsepars.append(d)
                            else: # we are in the parameter blocks
                                parapars.append(d)
                    vartype = -1
                    d = {} #reset dummy
                if "ENDALGPARS" in str(line):
                    vartype = -1
                    # to include them in mainpars uncomment
                    #mainpars.update(d)
                    # and comment the next line
                    algpars = d
                    d = {} #reset dummy
                if "ENDFLAGS" in str(line):
                    vartype = -1
                if "ENDFLAGGED" in str(line):
                    if pulsenr == -1:  # checks if parameters are for the main program
                        for flag in mainflags:  # identifies flags valued 1 and fills mainflagged accordingly
                            if flag[1] == 1:
                                mainflagged[flag[0]] = (1, d)
                                mainflags.remove(flag)
                                break
                    elif pulsenr >= 0:  # checks if these parameters are for the pulses
                        if paranr == -1:
                            for flag in pulseflags[pulsenr]:  # identifies flags valued 1 values and fills pulseflagged accordingly
                                if flag[1] == 1:
                                    pulseflagged[pulsenr][flag[0]] = (1, d)  # pulsenr is important here to keep flags
                                                                             # for different pulses seperated
                                    pulseflags[pulsenr].remove(flag)
                                    break
                        elif paranr >= 0:
                            for flag in paraflags[paranr]:
                                if flag[1] == 1:
                                    paraflagged[paranr][flag[0]] = (1, d)

                                    paraflags[paranr].remove(flag)
                                    break

                    vartype = -1
                    d = {} #reset dummy

                if "ENDPULSE" in str(line):
                    vartype = -1
                    if len(pulseflags[pulsenr]) != 0: #checks for flags that have been set 0
                                                      # and therefore have not yet been appended to pulseflagged list
                        for flag in pulseflags[pulsenr]:
                            pulseflagged[pulsenr][flag[0]] = (0, {}) # takes the flags that have not been selected and
                                                                         # adds copys of them to pulseflagged
                if "ENDPARAMETER" in str(line):
                    vartype = -1
                    if len(paraflags[paranr]) != 0: #checks for flags that have been set 0
                            # and therefore have not yet been appended to paraflagged list
                        for flag in paraflags[paranr]:
                            paraflagged[paranr][flag[0]] = (0, {}) # takes the flags that have not been selected and
                                                    # adds copys of them to paraflagged


            #Blocks that check vartype and either write data in d, if vartype is 1,2 or 3 or
            #flags in the corresponding flag dictionary/list if vartype is 0
                if vartype == 1 or vartype == 2 or vartype == 3 :
                    #Splits the string in the line at <splitstring>
                    # and determines the variable type for the input
                    try:
                        (key, val) = line.split(splitstring)
                        x = ast.literal_eval(val.strip()) #should get most types but is sensitive to empty spaces,
                                                          # if it cannot guess the variables correctly
                                                          #the next 3 try statements are failsaves
                        d[str(key).strip()] = x
                    except ValueError:
                        try:
                            (key, val) = line.split(splitstring)
                            d[str(key).strip()] = int(val)
                        except ValueError:
                            try:
                                (key, val) = line.split(splitstring)
                                d[str(key).strip()] = float(val)
                            except ValueError:
                                try:
                                    (key, val) = line.split(splitstring)
                                    d[str(key).strip()] = str(val).rstrip()
                                except ValueError:
                                    returnValue += 1
                                    log_id.error("ERROR: A value could not be read due to "
                                          "type mismatch")
                elif vartype == 0:
                    #Splits the string in the line at <splitstring>
                    #and determines if the flags are for the main flagged variables ore the pulse specific ones
                    (key, val) = line.split(splitstring)
                    if pulsenr == -1:
                        mainflags.append((key.strip(),int(val)))
                    else:
                        if paranr==-1: # still in pulse block region
                            pulseflags[pulsenr].append((key.strip(),int(val)))
                        elif paranr>=0:
                            paraflags[paranr].append((key.strip(),int(val)))
            #Blocks that check for keywords in the file, STARTPHYSPARS; STARTFLAGS ; STARTALGPARS ; STARTFLAGGED ; STARTPULSE
            # And prepares for a new Block in the file
                if "STARTPULSE" in str(line):
                    #Determines if a new pulse block started
                    pulsenr +=1
                    pulseflagged.append({}) #for each new pulse a new empty dictionary will be appended
                                            # in the existing pulseflagged list to prepare it for a new pulse
                    pulseflags.append([]) #for each new pulse a new empty list will be appended
                                          #again to prepare for a new pulse

                    if len(mainflags) != 0: #checks for flags that have been set 0 and therefore have not yet
                                            # been added to mainflagged and adds copys of them them to pulseflagged
                        for flag in mainflags:
                            mainflagged[flag[0]] = (0, {})
                if "STARTPARAMETER" in str(line):
                    # Determines if a new parameter block started
                    paranr +=1
                    paraflagged.append({}) #for each new parameter a new empty dictionary will be
                        # appended in the existing paraflagged list to prepare it for a new pulse
                    paraflags.append([]) #for each new parameter a new empty list will be appended

                if "STARTFLAGS" in str(line):
                    vartype = 0  #sets the flag for a new block of flags
                if "STARTPHYSPARS" in str(line):
                    vartype = 1  #sets the flag for a new block of variables
                if "STARTFLAGGED" in str(line):
                    vartype = 2  #sets the flag for a new block of variables
                if "STARTALGPARS" in str(line):
                    vartype = 3  #sets the flag for a new block of variables

        numpulses = pulsenr+1
        #The following block checks if pulseflags and mainflags have been read out entirely. If this was not the case it might
        # be because one or more flags have been set incorrectly
        for flag in mainflags:
            if flag[1] == 1:
                returnValue += 1
                log_id.error("ERROR: InputError: One or more flags for the flagged "
                      "variables corresponding to the main program might have been set "
                      "incorrectly.")

        for ii in range(len(pulseflags)):
            for flag in pulseflags[ii]:
                if flag[1] == 1:
                    returnValue += 1
                    log_id.error("ERROR: InputError: One or more flags for the flagged "
                          "variables corresponing to " \
                          "pulse " + str(ii) + " might have been set "
                                               "incorrectly")


        return (mainpars,algpars,mainflagged,pulsepars,pulseflagged,parapars,paraflagged,
                returnValue)

        #Ways to read the mainpars pulsepars and algpars:
        #function call optmize((<List of other variables that shall not be unpacked yet as keywords!>),**mainpars)
        #unpacks the mainpars dictionary to the variables in the function as keywords.
        #e.g function optimize(a,b,c,d = 4,**kwargs)
        #the dictionary mainpars should therefore contain a,b,c as elements and while unpacking
        # it will give these parameters their respective values
        #if it contains d as well the default value for d will be overwritten
        #if it contains more than a,b,c,d the rest will be saved (packed) in kwargs as a dictionary e.g. {"e" : 4,"f" : [1,2,3.4]}
        #To read pulseflagged
        #Each element of the list is a new pulse pulseflagged[a] will acces the a+1th pulseflags
        #the values ar estored sorted by keys and then a tupel, with the key value and the parameters
        #if pulseflagged[0]["KEY1"][0] == 1
        #for example checks if the key "KEY1" for the first pulsehas been set 1
        #mainflagged is basically the same, save for having to access a specific pulse
        # if mainflagged["KEY1"][0] == 1
"""

    def _readclientconfig():
"""
"""
                Reads config file in the Client_config folder

                Parameters
                ----------

                Returns
                -------
                exit_code : int
                    internal exit code. From this method: 0 (All okay) -4 (Error)
                clientdict : dict
                    dictionary containing the parameters in the config file
"""
"""
        global log_id
        try:
            # seperates at " := " and saves elements in dictionary
            clientdict = {}
            # MarcoR 07.05.2018
            config_name = "chopped.txt"
            with open(os.path.join(os.getcwd(), "..", "Config", "Client_config", config_name), "r") as configfile:
                configlines = configfile.readlines()
            basicswitch = False
            pathswitch = False
            for line in configlines:
                if "###" in str(line).strip():
                    continue
                if "Specific" in str(line).strip() and basicswitch:
                    basicswitch = False
                    pathswitch = True
                    continue
                if basicswitch:
                    dummy = [jj for jj in str(line).strip().split(" := ")]
                    try:
                        if "ServerCheckInterval" in str(dummy[0]):
                            clientdict[str(dummy[0])] = float(dummy[1])
                        elif "UserCheckInterval" in str(dummy[0]):
                            clientdict[str(dummy[0])] = float(dummy[1])
                        elif "LowerThresholdStd" in str(dummy[0]):
                            clientdict[str(dummy[0])] = float(dummy[1])
                        else:
                            clientdict[str(dummy[0])] = int(dummy[1])
                    except (TypeError, ValueError):
                        clientdict[str(dummy[0])] = str(dummy[1])
                if pathswitch:
                    dummy = [kk for kk in str(line).strip().split(" := ")]
                    clientdict[str(dummy[0])] = str(dummy[1])
                if "Basic" in str(line).strip():
                    basicswitch = True
            return 0, clientdict
        except OSError as err:
            io.log(log_id, 'f', 'e', "_readclientconfig : OSError, errno: " + str(err.errno) +
                   ", while reading client config file, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Error while trying to read client config file in: " +
                   str(os.path.join("Config", "Client_config")) + ". Make sure, that it exists.")
            return -4, {}
        # MarcoR 07.05.2018
        except IndexError:
            io.log(log_id, 'f', 'e', "_readclientconfig : IndexError while reading client config file, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Error while reading client config file: " +
                   str(os.path.join("Config", "Client_config", config_name)) +
                   ". Check if all keys have values")
            return -4, {}
"""

