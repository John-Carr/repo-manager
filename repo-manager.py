import argparse
import os, sys
from stat import S_ISDIR, S_ISREG
import json
import logging

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
        Fetcher[type](dep_info)

def fetchRaw(dep):
    logging.debug('Fetching raw dependency {}'.format(dep))

def fetchGithub(dep):
    logging.debug('Fetching github {}'.format(dep))
    repo = dep['uri']
    commit = dep['version']
    destination = dep['dest'] if 'dest' in dep else repo.split('/')[-1]
    prev_dir = os.getcwd()
    # TODO we need to check and handle failure conditions and handle accordingly
    # TODO we should replace the os.system calls with subprocess.check_call
    # Clone the repository
    ret = os.system("git clone --recursive {} {}".format(repo, destination))
    if ret != 0:
        logging.info("Failed to clone git repository exit value {}".format(ret))
        exit(ret)
    # Change the directory to the newly cloned repo
    ret = os.chdir(destination)
    if ret != 0:
        logging.info("Failed to change to clone repo directory {}".format(ret))
        exit(ret)
    # Checkout the commit
    ret = os.system("git checkout {}".format(commit))
    if ret != 0:
        logging.info("Failed to checkout version {} exit value {}"
            .format(commit, ret))
        exit(ret)
    # Move to our own branch
    os.system("git checkout -b repo-manager")
    if ret != 0:
        logging.info("Failed to create repo-manager branch exit value {}"
            .format(ret))
        exit(ret)
    # Go back to the directory we were at
    os.chdir(prev_dir)

def fetchDocker(dep):
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