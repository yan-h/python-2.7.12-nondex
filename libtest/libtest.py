import subprocess
import os
import sys

# Locations of important files. TODO: make more configurable
TEST_REPOS = "testrepos.txt" # List of URLs of Github projects
PY_EXE = "/home/yan/pynondex/python-2.7.12/bin/python"

# Location of this python file
HOME = os.path.dirname(os.path.abspath(__file__)) + "/"

def cd(path):
    subprocess.call("cd %s" % (path), shell=True)

# Called on each git url to be tested
def test_repo(url):
    print ">> Testing repo at %s" % (url)

    cd(HOME)
    repo_name = url.split('/')[-1]
    repo_dir = HOME + repo_name + "/"
    print repo_dir

    # Clone repo
    print "> Cloning repo %s into %s" % (url, repo_dir)
    if os.path.isdir(repo_dir):
        print "Directory already exists, skipping clone"
    else:
        print subprocess.check_output("git clone %s" % (url), shell=True)

    cd(repo_dir)

    # Set up virtual environment
    venv_dir = repo_dir + "venv/"
    print "> Setting up virtualenv at %s" % (venv_dir)
    if os.path.isdir(venv_dir):
        print "%s already exists, skipping venv" % (venv_dir)
    else:
        print subprocess.check_output("virtualenv -p %s %s" % (PY_EXE, venv_dir), shell=True)

    # Write .pth file for venv so that tests import the library correctly
    path_file = open(repo_dir + "venv/lib/python2.7/site-packages/paths.pth", "w+")
    path_file.write(repo_dir)

    venv_python = venv_dir + "bin/python"
    venv_pip = venv_dir + "bin/pip"
    reqs_file = repo_dir + "requirements.txt"
    if os.path.isfile(reqs_file):
        print "Installing requirements at %s" % (reqs_file)
        subprocess.call("%s install -r %s" % (venv_pip, reqs_file), shell=True)

    out_dir = HOME + "testlogs/"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    out_file = out_dir + repo_name + ".log"
    subprocess.call("%s install nose" % (venv_pip), shell=True)
    subprocess.call("%sbin/nosetests -s -w > %s 2>&1 %s"% (venv_dir, out_file, repo_dir), shell=True)


# Read git urls line by line from input file, test each of them
test_repos = open(TEST_REPOS)
for line in test_repos:
    test_repo(line.rstrip())



