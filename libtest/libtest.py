import subprocess
import os
import sys

if len(sys.argv) < 2:
    sys.exit("Usage: python libtest.py <file containing repo URLs>")
elif not os.path.isfile(sys.argv[1]):
    sys.exit("Could not find file with repo URLs")

# Locations of important files. TODO: make more configurable
repos_file = sys.argv[1] # List of URLs of Github projects
# Location of executable for nondeterministic version of Python
py_exe_nondex = "/home/yan/pynondex/python-2.7.12/bin/python"
py_exe_original = sys.executable
import_error = "ImportError: No module named "
import_error_len = len(import_error)

# Location of this python file
test_home = os.path.dirname(os.path.abspath(__file__)) + "/"
log_home = test_home + "logs/"
main_log_file = open(log_home + "main.log", "w+")

def cd(path):
    subprocess.call("cd %s" % (path), shell=True)

def remove_library(url):
    newFile = ""
    with open(repos_file, "r") as master:
        for line in master:
            if url not in line:
                newFile += line
    with open(repos_file, "w") as master:
        master.write(newFile)

# Called on each git url to be tested
def test_repo(url):
    print "=== Testing repo at %s ===" % (url)

    repo_name = url.split('/')[-1]
    libs_dir = test_home + "libs/"
    repo_dir = libs_dir + repo_name + "/"
    cd(libs_dir);

    # Clone repo
    if os.path.isdir(repo_dir):
        print "> Skipping clone of repo since it already exists"
    else:
        print "> Cloning repo %s into %s" % (url, repo_dir)
        print subprocess.check_output("git clone %s %s" % (url, repo_dir), shell=True)

    cd(repo_dir)
    venv_dir = ""

    def setup_tests(exe_path):
        # Set up virtual environment
        if os.path.isdir(venv_dir):
            print "> Skipping virtualenv creation, already exists"
        else:
            print "> Setting up virtualenv"
            print "virtualenv -p %s %s" % (exe_path, venv_dir)
            subprocess.call("virtualenv -p %s %s" % (exe_path, venv_dir), shell=True)

        # Write .pth file for venv so that tests import the library correctly
        path_file = open(venv_dir + "lib/python2.7/site-packages/paths.pth", "w+")
        path_file.write(repo_dir)

        venv_python = venv_dir + "bin/python"
        venv_pip = venv_dir + "bin/pip"
        reqs_file = repo_dir + "requirements.txt"
        if os.path.isfile(reqs_file):
            print "> Installing requirements at %s" % (reqs_file)
            subprocess.call("%s install -r %s" % (venv_pip, reqs_file), shell=True)

        if not os.path.exists(log_home):
            os.makedirs(log_home)

        subprocess.call("%s install nose" % (venv_pip), shell=True)

    # Automatically attempt to fix import errors
    missing_modules = []
    for i in range(2):
        print "> Running tests on standard Python"

        new_missing_modules = []
        venv_dir = repo_dir + "venv_original/"
        setup_tests(py_exe_original)
        outfile_path_original = log_home + repo_name + "_original.log"

        subprocess.call("%sbin/nosetests -s -w > %s 2>&1 %s"
                                    % (venv_dir, outfile_path_original, repo_dir), shell=True)

        # Attempt to fix ImportErrors
        with open(outfile_path_original) as f:
            for line in f:
                if line.startswith(import_error):
                    if i == 1:
                        # Abort library
                        remove_library(url)
                        return
                    new_missing_modules.append(line[len(import_error):].split(".")[0])

        for module in new_missing_modules:
            print "%s install %s" % (venv_dir + "bin/pip", module)
            subprocess.call("%s install %s" % (venv_dir + "bin/pip", module), shell=True)
            '''
            SPECIAL CASES
            - psycopg2i: sudo apt-get install libpq-dev
            '''
        if len(new_missing_modules) == 0:
            break

        missing_modules += new_missing_modules

    print "> Running tests on nondex Python"
    venv_dir = repo_dir + "venv_nondex/"
    setup_tests(py_exe_nondex)
    outfile_path_nondex = log_home + repo_name + "_nondex.log"

    for module in missing_modules:
        subprocess.call("%s install %s" % (venv_dir + "bin/pip", module), shell=True)


    subprocess.call("%sbin/nosetests -s -w > %s 2>&1 %s"
         % (venv_dir, outfile_path_nondex, repo_dir), shell=True)

    data_orig = ''
    data_nondex = ''
    with open(outfile_path_original, 'r') as f:
        data_orig = f.read()
    with open(outfile_path_nondex, 'r') as f:
        data_nondex = f.read()

    if data_orig.count('\n') != data_nondex.count('\n'):
        main_log_file.write("%s\n" % repo_name)
        main_log_file.flush()

# Read git urls line by line from input file, test each of them
test_repos = open(repos_file)
for line in test_repos:
    test_repo(line.rstrip())
main_log_file.close()
