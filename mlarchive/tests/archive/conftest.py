# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
import pytest
from factories import EmailListFactory, ThreadFactory, MessageFactory
from StringIO import StringIO
from django.conf import settings
from django.core.management import call_command
from mlarchive.archive.management.commands._classes import get_base_subject
from mlarchive.archive.models import Message, Thread

# `pytest` automatically calls this function once when tests are run.

'''
def pytest_configure(tmpdir_factory):
    DATA_ROOT = str(tmpdir_factory.mktemp('data'))
    settings.DATA_ROOT = DATA_ROOT
    settings.ARCHIVE_DIR = os.path.join(DATA_ROOT,'archive')
    # If you have any test specific settings, you can declare them here,
    # e.g.
    # settings.PASSWORD_HASHERS = (
    #     'django.contrib.auth.hashers.MD5PasswordHasher',
    # )
    django.setup()
    # Note: In Django =< 1.6 you'll need to run this instead
    # settings.configure()
'''


def load_db():
    pubone = EmailListFactory.create(name='pubone')
    pubtwo = EmailListFactory.create(name='pubtwo')
    pubthree = EmailListFactory.create(name='pubthree')
    private = EmailListFactory.create(name='private', private=True)
    athread = ThreadFactory.create(date=datetime.datetime(2013, 1, 1))
    bthread = ThreadFactory.create(date=datetime.datetime(2013, 2, 1))
    MessageFactory.create(email_list=pubone,
                          frm='Björn',
                          thread=athread,
                          subject='Another message about RFC6759',
                          msgid='a01',
                          date=datetime.datetime(2013, 1, 1))
    MessageFactory.create(email_list=pubone,
                          thread=bthread,
                          subject='BBQ Invitation',
                          base_subject=get_base_subject('BBQ Invitation'),
                          date=datetime.datetime(2013, 2, 1),
                          msgid='a02',
                          to='to@amsl.com')
    MessageFactory.create(email_list=pubone,
                          thread=bthread,
                          subject='Re: draft-ietf-dnssec-secops',
                          base_subject=get_base_subject('Re: draft-ietf-dnssec-secops'),
                          msgid='a03',
                          date=datetime.datetime(2013, 3, 1))
    MessageFactory.create(email_list=pubone,
                          thread=athread,
                          frm='larry@amsl.com',
                          subject='[RE] BBQ Invitation things',
                          base_subject=get_base_subject('[RE] BBQ Invitation things'),
                          date=datetime.datetime(2014, 1, 1),
                          msgid='a04',
                          spam_score=1)
    MessageFactory.create(email_list=pubtwo)
    MessageFactory.create(email_list=pubtwo)
    date = datetime.datetime.now().replace(second=0, microsecond=0)
    for n in range(21):
        MessageFactory.create(email_list=pubthree, date=date - datetime.timedelta(days=n))

    # add thread view messages
    # NOTE: thread_order 1 has later date
    apple = EmailListFactory.create(name='apple')
    cthread = ThreadFactory.create(date=datetime.datetime(2017, 1, 1))
    MessageFactory.create(email_list=apple,
                          thread=cthread,
                          subject='New Topic',
                          thread_order=0,
                          date=datetime.datetime(2017, 1, 1))
    MessageFactory.create(email_list=apple,
                          thread=cthread,
                          subject='Re: New Topic',
                          thread_order=5,
                          date=datetime.datetime(2017, 1, 2))
    MessageFactory.create(email_list=apple,
                          thread=cthread,
                          subject='Re: New Topic',
                          thread_order=2,
                          date=datetime.datetime(2017, 1, 3))
    MessageFactory.create(email_list=apple,
                          thread=cthread,
                          subject='Re: New Topic',
                          thread_order=3,
                          date=datetime.datetime(2017, 1, 4))
    MessageFactory.create(email_list=apple,
                          thread=cthread,
                          subject='Re: New Topic',
                          thread_order=4,
                          date=datetime.datetime(2017, 1, 5))
    MessageFactory.create(email_list=apple,
                          thread=cthread,
                          subject='Re: New Topic',
                          thread_order=1,
                          date=datetime.datetime(2017, 1, 6))
    MessageFactory.create(email_list=private, date=datetime.datetime(2017, 1, 1))
    MessageFactory.create(email_list=private, date=datetime.datetime(2017, 1, 2))

    # listnames with hyphen
    devops = EmailListFactory.create(name='dev-ops')
    MessageFactory.create(email_list=devops)

    privateops = EmailListFactory.create(name='private-ops', private=True)
    MessageFactory.create(email_list=privateops)


