import subprocess
import os
import sys
import yaml
import logging
import random
import time
import datetime
import copy

nondex_source_home = "/path/to/source/code/of/nondex/Python"
failure_string = "!!!failure detected during tests!!!"

# Parse arguments
if len(sys.argv) < 2:
    sys.exit("Usage: python libtest.py <file containing repo URLs> --setup <directory of source of nondex Python>")
elif not os.path.isfile(sys.argv[1]):
    sys.exit("Could not find file with repo URLs")

# Set environment variable for nondex mode
os.environ["PYTHONNONDEXMODE"] = "o"
os.environ["TOX_ENV"] = "py27"

# Time limit for subprocess calls
timelimit = 180

# Important files and directories
repos_file = os.getcwd() + "/" + sys.argv[1] # List of URLs of Github projects

# The directory this file is located is the base directory for storing test results, etc
test_home = os.path.dirname(os.path.abspath(__file__)) + "/"

log_home = test_home + "logs/" + datetime.datetime.now().strftime("%d-%b-%Y-%H:%M:%S") + "/" # Directory to store logs
venv_original_home = test_home + "venv_original/" # Directory of virtual environment copy of original Python
venv_nondex_home = test_home + "venv_nondex/" # Directory of virtual environment copy of nondex Python

if not os.path.exists(log_home):
    os.makedirs(log_home)

# Files to write output to
devnull = open(os.devnull, 'w')
main_log_file = open(log_home + "summary.log", "w+")
main_log_file.write("URL, setup, original errors?, nondex OFF errors?, nondex ONE errors?, nondex FULL errors?, time, description\n")
main_log_file.write("setup key: t=travis file, r=requirements file, f=failed\n")
main_log_file.write("tests key: p=passed, f=test failures, e=test errors, u=nonzero exit code, but unknown reason\n")

# Nondex modes. x = OFF, o = ONE, f = FULL
nondex_modes = ["x", "o", "f"]

# Special environment variable copies. For running a process under a virtualenv
env_nondex =  os.environ.copy()
env_nondex["PATH"] = venv_nondex_home + "bin:" + env_nondex["PATH"]
env_original = os.environ.copy()
env_original["PATH"] = venv_original_home + "bin:" + env_original["PATH"]

# Information on the original Python virtual environment to pass to functions that need it
venv_original = {"home": venv_original_home,
                 "num_trials": 1,
                 "env": env_original,
                 "mode": "original"}
# Equivalent of venv_original for nondex Python
venv_nondex =   {"home": venv_nondex_home,
                 "num_trials": 3,
                 "env": env_nondex,
                 "mode": "nondex"}

# Data structure containing test run info to output to the summary log file
summary_data = {"url":None,
                "setup":"?",
                "original":"?",
                "nondex_x":"?",
                "nondex_o":"?",
                "nondex_f":"?",
                "error":"",
                "time":-1}

# Writes a dictionary representing library test information to the summary log file
def write_summary(summary):
    main_log_file.write("%s,%s,%s,%s,%s,%s,%d,%s\n" %
        (url,
         summary["setup"],
         summary["original"],
         summary["nondex_x"],
         summary["nondex_o"],
         summary["nondex_f"],
         summary["time"],
         summary["error"]))
    main_log_file.flush()

def cd(path):
    os.chdir(path)

def remove_library(url):
    newFile = ""
    with open(repos_file, "r") as master:
        for line in master:
            if url not in line:
                newFile += line
    with open(repos_file, "w") as master:
        master.write(newFile)

def clone_repo(repo_dir, url):
    if not os.path.isdir(repo_dir):
        logging.info("Cloning repo %s into %s" % (url, repo_dir))
        logging.info("Cloning repo %s into %s" % (url, repo_dir))
        logging.info(subprocess.check_output("timeout 180 git clone %s %s" % (url, repo_dir), shell=True, timeout=timelimit))
    else:
        logging.info("Updating repo %s in %s" % (url, repo_dir))
        logging.info(subprocess.check_output("timeout 180 git -C %s pull" % (repo_dir), shell=True, timeout=timelimit))

def get_command(s):
    if s == None:
        return ""
    return '\n'.join(s) if type(s) is list else s

def run_commands(yaml_contents, key, environment):
    if key in yaml_contents and yaml_contents[key] is not None:
        subprocess.call(get_command(yaml_contents[key]), shell=True, timeout=timelimit, env = environment)

def setup_venv(url, summary, info):
    repo_name = url.split('/')[-1]
    repo_dir = test_home + "libs/" + repo_name + "/"

    cd(repo_dir)

    # Write .pth file for venv so that tests import the library correctly
    path_file = open(info["home"] + "lib/python2.7/site-packages/paths.pth", "w+")
    path_file.write(repo_dir)

    reqs_file = repo_dir + "requirements.txt"
    travis_file = repo_dir + ".travis.yml"

    if not os.path.exists(log_home):
        os.makedirs(log_home)

    test_command = "";

    # Try to parse travis file
    if os.path.isfile(travis_file):
        logging.info("Parsing .travis.yml")
        summary["setup"] = "t"
        with open(travis_file) as stream:
            yaml_contents = yaml.load(stream)
            run_commands(yaml_contents, 'before_install', info['env'])
            run_commands(yaml_contents, 'install', info['env'])
            run_commands(yaml_contents, 'before_script', info['env'])
            test_command = get_command(yaml_contents['script'])

    # Try to parse pip requirements file
    elif os.path.isfile(reqs_file):
        summary["setup"] = "r"
        logging.info("No .travis.yml found, attempting to use requirements.txt")
        subprocess.call("pip install -r %s" % (reqs_file), shell=True)
        test_command = "nosetests"

    # If none of the above worked
    else:
        summary["setup"] = "f"
        logging.info("No tests found")
        return None

    outfile_path = log_home + repo_name + "/"

    if not os.path.exists(outfile_path):
        os.makedirs(outfile_path)

    return test_command

