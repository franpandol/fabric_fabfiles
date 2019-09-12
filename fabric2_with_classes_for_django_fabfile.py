#!/usr/bin/python
from fabric import Connection, Config
import invoke
from invoke import task
import os
import time


@task
def full_deploy(local_context):
    FabfileClass().full_deploy()


@task
def restart_all(local_context):
    FabfileClass().restart_all()


@task
def fast_deploy(local_context):
    FabfileClass().fast_deploy()


class FabfileClass():
    remote_connection = None
    hosts = ["your_host_ip"]
    user = "serveruser"
    user_password = "serveeruserpassword"
    virtualenv_root = '~/.virtualenvs/your_project_name'
    project_name = "your_project_name"
    webapps_password = ""
    psql_user = "postgres_user"
    psql_database_name = "postgres_database_name"
    psql_password = "postgres_user_password"
    supervisor_process_name = "your_project_name"
    bitbucket_user = ""
    bitbucket_url = "https://{}@bitbucket.org/your_user/your_project_name.git".format(
        bitbucket_user)

    remote_config = Config(overrides={'sudo': {'password': user_password}})
    remote_connection = Connection(hosts[0], user=user, connect_kwargs={
                                   'password': user_password}, config=remote_config)

    def full_deploy(self):
        for host in self.hosts:
            self.remote_connection = Connection(
                host,
                user=self.user,
                connect_kwargs={'password': self.user_password},
                config=self.remote_config
            )
            self._pull()
            self._migrate()
            self._restart_all()

    def restart_all(self):
        for host in self.hosts:
            self.remote_connection = Connection(
                host,
                user=self.user,
                connect_kwargs={'password': self.user_password},
                config=self.remote_config
            )
            self._restart_all()

    def fast_deploy(self):
        for host in self.hosts:
            self.remote_connection = Connection(
                host,
                user=self.user,
                connect_kwargs={'password': self.user_password},
                config=self.remote_config
            )
            self._pull()
            self._restart_all()

    def _pull(self):
        self.local_context.run("git push origin master")
        with self.remote_connection.cd('~/projects/your_project_name'):
            self.remote_connection.run("git checkout master")
            self.remote_connection.run("git pull origin master")

    def _migrate(self):
        with self.remote_connection.cd("~/projects/your_project_name"):
            self._virtualenv("pip install -r requirements.txt")
            #virtualenv("python manage.py makemigrations")
            self._virtualenv("python manage.py migrate")
            self._virtualenv("python manage.py collectstatic --noinput")

    def _virtualenv(self, command):
        source = 'source {}/bin/activate && '.format(self.virtualenv_root)
        self.remote_connection.run(source + command)

    def _restart_all(self):
        #run('sudo supervisorctl restart celery_worker')
        self.remote_connection.sudo(
            'supervisorctl reload {}'.format(self.supervisor_process_name))
        #run('sudo systemctl restart redis')
        self.remote_connection.sudo('service nginx restart')

