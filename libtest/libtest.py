import subprocess
import os
import sys
import yaml
import logging
import random
import datetime

# Parse arguments
if len(sys.argv) < 2:
    sys.exit("Usage: python libtest.py <file containing repo URLs>")
elif not os.path.isfile(sys.argv[1]):
    sys.exit("Could not find file with repo URLs")

# Set environment variable for nondex mode
os.environ["PYTHONNONDEXMODE"] = "f"

# Time limit for subprocess calls
timelimit = 300

# Important files and directories
repos_file = os.getcwd() + "/" + sys.argv[1] # List of URLs of Github projects
test_home = os.path.dirname(os.path.abspath(__file__)) + "/"
log_home = test_home + "logs/"
venv_original_home = test_home + "venv_original/"
venv_nondex_home = test_home + "venv_nondex/"

# Files to write output to
devnull = open(os.devnull, 'w')
main_log_file = open("%sSummary %s.log" % (log_home, datetime.datetime.now()), "w+")
main_log_file.write("URL, succeeded?, nondex errors?, number of nondex errors, description\n")


# Special environment variable copies. For running a process under a virtualenv
env_nondex =  os.environ.copy()
env_nondex["PATH"] = venv_nondex_home + "bin:" + env_nondex["PATH"]
env_nondex["PYTHONHOME"] = venv_nondex_home
env_original = os.environ.copy()
env_original["PATH"] = venv_original_home + "bin:" + env_original["PATH"]

venv_original = {"home": venv_original_home,
                 "log_suffix": "_original.log",
                 "num_trials": 1,
                 "env": env_original}

venv_nondex =   {"home": venv_nondex_home,
                 "log_suffix": "_nondex.log",
                 "num_trials": 5,
                 "env": env_nondex}
# Summary information
num_succeeded = 0
num_with_errors = 0
num_libraries = 0

def write_summary(url, succeeded, errors, description=""):
    global num_succeeded
    global num_with_errors
    global num_libraries
    main_log_file.write("%s,%s,%s,%s\n" %
        (url,
        1 if succeeded else 0,
        1 if errors else 0,
        description))
    num_succeeded += 1 if succeeded else 0
    num_with_errors += 1 if errors else 0
    num_libraries += 1

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
        print("Cloning repo %s into %s" % (url, repo_dir))
        logging.info("Cloning repo %s into %s" % (url, repo_dir))
        print(subprocess.check_output("git clone %s %s" % (url, repo_dir), shell=True))

# Called on each git url to be tested
def test_repo(url):

    repo_name = url.split('/')[-1]
    repo_dir = test_home + "libs/" + repo_name + "/"

    clone_repo(repo_dir, url)

    cd(repo_dir)

    def run_tests(info):
        def get_command(s):
            if s == None:
                return ""
            return '\n'.join(s) if type(s) is list else s

        def run_commands(yaml_contents, key):
            if key in yaml_contents and yaml_contents[key] is not None:
                for cmd in yaml_contents[key]:
                    subprocess.call(cmd, shell=True, stdout=devnull, stderr=devnull, timeout=timelimit, env = info["env"])

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
            with open(travis_file) as stream:
                yaml_contents = yaml.load(stream)
                run_commands(yaml_contents, 'before_install')
                run_commands(yaml_contents, 'install')
                run_commands(yaml_contents, 'before_script')
                test_command = get_command(yaml_contents['script'])
        # Try to parse pip requirements file
        elif os.path.isfile(reqs_file):
            logging.info("No .travis.yml found, attempting to use requirements.txt")
            subprocess.call("pip install -r %s" % (reqs_file), shell=True)
            test_command = "nosetests"
        # If none of the above worked
        else:
            logging.info("No tests found; removing library")
            remove_library(url)
            return None

        outfile_path = log_home + repo_name + info["log_suffix"]
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

    # First run on standard Python. Check for import errors and attempt a basic fix.
    logging.info("= Running tests on standard Python")
    outfile_path_original = run_tests(venv_original)

    if outfile_path_original == None: return

    missing_modules = []
    with open(outfile_path_original, 'r') as f:
        for line in f:
            if line.startswith("ImportError: No Module named"):
                missing_modules.append(line.split(' ')[-1])

    # Attempt to fix import errors, then attempt another run on standard Ptython
    if len(missing_modules) > 0:
        logging.info("Detected missing modules on standard Python; attempting basic fix and rerunning tests")
        for module in missing_modules:
            subprocess.call("pip install %s" % (module), shell=True, env = venv_original["env"])

        outfile_path_original = run_tests(venv_original)

    # Check for errors after running with standard Python
    with open(outfile_path_original, 'r') as f:
        text = f.read()
        if "FAILED" in text:
            logging.info("Original tests failed with errors; removing library");
            write_summary(url, False, False, "Regular tests failed")
            remove_library(url)
            return

    # Run on nondex Python
    logging.info("= Running tests on nondex Python")
    outfile_path_nondex = run_tests(venv_nondex)

    with open(outfile_path_nondex, 'r') as f:
        data_nondex = f.read()
        if "FAILED" in data_nondex:
            write_summary(url, True, True)
        else:
            write_summary(url, True, False)
# Set up logging
logging.basicConfig(stream=sys.stdout, format='%(asctime)s: %(message)s' ,level=logging.INFO)
logging.info("===== Initiating new test session =====")

# Set up virtual environment
if "--setup" in sys.argv[1:]:
    logging.info("=== Setting up virtualenv ===")
    subprocess.call("virtualenv -p %s %s" % (venv_original["exe"], venv_original["home"]), shell=True)
    subprocess.call("virtualenv -p %s %s" % (venv_nondex["exe"], venv_nondex["home"]), shell=True)
    subprocess.call("pip install nose", shell=True, env=venv_original["env"])
    subprocess.call("pip install tox", shell=True, env=venv_original["env"])
    subprocess.call("pip install nose", shell=True, env=venv_nondex["env"])
    subprocess.call("pip install tox", shell=True, env=venv_nondex["env"])

# Main loop
# Read git urls line by line from input file, test each of them
with open(repos_file) as test_repos:
    for line in test_repos:

        url = line.rstrip()

        logging.info("=== Testing " + url + " ===")

        try:
            test_repo(url)
        except subprocess.TimeoutExpired:
            logging.info("TimeoutExpired error while running tests; removing library")
            write_summary(url, False, False, "TimeoutExpired error")
            remove_library(url)
        except subprocess.CalledProcessError:
            logging.info("subprocess.CalledProcessError while running tests; removing library")
            write_summary(url, False, False, "CalledProcessError error")
            remove_library(url)
        except:
            logging.info("Uncategorized error; removing library")
            write_summary(url, False, False, "Uncategorized error")
            remove_library(url)

main_log_file.write("Total libraries: %s; Num succeeded: %s; Num with errors: %s\n" % (num_libraries, num_succeeded, num_with_errors))
main_log_file.close()
