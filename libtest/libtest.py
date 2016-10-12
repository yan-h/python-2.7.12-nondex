import subprocess
import os
import sys
import yaml

if len(sys.argv) < 2:
    sys.exit("Usage: python libtest.py <file containing repo URLs>")
elif not os.path.isfile(sys.argv[1]):
    sys.exit("Could not find file with repo URLs")

# Locations of important files. TODO: make more configurable
repos_file = os.getcwd() + "/" + sys.argv[1] # List of URLs of Github projects
# Location of executable for nondeterministic version of Python
py_exe_nondex = "/home/yan/pynondex/python-2.7.12/bin/python"
py_exe_original = sys.executable
import_error = "ImportError: No module named "
import_error_len = len(import_error)
devnull = open(os.devnull, 'w')

# Location of this python file
test_home = os.path.dirname(os.path.abspath(__file__)) + "/"
log_home = test_home + "logs/"
main_log_file = open(log_home + "main.log", "w+")

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
        def venvify(s):
            return s.replace("python", venv_python).replace("nosetests", venv_dir + "bin/nosetests").replace("pip", venv_pip)
        def get_command(s):
            if s == None:
                return ""
            return venvify('\n'.join(s) if type(s) is list else s)

        cd(repo_dir)
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
        travis_file = repo_dir + ".travis.yml"
#if os.path.isfile(reqs_file):
#           print "> Installing requirements at %s" % (reqs_file)
#
        if not os.path.exists(log_home):
            os.makedirs(log_home)

        if os.path.isfile(travis_file):
            print "> Parsing .travis.yml"
            with open(travis_file) as stream:
                yaml_contents = yaml.load(stream)
                if 'install' in yaml_contents:
                    subprocess.call(get_command(yaml_contents['install']), shell=True, stdout=devnull, stderr=devnull)
                if 'before_script' in yaml_contents:
                    subprocess.call(get_command(yaml_contents['before_script']), shell=True, stdout=devnull, stderr=devnull)
                test_command = get_command(yaml_contents['script'])
                return test_command
        else:
            subprocess.call("%s install -r %s" % (venv_pip, reqs_file), shell=True)
            return "%sbin/nosetests" % (repo_dir)

    print "> Running tests on standard Python"
    venv_dir = repo_dir + "venv_original/"
    result = setup_tests(py_exe_original)

    if result == None:
        remove_library(url)
        return

    outfile_path_original = log_home + repo_name + "_original.log"
    with open(outfile_path_original, 'w') as f:
        subprocess.call(result, shell=True, stdout=devnull, stderr=f)

    # Remove this library if there are import errors
    with open(outfile_path_original) as f:
        for line in f:
            if line.startswith(import_error):
                remove_library(url)

    print "> Running tests on nondex Python"
    venv_dir = repo_dir + "venv_nondex/"
    result = setup_tests(py_exe_nondex)

    if result == None:
        remove_library(url)
        return
    outfile_path_nondex = log_home + repo_name + "_nondex.log"
    with open(outfile_path_nondex, 'w') as f:
        subprocess.call(result, shell=True, stdout=devnull, stderr=f)

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
