# AWS client for deployment
import os.path
import hashlib

from boto import beanstalk, s3
from boto.s3.key import Key
from boto.exception import S3CreateError

from . import git


class Client(object):
    """High level interface into deploying in beanstalk"""

    def __init__(self, region):
        self.s3 = S3Client(region)
        self.beanstalk = BeanstalkClient(region)
        self.application_name = git.get_application_name()
        print("Application name: {}".format(self.application_name))

    def bootstrap(self):
        """Bootstrap a new application"""
        self.s3.create_bucket(self.application_name)
        self.beanstalk.create_application(self.application_name)
        version_label = self.create_version(
            'initial',
            description='Initial code version for bootstrap')
        for environment_name in ['staging', 'production']:
            self.beanstalk.create_environment(
                self.application_name, environment_name, version_label)

    def create_version(self, version_label, with_sha=False, description=''):
        sha, package_path = git.create_package()
        s3_bucket, s3_key = self.s3.upload_package(
            self.application_name, package_path)
        if with_sha:
            version_label = '{}-{}'.format(version_label, sha)
        self.beanstalk.create_application_version(
            self.application_name, version_label,
            s3_bucket, s3_key,
            description)
        return version_label

    def deploy_to_branch_environment(self, branch):
        environment_name = 'dev-{}'.format(branch)
        version_label = self.create_version(environment_name, with_sha=True)
        self.beanstalk.create_or_update_environment(
            self.application_name, environment_name, version_label)

    def terminate_branch_environment(self, branch):
        environment_name = 'dev-{}'.format(branch)
        self.beanstalk.terminate_environment(
            self.application_name, environment_name)

    def deploy(self, version_label, environment_name):
        self.beanstalk.update_environment(
            self.application_name, environment_name, version_label)


class S3Client(object):
    def __init__(self, region, **kwargs):
        self._region = region
        self._options = kwargs
        self._connection = self._get_connection(region)

    def _get_connection(self, region):
        return s3.connect_to_region(region)

    def create_bucket(self, application_name):
        if self._region.startswith('eu'):
            location = 'EU'
        else:
            location = ''
        try:
            self._connection.create_bucket(application_name, location=location)
        except S3CreateError as e:
            if 'BucketAlreadyOwnedByYou' != e.error_code:
                raise

    def upload_package(self, application_name, package_path):
        bucket = self._connection.get_bucket(application_name)
        key = Key(bucket)
        key.key = os.path.basename(package_path)
        key.set_contents_from_filename(package_path)

        return application_name, key.key


class SomeException(Exception):
    pass


DEFAULT_SOLUTION_STACK = '64bit Amazon Linux 2014.03 v1.0.9 running Python 2.7'


class BeanstalkClient(object):

    def __init__(self, region, **kwargs):
        self._region = region
        self._options = kwargs
        self._connection = self._get_connection(region)

    @property
    def solution_stack_name(self):
        return self._options.get(
            'solution_stack_name', DEFAULT_SOLUTION_STACK)

    def _get_connection(self, region):
        return beanstalk.connect_to_region(region)

    def create_application(self, application_name):
        # Will fail if application exists
        self._connection.create_application(application_name)

    def create_environment(self, application_name, environment_name,
                           version_label):
        environment_name = self._environment_name(
            application_name, environment_name)
        self._connection.create_environment(
            application_name, environment_name, version_label,
            solution_stack_name=self.solution_stack_name)

    def _environment_name(self, application_name, environment_name):
        """Return an environment name

        Generate an environment name from the application name and
        an environment name. Amazon Beanstalk requires environment names to
        be unique across applications so the application name must be
        encoded into the environment name.
        """
        return '{}-{}'.format(
            hashlib.sha1(application_name).hexdigest()[:5],
            environment_name)

    def update_environment(self, application_name, environment_name,
                           version_label):
        environment_name = self._environment_name(
            application_name, environment_name)
        self._connection.update_environment(
            environment_name=environment_name,
            version_label=version_label)

    def create_or_update_environment(self, application_name, environment_name,
                                     version_label):
        try:
            self.create_environment(
                application_name, environment_name, version_label)
        except SomeException:
            self.update_environment(
                application_name, environment_name, version_label)

    def terminate_environment(self, application_name, environment_name):
        environment_name = self._environment_name(
            application_name, environment_name)
        self._connection.terminate_environment(
            environment_name=environment_name)

    def create_application_version(self, application_name, version_label,
                                   s3_bucket, s3_key, description):
        self._connection.create_application_version(
            application_name, version_label,
            s3_bucket=s3_bucket, s3_key=s3_key,
            description=description)