def run_tests(url, summary, info, test_command, nondex_mode = None):
    repo_name = url.split('/')[-1]
    repo_dir = test_home + "libs/" + repo_name + "/"

    cd(repo_dir)

    outfile_path = log_home + repo_name + "/" + info["mode"] + ("" if nondex_mode == None else "_" + nondex_mode) + ".log"
    open(outfile_path, 'w').close() # Clear output file
    logging.info("Running test command: " + test_command)

    # Run multiple trials
    f = open(outfile_path, 'a')

    for trial_num in range(1) if nondex_mode == 'x' else range(info["num_trials"]):
        new_env = info["env"].copy()

        if nondex_mode == None:
            log_string = "Original Python: test %d" % (trial_num + 1)
            f.write("=== " + log_string + " ===\n\n")
            logging.info(log_string)
        else:
            seed = random.randint(0, 424242)
            new_env["PYTHONNONDEXSEED"] = str(seed)
            new_env["PYTHONNONDEXMODE"] = nondex_mode
            log_string = "Mode %s: test %d with seed %d" % (nondex_mode, trial_num + 1, seed)
            f.write("=== " + log_string + " ===\n\n")
            logging.info(log_string)

        f.flush()
        try:
            code = subprocess.call(test_command, shell=True, stdout=f, stderr=f, timeout=timelimit, env=new_env)
            if code != 0:
                f.write(failure_string + "\n")
        except subprocess.CalledProcessError as e:
            logging.info("Error running test command. Continuing.\n")

        f.write('\n')
        f.flush()
    f.close()

    return outfile_path

def check_status(f, summary, mode):
    text = f.read().lower()
    if failure_string.lower() in text:
        # use some searching that ignores case
        if "failed" in text:
            summary[mode] = "f"
        elif "error" in text:
            summary[mode] = "e"
        else:
            summary[mode] = "u"
    else:
        summary[mode] = "p"

# Called on each git url to be tested
def test_repo(url, summary):

    repo_name = url.split('/')[-1]
    repo_dir = test_home + "libs/" + repo_name + "/"

    try:
        clone_repo(repo_dir, url)
    except Exception as e:
        pass

    cd(repo_dir)

    start_time = time.time()

    # Run on standard Python
    logging.info("= Running tests on standard Python")
    test_command = setup_venv(url, summary, venv_original)
    if test_command == None: return
    outfile_path_original = run_tests(url, summary, venv_original, test_command)
    if outfile_path_original == None: return
    check_status(open(outfile_path_original, 'r'), summary, "original")

    # Run on nondex Python
    logging.info("= Running tests on nondex Python")
    test_command = setup_venv(url, summary, venv_nondex)
    if test_command == None: return
    for nondex_mode in nondex_modes:
        outfile_path_nondex = run_tests(url, summary, venv_nondex, test_command, nondex_mode)
        check_status(open(outfile_path_nondex, 'r'), summary, "nondex_" + nondex_mode)

    end_time = time.time()
    summary["time"] = end_time - start_time

# Set up logging
logging.basicConfig(stream=sys.stdout, format='%(asctime)s: %(message)s' ,level=logging.INFO)
logging.info("===== Initiating new test session =====")


# Set up virtual environment for original and nondex Python
def setup_venv_original():
    subprocess.call("virtualenv -p %s %s" % ("python2.7", venv_original["home"]), shell=True)
    subprocess.call("pip install nose", shell=True, env=venv_original["env"])
    subprocess.call("pip install tox", shell=True, env=venv_original["env"])
    subprocess.call("pip install pytest-cov", shell=True, env=venv_original["env"])
    subprocess.call("pip install numpy", shell=True, env=venv_original["env"])

def setup_venv_nondex():
    subprocess.call("virtualenv -p %s %s" % (nondex_source_home + "bin/python", venv_nondex["home"]), shell=True)
    subprocess.call(venv_nondex["home"] + "bin/pip install nose", shell=True)
    subprocess.call(venv_nondex["home"] + "bin/pip install tox", shell=True)
    subprocess.call(venv_nondex["home"] + "bin/pip install pytest-cov", shell=True)
    subprocess.call(venv_nondex["home"] + "bin/pip install numpy", shell=True)

if "--setup" in sys.argv[1:]:
    nondex_source_home = sys.argv[sys.argv.index("--setup") + 1]
    print(nondex_source_home)
    setup_venv_original()
    setup_venv_nondex()

if not os.path.exists(venv_original_home):
    setup_venv_original()

if not os.path.exists(venv_nondex_home):
    setup_venv_nondex()

# Main loop
# Read git urls line by line from input file, test each of them
with open(repos_file) as test_repos:
    for line in test_repos:

        url = line.rstrip()

        logging.info("=== Testing " + url + " ===")

        summary = copy.deepcopy(summary_data)
        summary["url"] = url

        try:
            test_repo(url, summary)
        except Exception as e:
            error_msg = str(e)
            logging.info("Uncategorized error: " + error_msg)
            summary["error"] = error_msg

        write_summary(summary)

main_log_file.close()
