
from collections import defaultdict
from io import StringIO
import site

from pip._vendor.distlib.metadata import Metadata
from pkg_resources import (
    DistInfoDistribution, EggInfoDistribution, WorkingSet, find_distributions
)

from plover_plugins_manager.plugin_metadata import PluginMetadata

from plover import log


def list_plugins():
    working_set = WorkingSet()
    # Make sure user site packages are added
    # to the set so user plugins are listed.
    user_site_packages = site.USER_SITE
    if user_site_packages not in working_set.entries:
        working_set.entry_keys.setdefault(user_site_packages, [])
        working_set.entries.append(user_site_packages)
        for dist in find_distributions(user_site_packages, only=True):
            working_set.add(dist, user_site_packages, replace=True)
    plugins = defaultdict(list)
    for dist in working_set.by_key.values():
        if dist.key == 'plover':
            continue
        for entrypoint_type in dist.get_entry_map().keys():
            if entrypoint_type.startswith('plover.'):
                break
        else:
            continue
        if isinstance(dist, DistInfoDistribution):
            metadata_entry = 'METADATA'
        elif isinstance(dist, EggInfoDistribution):
            metadata_entry = 'PKG-INFO'
        else:
            log.warning('ignoring distribution (unsupported type): %s [%s]', dist, dist.__class__)
            continue
        if not dist.has_metadata(metadata_entry):
            log.warning('ignoring distribution (missing metadata): %s', dist)
            continue
        metadata_str = dist.get_metadata(metadata_entry)
        dist_metadata = Metadata(fileobj=StringIO(metadata_str))
        plugin_metadata = PluginMetadata.from_dict(dist_metadata.todict())
        plugins[dist.key].append(plugin_metadata)
    return {
        name: list(sorted(versions))
        for name, versions in plugins.items()
    }
