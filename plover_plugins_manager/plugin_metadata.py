from collections import namedtuple
from functools import total_ordering

from pkg_resources import parse_version


@total_ordering
class PluginMetadata(namedtuple('PluginMetadata', '''
                                author
                                author_email
                                description
                                description_content_type
                                home_page
                                keywords
                                license
                                name
                                summary
                                version
                                ''')):

    @property
    def requirement(self):
        return '%s==%s' % (self.name, self.version)

    @property
    def parsed_version(self):
        v = self.version

        try:
            from packaging.version import Version as PackagingVersion
            if isinstance(v, PackagingVersion):
                v = str(v)
        except Exception:
            # 'packaging' may not be importable in old environments
            pass

        # Decode raw bytes/bytearray → str
        if isinstance(v, (bytes, bytearray)):
            try:
                v = v.decode()
            except Exception:
                v = ''

        # Final fallback: ensure we hand a string to parse_version
        return parse_version(str(v) or '0')

    @classmethod
    def from_dict(cls, d):
        return cls(*(d.get(k, '') for k in cls._fields))

    @classmethod
    def from_kwargs(cls, **kwargs):
        return cls.from_dict(kwargs)

    def to_dict(self):
        return dict(zip(self._fields, self))

    def __eq__(self, other):
        return ((self.name.lower(), self.parsed_version) ==
                (other.name.lower(), other.parsed_version))

    def __lt__(self, other):
        return ((self.name.lower(), self.parsed_version) <
                (other.name.lower(), other.parsed_version))