@pytest.fixture(scope="session")
def index_resource():
    if not Message.objects.first():
        load_db()
    # build index
    content = StringIO()
    call_command('update_index', stdout=content)
    print content.read()

    def fin():
        call_command('clear_index', noinput=True, stdout=content)
        print content.read()


@pytest.fixture()
def messages(index_resource):
    """Load some messages into db and index for testing"""
    if not Message.objects.first():
        load_db()


@pytest.fixture()
def thread_messages():
    """Load some threads"""
    content = StringIO()
    path = os.path.join(settings.BASE_DIR, 'tests', 'data', 'thread.mail')
    call_command('load', path, listname='acme', summary=True, stdout=content)


@pytest.fixture()
def thread_messages_db_only():
    public = EmailListFactory.create(name='pubone')
    athread = ThreadFactory.create(date=datetime.datetime(2017, 1, 1))
    bthread = ThreadFactory.create(date=datetime.datetime(2017, 2, 1))
    cthread = ThreadFactory.create(date=datetime.datetime(2017, 3, 1))
    MessageFactory.create(email_list=public,
                          thread=athread,
                          thread_order=0,
                          msgid='x001',
                          date=datetime.datetime(2017, 1, 1))
    MessageFactory.create(email_list=public,
                          thread=athread,
                          thread_order=1,
                          msgid='x002',
                          date=datetime.datetime(2017, 2, 15))
    MessageFactory.create(email_list=public,
                          thread=athread,
                          thread_order=2,
                          msgid='x003',
                          date=datetime.datetime(2017, 1, 15))
    MessageFactory.create(email_list=public,
                          thread=bthread,
                          thread_order=0,
                          msgid='x004',
                          date=datetime.datetime(2017, 2, 1))
    MessageFactory.create(email_list=public,
                          thread=bthread,
                          thread_order=1,
                          msgid='x005',
                          date=datetime.datetime(2017, 3, 15))
    MessageFactory.create(email_list=public,
                          thread=cthread,
                          thread_order=0,
                          msgid='x006',
                          date=datetime.datetime(2017, 3, 1))
    MessageFactory.create(email_list=public,
                          thread=cthread,
                          thread_order=1,
                          msgid='x007',
                          date=datetime.datetime(2017, 3, 20))
    MessageFactory.create(email_list=public,
                          thread=cthread,
                          thread_order=2,
                          msgid='x008',
                          date=datetime.datetime(2017, 3, 10))

    # set first
    for thread in Thread.objects.all():
        thread.set_first()


@pytest.fixture(scope='session')
def tmp_dir(tmpdir_factory):
    """Create temporary directory for this test run"""
    tmpdir = tmpdir_factory.mktemp('data')
    return str(tmpdir)


@pytest.fixture()
def data_dir(tmp_dir, settings, autouse=True):
    """Set ARCHIVE_DIR to temporary directory"""
    DATA_ROOT = tmp_dir
    settings.DATA_ROOT = DATA_ROOT
    settings.ARCHIVE_DIR = os.path.join(DATA_ROOT, 'archive')


@pytest.fixture()
def query_messages(data_dir):
    """Load some threads"""
    content = StringIO()
    path = os.path.join(settings.BASE_DIR, 'tests', 'data', 'query_acme.mail')
    call_command('load', path, listname='acme', summary=True, stdout=content)
    path = os.path.join(settings.BASE_DIR, 'tests', 'data', 'query_star.mail')
    call_command('load', path, listname='star', summary=True, stdout=content)
