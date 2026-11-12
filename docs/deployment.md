# Deployment

[Quick start](quickstart.md) · [Operations and backups](runbook.md)

The repository provides a Docker Compose demonstration. A remote deployment has
not been verified here, and there is no one-click cloud installer.

## Private remote demo

1. Prepare a Linux x86_64 server that meets the [quick-start prerequisites](quickstart.md).
   Match the supported Ubuntu/Python versions and allow enough memory for the full
   stack; the recorded local host had about 11 GiB RAM.
2. Install Git, Docker Compose, Python 3.14.4, and uv. Clone your published
   repository onto the server.
3. Follow the quick start there. Use new server credentials and download the data
   on the server. `.env`, datasets, and database volumes are not included in Git.
4. Keep the existing localhost port bindings. Access the interfaces through SSH
   from your laptop:

   ```bash
   ssh -N -L 3000:127.0.0.1:3000 -L 8080:127.0.0.1:8080 your_user@your_server
   ```

5. Keep that terminal open and visit http://localhost:3000 for Metabase or
   http://localhost:8080 for Airflow on your laptop.

This is a private demo accessed over SSH. For persistent operation, configure
service startup after reboot and back up databases and required encryption keys
outside the server. See the [backup runbook](runbook.md).

## Public or production use

A public deployment requires additional configuration: HTTPS and access controls,
private database networking, restart policies, monitoring, and tested off-server
backup/restore. Use a reviewed production Compose override or a deployment system
appropriate for your environment. See
[Docker's deployment guidance](https://docs.docker.com/compose/how-tos/production/).

The current SQL Server container uses Developer edition, intended for development,
testing, and demonstrations. Review
[SQL Server licensing](https://download.microsoft.com/download/0/f/4/0f4c1b3c-cbc4-4495-97e4-2050543f49b3/SQL_Server_2022_Licensing_Datasheet.pdf)
and [dataset terms](data-rights.md) before adapting this project for production.
The DAG also uses historical dates; it is not configured as a live order feed.

## Existing Windows or external databases

External databases are not a drop-in option in the current scripts. Host Python
reads the connection settings in `.env`, but Airflow and Metabase explicitly
connect to the Compose service `postgres` and their setup scripts depend on it.
Using Windows-hosted PostgreSQL requires adapting those settings, setup scripts,
network access, roles, and database provisioning. SQL Server supplies inventory;
it does not replace the PostgreSQL warehouse.
