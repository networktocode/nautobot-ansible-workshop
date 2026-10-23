"""Lab 3 — launch an AWX Job Template from a Nautobot device page.

Why a Nautobot Job and not a Custom Link
----------------------------------------
A Custom Link is a templated URL that deep-links the operator into AWX's launch
form. It leaves no record on the Nautobot side.

A Job Button runs a Nautobot Job, which gives you:
  * server-side logic with the full Nautobot ORM in scope
  * a JobResult with logs, retained and searchable
  * RBAC on who may press the button
  * the ability to validate or enrich before anything reaches AWX

It also means attendees have run a Nautobot Job before the workshop discusses
when a Nautobot Job is a better fit than AWX.

Configuration
-------------
Environment variables on the Nautobot worker (playbooks/seed_awx.yml sets them):
  AWX_HOST           base URL of AWX, as reached from the worker
  AWX_TOKEN          an AWX OAuth2 token
  AWX_JOB_TEMPLATE   name of the Job Template to launch

AWX_HOST must be reachable from the Celery worker, which is where this Job
runs. If Nautobot runs in containers, `localhost` is the container itself: use
`host.docker.internal` (with `extra_hosts: ["host.docker.internal:host-gateway"]`
on the worker service) rather than a Docker bridge gateway address, which
varies between hosts. If Nautobot runs directly on the host, use an address the
host can reach AWX on.

When AWX is exposed with `kubectl port-forward`, start it with
`--address 0.0.0.0`; the default binds 127.0.0.1 only.

The target Job Template needs "Prompt on launch" enabled for Variables
(`ask_variables_on_launch: true`), otherwise AWX discards the extra_vars this
Job sends.
"""

import os

import requests

from nautobot.apps.jobs import JobButtonReceiver, register_jobs

# Groups these jobs together in the Nautobot Jobs list.
name = "Nautobot Ansible Workshop"

DEFAULT_TIMEOUT = 15


class LaunchAWXJobTemplate(JobButtonReceiver):
    """Launch an AWX Job Template for the device whose page this button is on."""

    class Meta:
        name = "Launch AWX job for this device"
        description = (
            "Posts to the AWX API to launch a Job Template, passing this device "
            "as extra_vars. Returns the AWX job ID and a direct link."
        )

    def receive_job_button(self, obj):
        awx_host = os.getenv("AWX_HOST", "").rstrip("/")
        awx_token = os.getenv("AWX_TOKEN", "")
        template_name = os.getenv("AWX_JOB_TEMPLATE", "Configure Dynamic Group members")

        if not awx_host or not awx_token:
            self.logger.failure(
                "AWX_HOST and AWX_TOKEN must be set on the Nautobot worker. "
                "Remember AWX_HOST must be reachable from inside the Nautobot "
                "container — localhost will not work."
            )
            return

        headers = {
            "Authorization": f"Bearer {awx_token}",
            "Content-Type": "application/json",
        }

        # Look the template up by name rather than hardcoding a numeric ID, so
        # this survives a rebuilt AWX.
        self.logger.info("Looking up AWX Job Template %r", template_name)
        try:
            lookup = requests.get(
                f"{awx_host}/api/v2/job_templates/",
                params={"name": template_name},
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )
            lookup.raise_for_status()
        except requests.RequestException as exc:
            self.logger.failure("Could not reach AWX at %s: %s", awx_host, exc)
            return

        results = lookup.json().get("results", [])
        if len(results) != 1:
            self.logger.failure(
                "Expected exactly one AWX Job Template named %r, found %d.",
                template_name,
                len(results),
            )
            return

        template = results[0]
        template_id = template["id"]

        # Everything AWX needs to act on this specific device. The playbook can
        # use device_name directly; device_id is the Nautobot UUID, handy for
        # writing results back.
        payload = {
            "extra_vars": {
                "device_name": obj.name,
                "device_id": str(obj.pk),
                "device_location": str(obj.location.name) if obj.location else "",
                "triggered_from": "nautobot-job-button",
            }
        }

        self.logger.info("Launching AWX Job Template %s (id=%s)", template_name, template_id)
        try:
            launch = requests.post(
                f"{awx_host}/api/v2/job_templates/{template_id}/launch/",
                json=payload,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )
            launch.raise_for_status()
        except requests.RequestException as exc:
            body = getattr(exc.response, "text", "")
            self.logger.failure("AWX rejected the launch: %s %s", exc, body)
            return

        job = launch.json()
        job_id = job.get("id")
        job_url = f"{awx_host}/#/jobs/playbook/{job_id}"

        self.logger.info("AWX job **%s** launched for %s: %s", job_id, obj.name, job_url)
        self.logger.info(
            "Extra vars sent: %s",
            ", ".join(f"{k}={v}" for k, v in payload["extra_vars"].items()),
        )

        # Returned values appear in the JobResult, so the operator sees the AWX
        # job id without digging through the log.
        return f"AWX job {job_id} launched for {obj.name}"


register_jobs(LaunchAWXJobTemplate)
