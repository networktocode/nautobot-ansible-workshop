"""Package marker for the workshop lab repository. Do not delete.

Nautobot imports Jobs from a Git repository with `pkgutil.walk_packages()`,
which only descends into directories containing an `__init__.py`. Without this
file the `jobs` package is never imported, and the repository sync still
reports success while logging:

    No jobs were registered on loading the `nautobot_ansible_workshop.jobs` submodule.
    Did you miss a `register_jobs()` call? ...

That message is misleading: `register_jobs()` is fine; the package was never
imported.
"""
