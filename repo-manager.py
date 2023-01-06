import argparse
import os, sys
from stat import S_ISDIR, S_ISREG
import json
import logging
import subprocess
import requests

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def main(args):
    print('Welcome to repo manager!')
    logging.debug('Debuging with config @ %s' % args.config_file)
    # Figure out if the config file is a file or directory
    abs_config_file = os.path.join(os.getcwd(), args.config_file)
    mode = os.lstat(abs_config_file).st_mode
    manifest_files = []
    if S_ISDIR(mode):
        # If its a dir parse all the files
        logging.debug('Parsing directory of manifest files')
        dir_list = os.listdir(args.config_file)
        dir_list = [os.path.join(abs_config_file, i) for i in dir_list]
        logging.debug(dir_list)
        # Exclude directories from the list of manifest files
        for item in dir_list:
            mode = os.lstat(item).st_mode
            # We wont recurse down sub dirs
            if(S_ISDIR(mode)):
                logging.debug('Removing %s' % item)
                dir_list.remove(item)
                continue
            # Only use *.json files
            split_tup = os.path.splitext(item)
            file_extension = split_tup[1]
            if(file_extension != '.json'):
                logging.debug('ignoring %s' % item)
                continue
            manifest_files.append(item)
    elif S_ISREG(mode):
        # If its a file go ahead and parse it
        logging.debug('Parsing a single manifest file')
        manifest_files.append(args.config_file)
    else:
        # Unknown file type, logging.debug a message
        logging.debug('Skipping %s' % args.config_file)

    # Parse files to make a list of json objects
    dependencies = parseFiles(manifest_files)
    fetchDependcies(dependencies)

def parseFiles(files):
    data = {}
    for file in files:
        logging.debug('Parsing file %s' % file)
        f = open(file)
        data.update(json.load(f))
        f.close()
    return data

def fetchDependcies(dependencies):
    logging.debug('Fetching dependencies')
    logging.debug(dependencies)
    for dep in dependencies:
        logging.debug('Dependency name %s ' % dep)
        dep_info = dependencies[dep]
        type = dep_info['type']
        logging.debug('Dependency type: %s' % type)
        Fetcher[type](dep, dep_info)

def fetchRaw(name, dep):
    logging.info('Fetching raw dependency {}'.format(name))
    # Get information needed to pull dependency
    url = dep['uri']
    file = dep['file'] if 'file' in dep else url.split('/')[-1]
    version = dep['version'] if 'version' in dep else ''
    destination = dep['dest'] if 'dest' in dep else os.getcwd()
    # Stash our current directory
    prev_dir = os.getcwd()
    # Check to see if we have already cloned this object
    # Get the path (strip last / if it exists)
    os.path.normpath(destination)
    try:
        os.chdir(destination)
    except FileNotFoundError as e:
        logging.error("{}:Cannot create directory. Error: {}".format("fetchRaw", e))

    if os.path.exists(file):
        logging.debug("File already exists at {}, skipping fetch.".format(destination))
        return
    else:
        logging.debug("File {} does not exist, fetching.".format(file))
    
    # try to get the object
    try:
        response = requests.get(url)
    except Exception as e:
        print(e)

    # Get the file name if its not given in the manifest
    file = url.split('/')[-1] if not file else file
    # try to write object
    try:
        logging.debug("Creating file at `{}/{}".format(destination, file))
        open(destination + '/' + file, 'wb').write(response.content)
    except Exception as e:
        print(e)


def fetchGithub(name, dep):
    logging.info('Fetching github dependency {}'.format(name))
    # Get information needed to pull dependency
    repo = dep['uri']
    commit = dep['version'] if 'version' in dep else 'HEAD'
    commit = commit if commit else 'HEAD'
    destination = dep['dest'] if 'dest' in dep else repo.split('/')[-1]
    # Stash our current directory
    prev_dir = os.getcwd()
    logging.debug("Saving dir as {}".format(prev_dir))

    # Check to see if we have already cloned this repository
    try:
        os.chdir(destination)
    except FileNotFoundError as e:
        # This means we should continue and clone so just continue
        pass
    else:
        logging.info("{}: Directory already exists skipping clone".format(name))
        os.chdir(prev_dir)
        return

    # Clone the repository
    try:
        subprocess.check_call(["git", "clone", "--recursive", repo, destination],
                                    stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print("Failed to clone {}".format(repo))
        exit(1)
        
    # Change the directory to the newly cloned repo
    os.chdir(destination)

    # Checkout the commit
    try:
        subprocess.check_call(["git", "checkout", commit],
                                    stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logging.info("Failed to checkout version {}"
            .format(commit))
        exit(1)
        
    # Move to our own branch
    try:
        subprocess.check_call(["git", "checkout", "-b", "repo-manager"])
    except subprocess.CalledProcessError as e:
        logging.info("Failed to create repo-manager branch exit value")
        exit(1)
    # Go back to the directory we were at
    os.chdir(prev_dir)
    logging.debug("Left func at {}".format(os.curdir))

def fetchDocker(name, dep):
    logging.debug('Fetching docker {}'.format(dep))

Fetcher = {
    "git": fetchGithub,
    "raw": fetchRaw,
    "docker": fetchDocker
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--config_file', type=str, default='repo-manifest',
                        required = False, help='The file to fetch dependencies from')
    
    args = parser.parse_args()
    main(args)