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
import_error = "ImportError: No module named "
import_error_len = len(import_error)
devnull = open(os.devnull, 'w')

# Location of this python file
test_home = os.path.dirname(os.path.abspath(__file__)) + "/"
log_home = test_home + "logs/"
venv_original_home = test_home + "venv_original/"
venv_nondex_home = test_home + "venv_nondex/"
venv_original = {"home": venv_original_home,
                 "python": venv_original_home + "bin/python",
                 "pip": venv_original_home + "bin/pip",
                 "nosetests": venv_original_home + "bin/nosetests",
                 "tox": venv_original_home + "bin/tox",
                 "exe": sys.executable}

venv_nondex =   {"home": venv_nondex_home,
                 "python": venv_nondex_home + "bin/python",
                 "pip": venv_nondex_home + "bin/pip",
                 "nosetests": venv_nondex_home + "bin/nosetests",
                 "tox": venv_nondex_home + "bin/tox",
                 "exe": "/home/yan/pynondex/python-2.7.12/bin/python"}

def venvify_exe(exe, venv_dict):
    return venv_dict["home"] + "bin/" + exe

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

    def setup_tests(info):
        def replace_first(string, word, rep):
            return string[:len(word)].replace(word, rep) + string[len(word):]

        def venvify(s):
            replaceables = ["python", "nosetests", "coverage", "pip"]
            for exe in replaceables:
                s = replace_first(s, exe, venvify_exe(exe, info))
            return s

        def get_command(s):
            if s == None:
                return ""
            return venvify('\n'.join(s) if type(s) is list else s)

        def can_iterate(yaml_contents, key):
            return key in yaml_contents and yaml_contents[key] is not None

        cd(repo_dir)

        # Write .pth file for venv so that tests import the library correctly
        path_file = open(info["home"] + "lib/python2.7/site-packages/paths.pth", "w+")
        path_file.write(repo_dir)

        reqs_file = repo_dir + "requirements.txt"
        travis_file = repo_dir + ".travis.yml"

        if not os.path.exists(log_home):
            os.makedirs(log_home)

        if os.path.isfile(travis_file):
            print "> Parsing .travis.yml"
            with open(travis_file) as stream:
                yaml_contents = yaml.load(stream)
                if can_iterate(yaml_contents, 'before_install'):
                     for cmd in yaml_contents['before_install']:
                        subprocess.call(venvify(cmd), shell=True, stdout=devnull, stderr=devnull)
                if can_iterate(yaml_contents, 'install'):
                    for cmd in yaml_contents['install']:
                        subprocess.call(venvify(cmd), shell=True, stdout=devnull, stderr=devnull)
                if can_iterate(yaml_contents, 'before_script'):
                    for cmd in yaml_contents['before_script']:
                        subprocess.call(venvify(cmd), shell=True, stdout=devnull, stderr=devnull)
                test_command = get_command(yaml_contents['script'])
                return test_command
        else:
            print "> No .travis.yml found, attempting to use requirements.txt"
            subprocess.call("%s install -r %s" % (info["pip"], reqs_file), shell=True)
            return info["nosetests"]

    print "> Running tests on standard Python"
    result = setup_tests(venv_original)

    if result == None:
        remove_library(url)
        return

    outfile_path_original = log_home + repo_name + "_original.log"
    with open(outfile_path_original, 'w') as f:
        print result
        subprocess.call(result, shell=True, stdout=f, stderr=f)

    # Remove this library if there are import errors
    with open(outfile_path_original) as f:
        for line in f:
            if line.startswith(import_error):
                remove_library(url)

    print "> Running tests on nondex Python"
    result = setup_tests(venv_nondex)

    if result == None:
        remove_library(url)
        return

    outfile_path_nondex = log_home + repo_name + "_nondex.log"
    with open(outfile_path_nondex, 'w') as f:
        subprocess.call(result, shell=True, stdout=f, stderr=f)

    data_orig = ''
    data_nondex = ''
    with open(outfile_path_original, 'r') as f:
        data_orig = f.read()
    with open(outfile_path_nondex, 'r') as f:
        data_nondex = f.read()

    if data_orig.count('\n') != data_nondex.count('\n'):
        main_log_file.write("%s\n" % repo_name)
        main_log_file.flush()

# Set up virtual environment
if "--setup" in sys.argv[1:]:
    print "> Setting up virtualenv"
    subprocess.call("virtualenv -p %s %s" % (venv_original["exe"], venv_original["home"]), shell=True)
    subprocess.call("virtualenv -p %s %s" % (venv_nondex["exe"], venv_nondex["home"]), shell=True)
    print venv_original["pip"]
    subprocess.call(venv_original["pip"] + " install nose", shell=True)
    subprocess.call(venv_original["pip"] + " install tox", shell=True)
    subprocess.call(venv_nondex["pip"] + " install nose", shell=True)
    subprocess.call(venv_nondex["pip"] + " install tox", shell=True)

# Read git urls line by line from input file, test each of them
test_repos = open(repos_file)
for line in test_repos:
    test_repo(line.rstrip())
main_log_file.close()
