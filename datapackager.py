#!/usr/bin/env python3

from pathlib import Path
import itertools
import argparse
import zipfile
import logging
import os


CONFIG = 'project'
LOG_LEVELS = {
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'WARNING': logging.WARNING,
}


class ConfigNotFoundError(Exception):
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
        zip_kwargs = {'mode': 'w', 'compression': zipfile.ZIP_DEFLATED, 'compresslevel': compression}
        with zipfile.ZipFile(out / fname, **zip_kwargs) as zip:
            yield release, zip


def gen_files(zips):
    for release, zip in zips:
        # we glob all files. could be optimized though
        for file in Path('.').rglob('*'):
            yield release, zip, file


def write_zips(cfg, gen):
    for tup in gen:
        release, zip, file = tup
        releases = cfg['releases']

        include_file = True

        # ignore folders
        if file.is_dir():
            logging.debug(f'skipped(directory)       {file}')
            continue
        else:
            logging.debug(file)

        # whitelist checking
        for rule in cfg['global'].get('whitelist', []):
            if file.match(rule):
                include_file = True
                break
        else:  # nobreak
            logging.info(f'skipped(whitelist)       {file}')
            include_file = False

        # Let's chain our ignore rules together
        ignore_rules = itertools.chain(
            cfg['global'].get('ignore', []),
            releases[release].get('ignore', []),
        )

        for rule in ignore_rules:
            if file.match(rule):
                include_file = False
                logging.info(f'skipped(ignored)         {file}')
                break

        for pat, replacee in releases[release].get('replacer', {}).items():
            if pat in str(file):
                replacer(zip, file, pat, replacee)
                include_file = False

        for rule in releases[release].get('include', []):
            if file.match(rule):
                include_file = True
                logging.info(f'included                 {file}')
                break

        if include_file:
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
    args = parser.parse_args()

    directory = Path(args.dir)
    output = Path(args.output)

    logging.basicConfig(format='\033[1m%(levelname)s\033[0m: %(message)s', level=LOG_LEVELS[args.log])

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

    return directory, output, args.compression


def get_cfg():
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
    return cfg


def main():
    directory, output, compression = parse_args()

    cfg = get_cfg()

    zips = gen_zips(cfg, output, compression)
    files = gen_files(zips)

    write_zips(cfg, files)


if __name__ == '__main__':
    main()
