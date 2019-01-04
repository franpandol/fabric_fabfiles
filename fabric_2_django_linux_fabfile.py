#!/usr/bin/python
from fabric import Connection, Config
import invoke
from invoke import task
import os
import time


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

hosts = ["your_host_ip"]
user = "serveruser"
virtualenv_root = '~/.virtualenvs/your_project_name'
virtualenv_root_local = '~/virtualenvs/your_project_name'
project_name = "your_project_name"
webapps_password = ""
psql_user = "postgres_user"
psql_database_name = "postgres_database_name"
psql_password = "postgres_user_password"
supervisor_process_name = "your_project_name"
bitbucket_user = ""
bitbucket_url = "https://{}@bitbucket.org/your_user/your_project_name.git".format(
    bitbucket_user)

remote_config = Config(overrides={'sudo': {'password': 'root_password'}})
remote_connection = Connection(hosts[0], user=user, connect_kwargs={
                               'password': 'root_password'}, config=remote_config)

local_config = invoke.config.Config(project_location=BASE_DIR)
local_context = invoke.context.Context(config=local_config)


# TODO Creamos un usuario y lo agregamos al grupo sudo
# $ adduser serveruser
# Le asignamos un password.

# Adding user webapps to group sudo
# $ gpasswd -a serveruser sudo
# su serveruser

@task
def update_system(local_context):
    remote_connection.sudo("apt-get install aptitude")
    remote_connection.sudo("aptitude -y update")
    remote_connection.sudo("aptitude -y upgrade")


@task
def create_virtualenv(local_context):
    remote_connection.sudo("aptitude install -y python-virtualenv")
    remote_connection.sudo("aptitude install -y build-essential")
    remote_connection.sudo("aptitude install -y python3.5-dev")
    remote_connection.run("mkdir ~/.virtualenvs")
    remote_connection.run(
        "virtualenv -p `which python3` ~/.virtualenvs/{}".format(project_name))


@task
def install_postgresql(local_context):
    remote_connection.sudo(
        "aptitude install -y postgresql postgresql-contrib postgresql-server-dev-9.5")
    remote_connection.sudo("aptitude install -y postgresql-9.5-postgis-2.0")


@task
def install_gunicorn(local_context):
    virtualenv("pip install gunicorn")


@task
def install_supervisor(local_context):
    remote_connection.sudo("aptitude install -y supervisor")


@task
def install_supervisor(local_context):
    remote_connection.sudo("aptitude install -y nginx")
    remote_connection.run("touch ~/logs/nginx-access.log")
    remote_connection.run("touch ~/logs/nginx-error.log")


@task
def install_bower(local_context):
    remote_connection.sudo("aptitude install -y nodejs", warn=True)
    remote_connection.sudo("aptitude install -y npm", warn=True)
    remote_connection.sudo("ln -s /usr/bin/nodejs /usr/bin/node")
    remote_connection.sudo("npm -g install bower")
    remote_connection.run("touch ~/projects/your_project_name/components/")
    with remote_connection.cd("~/projects/your_project_name"):
        virtualenv("python manage.py bower install")
        virtualenv("python manage.py collectstatic --noinput")


@task
def create_psql_user(local_context):
    remote_connection.sudo(
        'psql -U postgres -c "CREATE ROLE {0} LOGIN PASSWORD  \'{1}\'  NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;"'.format(psql_user, psql_password), warn=True)
    remote_connection.sudo('psql -U postgres -c "CREATE DATABASE {0} WITH OWNER {1};"'.format(
        psql_database_name, psql_user), warn=True)
    remote_connection.sudo(
        'psql -U postgres -c "CREATE EXTENSION postgis;"', warn=True)


@task
def db(local_context):
    virtualenv_local("python manage.py makemigrations", local_context)
    virtualenv_local("python manage.py migrate", local_context)
    virtualenv_local("python manage.py collectstatic --noinput", local_context)


def virtualenv_local(command, local_context):
    source = 'source {}/bin/activate && '.format(virtualenv_root_local)
    local_context.run(source + command)


@task
def pull(local_context):
    local_context.run("git push origin master")
    with remote_connection.cd('~/projects/your_project_name'):
        remote_connection.run("git pull origin master")


@task
def restart_all(local_context):
    run('sudo supervisorctl restart celery_worker')
    remote_connection.sudo(
        'supervisorctl reload {}'.format(supervisor_process_name))
    run('sudo systemctl restart redis')
    remote_connection.sudo('service nginx restart')


@task
def migrate(local_context):
    with remote_connection.cd("~/projects/your_project_name"):
        virtualenv("pip install -r requirements.txt")
        virtualenv("python manage.py makemigrations")
        virtualenv("python manage.py migrate")
        virtualenv("python manage.py collectstatic --noinput")


def virtualenv(command):
    source = 'source {}/bin/activate && '.format(virtualenv_root)
    remote_connection.run(source + command)


def load_initial_data(local_context):
    with remote_connection.cd('/home/webapps/projects/your_project_name/'):
        virtualenv("python manage.py loaddata all")


def restore_db(database_name):
    with remote_connection.cd('/home/webapps/projects/your_project_name/'):
        virtualenv("python manage.py migrate")
        load_initial_data()


def run_tests():
    with remote_connection.cd('/home/webapps/projects/your_project_name/'):
        virtualenv(
            "pytest --cov-report term-missing --cov=api.views --reuse-db")


@task
def backup_database(local_context):
    timestr = time.strftime("%Y%m%d-%H%M%S")
    filename = timestr + '.sql'
    folder = os.path.join(BASE_DIR, "your_project_name/backups/")
    custom_command = "/usr/local/bin/pg_dump --format c --file {} -U {} "\
        " -O --disable-triggers {}".format(
            folder + filename,
            "postgres",
            "your_project_name"
        )
    local_context.run(custom_command, warn=True)


@task
def deploy(local_context):
    pull(local_context)
    migrate(local_context)
    restart_all(local_context)


@task
def fast_deploy(local_context):
    pull(local_context)
    # migrate(local_context)
    restart_all(local_context)


@task
def fd(local_context):
    fast_deploy(local_context)
