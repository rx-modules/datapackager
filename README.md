## datapackager.py - a small python build script to manage your datapacks

This script will allow you to maintain multiple release versions of your datapack through a project configuration file. It allows you to maintain a paper compatibility and even a fully functioning fabric mod jar through a simple set of ignore and inclusion rules.

## Code Examples

* `python datapackager.py --help`
* `python datapackager.py /path/to/my/datapack/`
* `python datapackager.py /path/to/my/datapack/ --output releases/`

*Your setup may require python3 instead of python*

## Configuration Examples

Recommended: As a [toml file](example.toml).

As a [json file](example.json).

## Motivation

The purpose of this project is to make the maintaince of multiple datapack releases much easier. The rules system allow you to dynamically allow/disallow different files which can help you tweak different files. For example, a certain aspect of your datapack might need to be disabled for your datapack on Paper while certain biome json files can be removed for Fabric compatibility.

This project also helps us MacOS peeps to painlessly remove `.DS_Store` everywhere. You can also produce a working Fabric jar which is in the example configuration files.

## Dependencies

This script has a soft-dependancy on the [toml](https://pypi.org/project/toml/) python library. If you don't have `toml` or don't wish to use it, you can easily use the `json` configuration file format.

To get `toml`, you can easily run:

    pip install toml


*Your setup may require pip3 instead of pip*

## Script

You can easily slap this script anywhere you like. You will have to be aware of the relative path of your datapack, but an absolute path will always work!

Note that this script will overwrite zip files. *TODO: add argument to disable that*

## Usage

This script comes with minor tweaking options but the main usage is as follows:
`python datapackager.py <datapack path>`

Running: `python datapackager.py -h` will pull up a help menu describing the other options
* `datapack <path>` which datapack you would like to package
* `-o --output <name/path>` will set the output folder for all of the zips.
	* This is in the directory of the datapack folder. 
    * By default it is `releases/` but you can change to to outside the folder via `../<name>`
    * Since this is inside the datapack folder, you'll wanna ignore the `<name>` folder.
    * This will create the folder if it doesn't exist.
* `-c --compression <0:9>` will set the level of compression the packager will use
    * By default this is `6`
* `-l --log <INFO|DEBUG|WARN>` will set the logging level.
    * By default this is `INFO`


## Notes

This script is still pretty new. I mostly wanted a small build tool for me to zip file files easily, but some other folks recommended some ideas for me. I plan to add some pre-build options such as running scripts in place or running a pre-processor from somewhere else.

I'm on discord as @rx#1284. Catch me in the r/minecraftcommands discord.

## License

[MIT](LICENSE.md)
