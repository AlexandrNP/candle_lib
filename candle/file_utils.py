import os
import shutil
import hashlib
from urllib.error import URLError, HTTPError
from urllib.request import urlretrieve
from typing import Dict

from .generic_utils import Progbar
from .modac_utils import get_file_from_modac


def get_file(fname: str,
             origin: str,
             unpack: bool = False,
             md5_hash: str = None,
             cache_subdir: str = 'common',
             datadir: str = None) -> str:
    """Downloads a file from a URL if it not already in the cache. Passing the
    MD5 hash will verify the file after download as well as if it is already
    present in the cache.

    Parameters
    ----------
    fname : string
        name of the file
    origin : string
        original URL of the file
    unpack : boolean
        whether the file should be decompressed
    md5_hash : string
        MD5 hash of the file for verification
    cache_subdir : string
        directory being used as the cache
    datadir : string
        if set, datadir becomes its setting (which could be e.g. an absolute path) and cache_subdir no longer matters

    Returns
    ----------
    string
        Path to the downloaded file
    """
    if datadir is None and os.environ['CANDLE_DATA_DIR'] is not None:
        datadir = os.environ['CANDLE_DATA_DIR']
    elif datadir is None and os.environ['CANDLE_DATA_DIR'] is None:
        raise ValueError(
            'Need data directory. Either pass datadir or set CANDLE_DATA_DIR environment variable'
        )

    if cache_subdir is not None:
        datadir = os.path.join(datadir, cache_subdir)

    if not os.path.exists(datadir):
        os.makedirs(datadir)

    if fname.endswith('.tar.gz'):
        fnamesplit = fname.split('.tar.gz')
        unpack_fpath = os.path.join(datadir, fnamesplit[0])
        unpack = True
    elif fname.endswith('.tgz'):
        fnamesplit = fname.split('.tgz')
        unpack_fpath = os.path.join(datadir, fnamesplit[0])
        unpack = True
    elif fname.endswith('.zip'):
        fnamesplit = fname.split('.zip')
        unpack_fpath = os.path.join(datadir, fnamesplit[0])
        unpack = True
    else:
        unpack_fpath = None

    fpath = os.path.join(datadir, fname)
    if not os.path.exists(os.path.dirname(fpath)):
        os.makedirs(os.path.dirname(fpath))

    download = False
    if os.path.exists(fpath) or (unpack_fpath is not None and
                                 os.path.exists(unpack_fpath)):
        # file found; verify integrity if a hash was provided
        if md5_hash is not None:
            if not validate_file(fpath, md5_hash):
                print('A local file was found, but it seems to be '
                      'incomplete or outdated.')
                download = True
    else:
        download = True

    # fix ftp protocol if needed
    '''
    if origin.startswith('ftp://'):
        new_url = origin.replace('ftp://','http://')
        origin = new_url
    print('Origin = ', origin)
    '''

    if download:
        if 'modac.cancer.gov' in origin:
            get_file_from_modac(fpath, origin)
        else:
            print('Downloading data from', origin)
            global progbar
            progbar = None

            def dl_progress(count, block_size, total_size):
                global progbar
                if progbar is None:
                    progbar = Progbar(total_size)
                else:
                    progbar.update(count * block_size)

            error_msg = 'URL fetch failure on {}: {} -- {}'
            try:
                try:
                    urlretrieve(origin, fpath, dl_progress)
                    # fpath = wget.download(origin)
                except URLError as e:
                    raise Exception(error_msg.format(origin, e.errno, e.reason))
                except HTTPError as e:
                    raise Exception(error_msg.format(origin, e.code, e.msg))
            except (Exception, KeyboardInterrupt) as e:
                print(f"Error {e}")
                if os.path.exists(fpath):
                    os.remove(fpath)
                raise
            progbar = None
            print()

    if unpack:
        if not os.path.exists(unpack_fpath):
            print('Unpacking file...')
            try:
                shutil.unpack_archive(fpath, datadir)
            except (Exception, KeyboardInterrupt) as e:
                print(f"Error {e}")
                if os.path.exists(unpack_fpath):
                    if os.path.isfile(unpack_fpath):
                        os.remove(unpack_fpath)
                    else:
                        shutil.rmtree(unpack_fpath)
                raise
        return unpack_fpath

    return fpath


def validate_file(fpath: str, md5_hash: str) -> bool:
    """Validates a file against a MD5 hash.

    Parameters
    ----------
    fpath : string
        path to the file being validated
    md5_hash : string
        the MD5 hash being validated against

    Returns
    ----------
    boolean
        Whether the file is valid
    """
    hasher = hashlib.md5()
    with open(fpath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    if str(hasher.hexdigest()) == str(md5_hash):
        return True
    else:
        return False


def directory_from_parameters(params: Dict, commonroot: str = 'Output') -> str:
    """Construct output directory path with unique IDs from parameters.

    Parameters
    ----------
    params : python dictionary
        Dictionary of parameters read
    commonroot : string
        String to specify the common folder to store results.

    Returns
    ----------
    string
        Path to the output directory
    """

    if commonroot in set(['.',
                          './']):  # Same directory --> convert to absolute path
        outdir = os.path.abspath('.')
    else:  # Create path specified
        outdir = os.path.abspath(os.path.join('.', commonroot))
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        outdir = os.path.abspath(os.path.join(outdir, params['experiment_id']))
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        outdir = os.path.abspath(os.path.join(outdir, params['run_id']))
        if not os.path.exists(outdir):
            os.makedirs(outdir)

    return outdir
