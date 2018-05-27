#!/nix/store/r8bx3qf1bpncb14i9gzma4vr089pc3pv-bash-4.4-p19/bin/sh
#
# ===============================
# pywatchman pypi publishing tool
# ===============================
#
# this publishes the watchman python module to the pypi project
# index located at https://pypi.python.org/pypi/pywatchman. the
# metadata used for this process comes directly from setup.py.
#
# this requires write access to the pywatchman project on pypi
# as well as a ~/.pypirc of the following form:
#
#    [distutils]
#    index-servers = pypi
#
#    [pypi]
#    repository: https://pypi.python.org/pypi
#    username: <pypi_username>
#    password: <pypi_password>
#

python setup.py sdist bdist_wheel upload -r pypi
