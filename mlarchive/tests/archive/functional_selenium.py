'''Selenium Functional Tests'''

import urlparse
import pytest

from importlib import import_module
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from pyquery import PyQuery
from selenium.webdriver.phantomjs.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from mlarchive.archive.models import Message


timeout = 10


def force_login(user, driver, base_url):
    from django.conf import settings
    SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
    selenium_login_start_page = getattr(settings, 'SELENIUM_LOGIN_START_PAGE', '/page_404/')
    driver.get('{}{}'.format(base_url, selenium_login_start_page))

    session = SessionStore()
    session[SESSION_KEY] = user.id
    session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    domain = base_url.split(':')[-2].split('/')[-1]
    cookie = {
        'name': settings.SESSION_COOKIE_NAME,
        'value': session.session_key,
        'path': '/',
        'domain': domain
    }

    cookies = driver.get_cookies()
    print cookies

    driver.add_cookie(cookie)
    driver.refresh()


class MySeleniumTests(StaticLiveServerTestCase):
    '''Selenium functional test cases'''
    @classmethod
    def setUpClass(cls):
        super(MySeleniumTests, cls).setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.set_window_size(1400, 1000)
        # cls.selenium.PhantomJS(service_log_path='tests/tmp/ghostdriver.log')

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(MySeleniumTests, cls).tearDownClass()

    # TEST MESSAGE VIEW NAVIGAIONS

    @pytest.mark.usefixtures("thread_messages")
    def test_message_detail_next_list(self):
        '''Test next message in list button of message detail'''
        messages = Message.objects.all().order_by('date')
        url = urlparse.urljoin(self.live_server_url, messages[0].get_absolute_url())
        self.selenium.get(url)
        self.selenium.find_element_by_id('next-in-list').click()

        # Wait until the response is received
        WebDriverWait(self.selenium, timeout).until(
            lambda driver: driver.find_element_by_tag_name('body'))

        # Get results page
        # print self.selenium.page_source
        self.selenium.get_screenshot_as_file('tests/tmp/test_message_detail_next_list.png')
        self.assertIn('Archive', self.selenium.title)
        self.assertIn(messages[1].msgid, self.selenium.page_source)

    @pytest.mark.usefixtures("thread_messages")
    def test_message_detail_previous_list(self):
        '''Test previous message in list button of message detail'''
        messages = Message.objects.all().order_by('date')
        self.assertEqual(len(messages), 4)
        url = urlparse.urljoin(self.live_server_url, messages[1].get_absolute_url())
        self.selenium.get(url)
        self.selenium.find_element_by_id('previous-in-list').click()

        # Wait until the response is received
        WebDriverWait(self.selenium, timeout).until(
            lambda driver: driver.find_element_by_tag_name('body'))

        # Get results page
        # print self.selenium.page_source
        self.selenium.get_screenshot_as_file('tests/tmp/test_message_detail_previous_list.png')
        self.assertIn('Archive', self.selenium.title)
        self.assertIn(messages[0].msgid, self.selenium.page_source)

    @pytest.mark.usefixtures("thread_messages")
    def test_message_detail_next_search(self):
        '''Test next message in search results button of message detail'''
        # perform regular search
        url = reverse('archive_search') + '?q=anvil'
        url = urlparse.urljoin(self.live_server_url, url)
        self.selenium.get(url)
        q = PyQuery(self.selenium.page_source)
        assert len(q('.xtr')) == 4
        second_row = q('.xtr:nth-child(2)')
        message_url = second_row.find('.xtd.url-col')
        next_message_url = message_url.text()

        # navigate to first message detail
        elements = self.selenium.find_elements_by_css_selector("a.msg-detail")
        elements[0].click()

        # Wait until the response is received
        WebDriverWait(self.selenium, timeout).until(
            lambda driver: driver.find_element_by_tag_name('body'))

        # click next in search button
        self.selenium.find_element_by_id('next-in-search').click()

        # Wait until the response is received
        WebDriverWait(self.selenium, timeout).until(
            lambda driver: driver.find_element_by_tag_name('body'))

        print self.selenium.current_url
        self.assertIn(next_message_url, self.selenium.current_url)

    @pytest.mark.usefixtures("thread_messages")
    def test_message_detail_toggle_nav(self):
        '''Test toggle navigation bar feature of message detail'''
        message = Message.objects.first()
        url = urlparse.urljoin(self.live_server_url, message.get_absolute_url())
        self.selenium.get(url)

        # navbar is there
        element = self.selenium.find_element_by_class_name('navbar-msg-detail')
        assert element.is_displayed()

        # click hide
        self.selenium.find_element_by_link_text('Hide Navigation Bar').click()

        # navbar is gone
        element = self.selenium.find_element_by_class_name('navbar-msg-detail')
        assert not element.is_displayed()

        # click to show
        self.selenium.find_element_by_link_text('Show Navigation Bar').click()

        # navbar is there
        element = self.selenium.find_element_by_class_name('navbar-msg-detail')
        assert element.is_displayed()

    @pytest.mark.usefixtures("thread_messages")
    def test_message_detail_toggle_msg_header(self):
        '''Test toggle message header feature of message detail'''
        message = Message.objects.first()
        url = urlparse.urljoin(self.live_server_url, message.get_absolute_url())
        self.selenium.get(url)

        # header is hidden
        element = self.selenium.find_element_by_id('msg-header')
        assert not element.is_displayed()

        # click show
        self.selenium.find_element_by_link_text('Show header').click()

        # header is visible
        self.selenium.get_screenshot_as_file('tests/tmp/test_message_detail_toggle_msg_header.png')
        element = self.selenium.find_element_by_id('msg-header')
        assert element.is_displayed()

        # click to hide
        self.selenium.find_element_by_link_text('Hide header').click()

        # header is hidden
        element = self.selenium.find_element_by_id('msg-header')
        assert not element.is_displayed()


"""
class AdminSeleniumTests(StaticLiveServerTestCase):
    '''Selenium functional test cases'''
    @classmethod
    def setUpClass(cls):
        super(AdminSeleniumTests, cls).setUpClass()
        from selenium.webdriver.chrome.webdriver import WebDriver
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.set_window_size(1400, 1000)

        User.objects.create_superuser(username='admin',
                                      password='password',
                                      email='admin@example.com')


    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(AdminSeleniumTests, cls).tearDownClass()

    @pytest.mark.usefixtures("thread_messages", "admin_user")
    def test_admin_spam_mode(self):
        '''Test Spam Mode of admin view'''
        email_list = EmailList.objects.first()
        admin_url = reverse('archive_admin') + '?email_list=' + str(email_list.pk)
        url = urlparse.urljoin(self.live_server_url, admin_url)
        user = User.objects.get(username='admin')
        force_login(user, self.selenium, self.live_server_url)
        self.selenium.get(url)

        # spam tabs are hidden
        self.selenium.get_screenshot_as_file('tests/tmp/test_admin_spam_mode.png')
        element = self.selenium.find_element_by_class_name('nav-tabs')
        assert not element.is_displayed()

        self.selenium.find_element_by_id('spam-toggle').click()

        # spam tabs displayed
        element = self.selenium.find_element_by_class_name('nav-tabs')
        assert element.is_displayed()
"""
