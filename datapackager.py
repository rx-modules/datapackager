#!/usr/bin/env python3

from timeit import default_timer as timer
from fnmatch import fnmatch
from pathlib import Path
from collections import namedtuple
import argparse
import zipfile
import logging
import os
import re


VERSION = namedtuple('version', 'major minor patch')(1, 1, 0)

CONFIG = 'project'
LOG_LEVELS = {
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'WARNING': logging.WARNING,
}

RULES = {'ignore', 'replacer', 'include', 'regex'}


class ConfigError(Exception):
    pass


class ConfigNotFoundError(ConfigError):
    pass


def replacer(zip, file, pat, replacee):
    ''' This function aids in replacing via the cfg option '''
    new_file = str(file).replace(pat, replacee)
    contents = file.read_text()
    zip.writestr(new_file, contents)
    logging.info(f'replacer(contents: file) {file}: {str(new_file)}')


def gen_zips(cfg, out, compression):
    for release, options in cfg['releases'].items():

        # constructs the filename based upon format
        fname = cfg['name-format'].format(
            title=cfg['title'],
            version=cfg['version'],
            release_name=options['name'] if 'name' in options else release
        ).strip() + options.get('ending', '.zip')

        logging.info(f'working w/ {release}')

        file = out / fname

        # overwrite the zip if it exists
        if file.exists():
            file.unlink()
            logging.warning(f'overwriting {fname} since it already exists')

        # ZipFile as a resource manager so that it auto closes
        zip_kwargs = {
            'mode': 'w',
            'compression': zipfile.ZIP_DEFLATED,
            'compresslevel': compression
        }

        # cfg
        # default rule
        cfg['releases'][release]['rules'] = cfg['releases'][release].get('rules', [])
        cfg['releases'][release]['rules'].insert(
            0,
            {rule: cfg['releases'][release].get(rule, [] if rule not in {'replacer', 'regex'} else {}) for rule in RULES}  # noqa
        )

        with zipfile.ZipFile(out / fname, **zip_kwargs) as zip:
            yield release, zip


def gen_files(zips):
    for release, zip in zips:
        # we glob all files. could be optimized though
        for file in Path('.').rglob('*'):
            yield release, zip, file


def match(file, pattern):
    '''dumb matching dumb dumb dumb dumb'''

    # first do pathlib matching
    if file.match(pattern):
        return True

    # then do fnmatch'ing
    return fnmatch(str(file), pattern)


def write_zips(cfg, gen):
    for tup in gen:
        release, zip, file = tup
        lines = None

        # ignore folders
        if file.is_dir():
            logging.debug(f'skipped(directory)       {file}')
            continue

        logging.debug(file)

        # whitelist checking
        for rule in cfg['global'].get('whitelist', []):
            if match(file, rule):
                include_file = True
                break
        else:  # nobreak
            # logging.info(f'skipped(whitelist)       {file}')
            include_file = False

        # global ignore
        for rule in cfg['global'].get('ignore', []):
            if match(file, rule):
                include_file = False
                logging.info(f'skipped(ignored)         {file}')
                break

        # rules
        for rule in cfg['releases'][release]['rules']:
            for ignore_rule in rule.get('ignore', []):
                if match(file, ignore_rule):
                    include_file = False
                    logging.info(f'skipped(ignored)         {file}')
                    break

            for pat, replacee in rule.get('replacer', {}).items():
                if include_file and pat in str(file):
                    replacer(zip, file, pat, replacee)

            for include_rule in rule.get('include', []):
                if match(file, include_rule):
                    include_file = True
                    logging.info(f'included                 {file}')
                    break

            if include_file and 'regex' in rule:
                with file.open() as f:
                    lines = f.readlines()
                for i in range(len(lines)):
                    for pat, repl in rule['regex'].items():
                        try:
                            pat = re.compile(pat)
                        except Exception:
                            logging.warning(f'regex failed compile')
                            continue

                        if pat.search(lines[i]):
                            out = pat.sub(repl, lines[i])
                            logging.info(f'regex: replaced {lines[i]} w/ {out}')
                            lines[i] = out

        if include_file:
            if lines:
                zip.writestr(str(file), '\n'.join(lines))
                continue
            zip.write(file)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('dir', help='input directory to build')
    parser.add_argument(
        '-o', '--output', help='output directory for zips', default='releases')
    parser.add_argument(
        '-c', '--compression',
        help='compression level for zipping',
        default=6, type=int, choices=list(range(0, 10))
    )
    parser.add_argument(
        '-l', '--log',
        help='changed logging level to INFO',
        default='INFO', type=str, choices={'DEBUG', 'INFO', 'WARN'}
    )
    parser.add_argument(
        '-v', '--version',
        help='override version level in config file',
        default=None, type=str
    )
    args = parser.parse_args()

    directory = Path(args.dir)
    output = Path(args.output)

    logging.basicConfig(
        format='\033[1m%(levelname)s\033[0m: %(message)s', level=LOG_LEVELS[args.log])

    # if debug:
    #     logging.setLevel(logging.DEBUG)
    # else:
    #     logging.setLevel(logging.INFO)

    logging.info('parsed args')

    if not directory.exists():
        raise FileNotFoundError(f'the directory, {str(directory)}, was not found')

    os.chdir(str(directory))  # 3.6+ allows output w/o str(...)
    output.mkdir(parents=True, exist_ok=True)
    logging.info(f'{str(directory)} exists')

    return directory, output, args.compression, args.version


def get_cfg(version):
    cfg = None
    toml_cfg = f'{CONFIG}.toml'
    json_cfg = f'{CONFIG}.json'

    # First, let's try toml config
    try:
        import toml
        cfg = toml.load(toml_cfg)
    except ModuleNotFoundError:
        if Path(toml_cfg).exists():
            logging.warning(f'{toml_cfg} exists but toml is not installed')
        else:
            logging.warning('toml is not installed')
    except FileNotFoundError:
        logging.warning(f'{toml_cfg} does not exist')

    # If we still don't have cfg, let's try json
    if cfg is None:
        import json
        logging.info('trying json config')
        try:
            cfg = json.load(json_cfg)
        except FileNotFoundError:
            logging.warning(f'{json_cfg} does not exist')  # noqa
            raise ConfigNotFoundError('Could not find a project config.')

    logging.info('successfully loaded config')

    # override version from parse_args
    cfg['version'] = version if version is not None else cfg['version']

    # config version checking
    if 'config-version' not in cfg:
        raise ConfigError(f'config-version not found. Please use version: {".".join(VERSION)}')
    else:
        try:
            major, minor, patch = [int(i) for i in cfg['config-version'].split('.')]
        except ValueError:
            raise ConfigError(
                'config-version incorrectly formatted. Must be in form: major.minor.patch')

        if major < VERSION.major:
            raise ConfigError(
                f'datapackager is on major version {VERSION.major} while config provided {major}')

        elif minor < VERSION.minor:
            logging.warning(
                f'datapackager is on minor version {VERSION.minor} while config provided {minor}')

        elif patch < VERSION.patch:
            logging.info(
                f'datapackager is on patch version {VERSION.patch} while config provided {patch}')

    return cfg


def main():
    t0 = timer()
    directory, output, compression, version = parse_args()

    cfg = get_cfg(version)

    zips = gen_zips(cfg, output, compression)
    files = gen_files(zips)

    write_zips(cfg, files)
    t1 = timer()

    delta = (t1 - t0) * 1000
    print(f'\nSuccess! Completed in {delta:.2f}ms')


if __name__ == '__main__':
    main()
