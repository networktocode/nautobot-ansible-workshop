"""Nautobot Jobs for the Nautobot + Ansible workshop.

Nautobot discovers Jobs from a Git Repository that provides "jobs" by importing
the top-level `jobs/` package. Each module here registers its own Jobs with
`register_jobs()`, so importing it is enough.

To load these into Nautobot
---------------------------
Extensibility -> Git Repositories -> Add:
  Name:                 nautobot-ansible-workshop
  Remote URL:           <this repo's HTTPS clone URL>
  Provides:             jobs
Then Sync. The jobs appear under Jobs, grouped as "Nautobot Ansible Workshop", and must be
**enabled** before they can run.
"""

from . import launch_awx  # noqa: F401  (import registers the job)

__all__ = ("launch_awx",)
