# Command line interface to deployment
from __future__ import print_function
import sys

import argh

from digitalmarketplace.deploy import aws, git


def bootstrap(region=None):
    """Create a new application with associated S3 bucket and core environments"""
    aws.get_client(region).bootstrap()


def create_version(version_label, region=None):
    """Create a new version of the application from the current HEAD"""
    aws.get_client(region).create_version(version_label)


def deploy_to_branch_environment(branch=None, region=None):
    """Deploy the current HEAD to a temporary branch environment"""
    if branch is None:
        branch = git.get_current_branch()
    aws.get_client(region).deploy_to_branch_environment(branch)


def terminate_branch_environment(branch=None, region=None):
    """Terminate a temporary branch environment"""
    if branch is None:
        branch = git.get_current_branch()
    aws.get_client(region).terminate_branch_environment(branch)


def deploy_to_staging(version_label, region=None):
    """Deploy a previously created version to the staging environment"""
    aws.get_client(region).deploy(version_label, 'staging')


def deploy_to_production(version_label, region=None):
    """Deploy a previously created version to the production environment"""
    aws.get_client(region).deploy(version_label, 'production')


def main():
    parser = argh.ArghParser()
    parser.add_argument('--region', default='eu-west-1')
    parser.add_commands([
        bootstrap,
        create_version,
        deploy_to_branch_environment,
        terminate_branch_environment,
        deploy_to_staging,
        deploy_to_production])
    try:
        parser.dispatch()
    except aws.AWSError as e:
        print(e.message, file=sys.stderr)
        sys.exit(1)
