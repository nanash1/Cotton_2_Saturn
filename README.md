This is a collection of tools written in Python 3 and C to translate the Sega Saturn game Cotton 2.

The image tools uses an extension module written in C to speed up the compression. If you want to use this module you'll have to compile it from the included C file. There is a fallback method provided in case the module is missing. The fallback method however is slower by a factor of 100 on my PC.
