# Plover Plugin Manager

> **⚠️  Important:** This standalone Plugin Manager is only required for **Plover v4**.  
> Starting with **Plover v5** its functionality is built directly into Plover itself, so you
> do **not** need to install or update this package when running Plover v5 or later.


## Release history

### 0.7.9

* Remove debugging prints from previous tests

### 0.7.8

* Added debugging prints

### 0.7.7

* Burned during testing 

### 0.7.6

* Burned during testing 

### 0.7.5

* add workaround for different requests-cache versions

### 0.7.4

* fix plugin version parsing since pkginfo now returns packaging.version.Version objects instead of plain strings
* fix CachedSession.remove_expired_responses() error
* change caching from sqlite to memory since that's more robust

### 0.7.3

* burned this release number with a wrong upload to PyPi


### 0.7.2

* added button in UI to take Git url for installation

### 0.7.1

* fix editable installation (ensure UI files are properly generated)

### 0.7.0

* tweak custom info widget's API for reuse in other plugins

### 0.6.3

* fix Python packaging

### 0.6.2

* fix compatibility with `requests-cache>=0.8.0`

### 0.6.1

* minor tweaks to make packaging for AUR easier

### 0.6.0

* warn users about the security risk when installing plugins
* fix plugin install/removal when running in a Python virtual environment

### 0.5.16

* stop using PyPI's (disabled) XMLRPC search endpoint, and switch to a self-hosted registry of
  available plugins (maintained at <https://github.com/openstenoproject/plover_plugins_registry>).

### 0.5.15

* fix support for cancelling an install/update/removal operation on Windows.

### 0.5.14

* drop the use of pip's internal APIs
* drop the dependency on PyQt5 WebEngine
* improve and simplify cache handling: persistently cache all network
  requests (with a 10 minutes expiration date)
* support for Python 3.8

### 0.5.13

* add support for `pip>=18.0`
* add support for `PyQt5>=5.11`
* add support for Markdown plugin descriptions

### 0.5.12

* improve handling of plugins when user site is disabled: always list the
  version for the user installed plugin (even if it's older than the system
  package version and user site packages are disabled)
* disable pip version check
* add support for `pip>=10.0`

### 0.5.11

* plugins are now handled even if they can't be loaded by Plover
  (so it's possible to update/uninstall broken plugins)

### 0.5.10

* fix #5: open all links externally

### 0.5.9

* refresh PyPI metadata in the background
* cache PyPI metadata for 10 minutes
* do not crash if connection to PyPI fails

## Credits

Icons made by [Freepik][] from [www.flaticon.com][] and Yusuke Kamiyamane.

  [Freepik]: http://www.freepik.com/
  [www.flaticon.com]: http://www.flaticon.com/
