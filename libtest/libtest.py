import subprocess
import os
import sys
import yaml
import logging
import random
import datetime
import copy

nondex_source_home = "/home/yan/pynondex/python-2.7.12/"

# Parse arguments
if len(sys.argv) < 2:
    sys.exit("Usage: python libtest.py <file containing repo URLs>")
elif not os.path.isfile(sys.argv[1]):
    sys.exit("Could not find file with repo URLs")

# Set environment variable for nondex mode
os.environ["PYTHONNONDEXMODE"] = "o"

# Time limit for subprocess calls
timelimit = 180

# Important files and directories
repos_file = os.getcwd() + "/" + sys.argv[1] # List of URLs of Github projects
test_home = os.path.dirname(os.path.abspath(__file__)) + "/"
log_home = test_home + "logs/" + datetime.datetime.now().strftime("%d-%b-%Y-%H:%M:%S") + "/"
venv_original_home = test_home + "venv_original/"
venv_nondex_home = test_home + "venv_nondex/"

if not os.path.exists(log_home):
    os.makedirs(log_home)

# Files to write output to
devnull = open(os.devnull, 'w')
main_log_file = open(log_home + "summary.log", "w+")
main_log_file.write("Mode: " + os.environ["PYTHONNONDEXMODE"] + "\n")
main_log_file.write("URL, setup, original errors?, nondex errors?, description\n")


# Special environment variable copies. For running a process under a virtualenv
env_nondex =  os.environ.copy()
env_nondex["PATH"] = venv_nondex_home + "bin:" + env_nondex["PATH"]
env_nondex["PYTHONHOME"] = venv_nondex_home
env_original = os.environ.copy()
env_original["PATH"] = venv_original_home + "bin:" + env_original["PATH"]

venv_original = {"home": venv_original_home,
                 "log_name": "original.log",
                 "num_trials": 1,
                 "env": env_original}

venv_nondex =   {"home": venv_nondex_home,
                 "log_name": "nondex.log",
                 "num_trials": 3,
                 "env": env_nondex}

summary_data = {"url":None,
                "setup":"?",
                "original":"?",
                "nondex":"?",
                "error":""}

def bool_str(bool):
    return "1" if bool else "0"

def write_summary(summary):
    main_log_file.write("%s,%s,%s,%s,%s\n" %
        (url,
         summary["setup"],
         summary["original"],
         summary["nondex"],
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
        logging.info(subprocess.check_output("git clone %s %s" % (url, repo_dir), shell=True))
    else:
        logging.info("Updating repo %s in %s" % (url, repo_dir))
        logging.info(subprocess.check_output("git -C %s pull" % (repo_dir), shell=True))

def get_command(s):
    if s == None:
        return ""
    return '\n'.join(s) if type(s) is list else s

def run_commands(yaml_contents, key, environment):
    if key in yaml_contents and yaml_contents[key] is not None:
        for cmd in yaml_contents[key]:
            subprocess.call(cmd, shell=True, stdout=devnull, stderr=devnull, timeout=timelimit, env = environment)

def run_tests(url, summary, repo_name, repo_dir, info):
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

    outfile_path += info["log_name"]
    open(outfile_path, 'w').close() # Clear output file
    logging.info("Running test command: "+test_command)

    # Run multiple trials
    for trial_num in range(info["num_trials"]):
        with open(outfile_path, 'a') as f:
            seed = random.randint(0, 424242)
            new_env = info["env"].copy()
            new_env["PYTHONNONDEXSEED"] = str(seed)
            f.write("=== Test %d with seed %d ===\n\n" % (trial_num + 1, seed))
            logging.info("Test %d with seed %d" % (trial_num + 1, seed))
            f.flush()
            try:
                subprocess.call(test_command, shell=True, stdout=f, stderr=f, timeout=timelimit, env=new_env)
            except subprocess.CalledProcessError as e:
                logging.info("Error running test command. Continuing.")
            f.write('\n')
            f.flush()

    return outfile_path

# Called on each git url to be tested
def test_repo(url, summary):

    repo_name = url.split('/')[-1]
    repo_dir = test_home + "libs/" + repo_name + "/"

    clone_repo(repo_dir, url)

    cd(repo_dir)

    # Run on standard Python
    logging.info("= Running tests on standard Python")
    outfile_path_original = run_tests(url, summary, repo_name, repo_dir, venv_original)

    if outfile_path_original == None: return

    # Check for errors after running with standard Python
    with open(outfile_path_original, 'r') as f:
        text = f.read()
        if "FAILED" in text:
            summary["original"] = "f"
        elif "error" in text:
            summary["original"] = "e"
        else:
            summary["original"] = "p"

    # Run on nondex Python
    logging.info("= Running tests on nondex Python")
    outfile_path_nondex = run_tests(url, summary, repo_name, repo_dir, venv_nondex)

    with open(outfile_path_nondex, 'r') as f:
        text = f.read()
        if "FAILED" in text:
            summary["nondex"] = "f"
        elif "error" in text:
            summary["nondex"] = "e"
        else:
            summary["nondex"] = "p"

# Set up logging
logging.basicConfig(stream=sys.stdout, format='%(asctime)s: %(message)s' ,level=logging.INFO)
logging.info("===== Initiating new test session =====")

# Set up virtual environment
if "--setup" in sys.argv[1:]:
    logging.info("=== Setting up virtualenv ===")
    subprocess.call("virtualenv -p %s %s" % ("python2.7", venv_original["home"]), shell=True)
    subprocess.call("virtualenv -p %s %s" % (nondex_source_home + "bin/python", venv_nondex["home"]), shell=True)
    subprocess.call("pip install nose", shell=True, env=venv_original["env"])
    subprocess.call("pip install tox", shell=True, env=venv_original["env"])
    subprocess.call(nondex_source_home + "bin/pip install nose", shell=True)
    subprocess.call(nondex_source_home + "bin/pip install tox", shell=True)

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
