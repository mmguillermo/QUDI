import os
import sys
import time
from shutil import move, rmtree
import multiprocessing


# clunky solution to handling multiple jobs from the same RedCRAB folder
# by using multiprocessing. Does not allow for recovery and StopRedcrab stops all running jobs!
def redcrab_spawn():
    # changes working directory
    os.chdir("./bin")
    # calls redcrab code (slightly messy in python 3)
    with open("redcrab.py") as f:
        code = compile(f.read(), "redcrab.py", 'exec')
        exec (code, globals())

def output_pipe():
    # pipes stdout to file, named by the process id
    name = multiprocessing.current_process().name
    sys.stdout = open(os.path.join("Multilaunch", "MultilaunchLogs", "output_log_job" + str(name) + ".txt"), "w")
    redcrab_spawn()

def del_tmp():
    # deletes tmp folder if possible
    tmppath = os.path.exists(os.path.join("bin","tmp"))
    if tmppath:
        # while true loop, that tries to access the folder and remove it
        run_out = 0
        success = False
        while True:
            if run_out > 300:
                break
            try:
                os.rename(tmppath,tmppath)
            except OSError as e:
                time.sleep(0.5)
                run_out += 0.5
                continue
            else:
                rmtree(tmppath)
                break
        return success
    else:
        return True


def tmpcheck():
    # checks if the last job was sent successfully!
    # more precsely tests for the existance of a tmp folder and deletes this folder immediately
    # if possible
    checktimeout = 0
    while True:
        if os.path.exists(os.path.join("bin", "logconfig", "tmp.log")):
            time.sleep(3.0)
        else:
            if os.path.exists(os.path.join("bin", "tmp")):
                success = del_tmp()
                if success:
                    return 0
                else:
                    # stop sending further jobs
                    return -1
            else:
                time.sleep(3.0)
        if checktimeout > 1500:
            return 1

def get_user_job_id(jobfile_name):
    if "Cfg_" in str(jobfile_name) and ".txt" in str(jobfile_name):
        # check if allowed length of user job name was exceeded
        if len(str(files)) > 16:
            return False, 0
        ujid = str(files[0])[4:-4]
        return True, ujid
    else:
        return False, 0

if __name__ ==  '__main__':
    sys.path.append(os.path.join(os.getcwd(), "bin"))
    config_target_path = os.path.join(".", "Multilaunch", "MultilaunchConfigs")
    force_abort = False
    config_list = []
    process_list = []
    # searches multilaunch config folder for config files
    for root, dirs, files in os.walk(config_target_path):
        for element in files:
            print(element)
            config_list.append([os.path.join(root, element), str(element)])
    if len(config_list) == 0:
        print("No jobs in MultilaunchConfig folder")
        sys.exit(0)
    else:
        config_list.sort()
    for cfg_ind in range(len(config_list)):
        # Walks through files to copy the config file and start the job if last process was done starting properly
        file_ok, user_job_id = get_user_job_id(str(config_list[cfg_ind][1]))
        if file_ok:
            move(str(config_list[cfg_ind][0]), os.path.join("Config", "RedCRAB_config", str(config_list[cfg_ind][1])))
            process_list.append(multiprocessing.Process(target=output_pipe, name=str(user_job_id)))
            process_list[-1].start()
            print("Job " +str(cfg_ind + 1) + "/" + str(len(config_list)) + " was started successfully")
            time.sleep(5)
            # check loop for tmp folder
            tmp_exit_code = tmpcheck()
            if tmp_exit_code == -1:
                force_abort = True
                print("An error occurred while preparing for the next job.\nSending further jobs is not possible!!\n"
                      "Waiting for the running ones to complete (if any).")
                break
            elif tmp_exit_code == 0:
                pass
            elif tmp_exit_code == 1:
                # terminating might not be necessary here, but it secures, that no tmp folder will be created
                if process_list[-1].is_alive():
                    process_list[-1].terminate()
                print("An error occurred while preparing for the next job.\n"
                      "The last job was probably not accepted by the server and is therefore stopped. \n Sending"
                      "further jobs is possible however.")
        else:
            print("Job with config file " + str(config_list[cfg_ind][1]) + " was not accepted, wrong filename.")
    time.sleep(10)
    # just try to delete again, but ignore the outcome
    if not force_abort:
        del_exit_code = del_tmp()
    print("Waiting for the optimizations to finish")
    for process in process_list:
        process.join()
    time.sleep(2)
    # all optimizations finished
    print("Optimizations finished")
    if not force_abort:
        del_exit_code = del_tmp()
        if del_exit_code != 0:
            print("Delete bin/tmp folder before the next start of MultilaunchRedCRAB")
        else:
            pass
    else:
        print("Delete bin/tmp folder before the next start of MultilaunchRedCRAB")


