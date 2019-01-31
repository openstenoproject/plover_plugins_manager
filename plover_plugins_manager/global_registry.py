
from collections import defaultdict
from datetime import datetime
import json
import os

from pkg_resources import safe_name

from plover.oslayer.config import CONFIG_DIR
from plover import log

from plover_plugins_manager.package_index import find_plover_plugins_releases
from plover_plugins_manager.plugin_metadata import PluginMetadata


CACHE_FILE = os.path.join(CONFIG_DIR, '.cache', 'plugins.json')
CACHE_VERSION = 4


def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as fp:
                return json.load(fp)
    except:
        log.error('loading `%s` cache failed',
                  CACHE_FILE, exc_info=True)
    return {}

def save_cache(**kwargs):
    dirname = os.path.dirname(CACHE_FILE)
    try:
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(CACHE_FILE, 'w') as fp:
            json.dump(kwargs, fp, indent=2, sort_keys=True)
    except:
        log.error('saving `%s` cache failed',
                  CACHE_FILE, exc_info=True)


def list_plugins():
    cache = load_cache()
    if cache.get('version') == CACHE_VERSION and \
       (cache.get('timestamp', 0.0) + 600.0) >= datetime.utcnow().timestamp():
        plugins = {
            name: [PluginMetadata(*[
                v.get(k, '')
                for k in PluginMetadata._fields
            ]) for v in versions]
            for name, versions in cache.get('plugins', {}).items()
        }
        return plugins
    plugins = defaultdict(list)
    for release in find_plover_plugins_releases():
        release_info = release['info']
        plugin_metadata = PluginMetadata(*[
            release_info.get(k, '')
            for k in PluginMetadata._fields
        ])
        plugins[safe_name(plugin_metadata.name)].append(plugin_metadata)
    plugins = {
        name: list(sorted(versions))
        for name, versions in plugins.items()
    }
    save_cache(version=CACHE_VERSION,
               timestamp=datetime.utcnow().timestamp(),
               plugins={
                   name: [v.to_dict() for v in versions]
                   for name, versions in plugins.items()
               })
    return plugins
