#!/usr/bin/env python3

from pathlib import Path
import itertools
import argparse
import zipfile
import pprint
import os

CONFIG = 'project'


def replacer(zip, file, pat, replacee):
    ''' This function aids in replacing the .mcfunction w/ .paper '''
    new_file = str(file).replace(pat, replacee)
    contents = file.read_text()
    zip.writestr(new_file, contents)
    print(f'replaced {str(new_file)}', end=' ')


def gen_zips(cfg, out, compression):
    for release, options in cfg['releases'].items():

        # constructs the filename based upon format
        fname = cfg['name-format'].format(
            title=cfg['title'],
            version=cfg['version'],
            release_name=options['name'] if 'name' in options else release
        ).strip() + options.get('ending', '.zip')

        print(release)

        file = out / fname
        if file.exists():
            file.unlink()
            print(f'overwriting {fname}')

        zip = zipfile.ZipFile(
            out / fname, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=compression)
        yield release, zip
        zip.close()
        print()


def gen_files(zips):
    for release, zip in zips:
        for file in Path('.').rglob('*'):
            yield release, zip, file


def write_zips(cfg, gen):
    for tup in gen:
        release, zip, file = tup
        releases = cfg['releases']
        print(str(file), end=' ')

        include_file = True

        # First, let's whitelist
        for rule in cfg['global'].get('whitelist', []):
            if file.match(rule):
                include_file = True
                break
        else:  # nobreak
            include_file = False

        # Let's chain our ignore rules together
        ignore_rules = itertools.chain(
            cfg['global'].get('ignore', []),
            releases[release].get('ignore', []),
        )

        for rule in ignore_rules:
            if file.match(rule):
                include_file = False
                break

        for pat, replacee in releases[release].get('replacer', {}).items():
            if pat in str(file):
                replacer(zip, file, pat, replacee)
                include_file = False

        for rule in releases[release].get('include', []):
            if file.match(rule):
                include_file = True
                break

        if include_file:
            zip.write(file)
        else:
            print('ignored', end=' ')
        print()


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
    args = parser.parse_args()

    directory = Path(args.dir)
    output = Path(args.output)

    if directory.exists():
        os.chdir(str(directory))  # 3.6+ allows output w/o str(...)
        output.mkdir(parents=True, exist_ok=True)
    else:
        print('Input directory does not exist')
        exit()

    return directory, output, args.compression


def get_cfg():
    try:
        import toml
        cfg = toml.load(f'{CONFIG}.toml')
    except ModuleNotFoundError:
        import json
        if Path(f'{CONFIG}.json').exists():
            cfg = toml.load(f'{CONFIG}.json')
        else:
            print('Error. No project.json found! Did you forget to pip install toml or did you forget a project.toml')  # noqa
        cfg = json.load(f'{CONFIG}.json')
    return cfg


def main():
    directory, output, compression = parse_args()

    cfg = get_cfg()
    pprint.pprint(cfg)
    print()

    zips = gen_zips(cfg, output, compression)
    files = gen_files(zips)

    write_zips(cfg, files)


if __name__ == '__main__':
    main()
