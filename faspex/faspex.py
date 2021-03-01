import os
import shutil
import subprocess
from HTMLParser import HTMLParser

from bs4 import BeautifulSoup


class FaspexCLI(object):

    def __init__(self, user, password, url, url_prefix='aspera/faspex', aspera_executable_path=None):
        self.user = user
        self.password = password
        self.url = url
        self.url_prefix = url_prefix
        self.aspera_executable_path = aspera_executable_path or shutil.which('aspera')

    def send_package(self, filepath, title, recipients, note=None, file_encrypt_password=None, cc_on_upload=None,
                     cc_on_download=None):
        if not os.path.exists(filepath):
            raise IOError('Filepath could not be found: {}'.format(filepath))
        elif not recipients:
            raise ValueError('You must provide a list of recipients')
        elif not title:
            raise ValueError('You must provide a title')

        flags = ['--file', filepath, '--title', title]

        recipient_flags = self._get_list_flags('--recipient', recipients)
        cc_on_upload_flags = self._get_list_flags('--cc-on-upload', cc_on_upload)
        cc_on_download_flags = self._get_list_flags('--cc-on-download', cc_on_download)

        flags += recipient_flags + cc_on_upload_flags + cc_on_download_flags

        if note:
            flags += ['--note', note]
        if file_encrypt_password:
            self._set_aspera_scp_filepass(file_encrypt_password)
            flags.append('--file-encrypt')

        cmd = self._build_cmd('send', flags)
        self._call_faspex(cmd)

    @staticmethod
    def _get_list_flags(flag_name, flag_values):
        flags = []
        if flag_values:
            for val in flag_values:
                flag = [flag_name, val]
                flags += flag
        return flags

    @staticmethod
    def _set_aspera_scp_filepass(password):
        os.environ['ASPERA_SCP_FILEPASS'] = str(password)

    def download_package(self):
        raise NotImplementedError

    def list_inbox_packages(self):
        return self._list_packages('inbox')

    def list_sent_packages(self):
        return self._list_packages('sent')

    def list_archived_packages(self):
        return self._list_packages('archived')

    def _list_packages(self, mailbox):
        if mailbox not in ['inbox', 'sent', 'archived']:
            raise ValueError('mailbox must be either inbox, sent, or archived')
        flags = ['--xml', '--{}'.format(mailbox)]
        cmd = self._build_cmd('list', flags)
        response, errors = self._call_faspex(cmd)
        return self._parse_list_packages_xml_response(response)

    def _parse_list_packages_xml_response(self, xml):
        packages = []
        xml = xml[xml.index('<'):]
        soup = BeautifulSoup(xml, 'xml')
        entries = soup.find_all('entry')
        if not entries:
            return None
        html_parser = HTMLParser()
        for entry in entries:
            package = {
                'title': self._get_standard_child(entry, 'title'),
                'delivery_id': int(self._get_standard_child(entry, 'package:delivery_id')),
                'download_link': html_parser.unescape(entry.findChild('link', {'rel': 'package'})['href']),
                'enclosure_link': html_parser.unescape(entry.findChild('link', {'rel': 'enclosure'})['href']),
                'attention_to': entry.findChild('metadata').findChild('field', {'name': 'Attention To:'}).text,
                'uuid': self._get_standard_child(entry, 'id'),
                'sequence_id': self._get_standard_child(entry, 'sequence_id'),
                'published_timestamp': self._get_standard_child(entry, 'published'),
                'updated_timestamp': self._get_standard_child(entry, 'updated'),
                'completed_timestamp': self._get_standard_child(entry, 'completed'),
                'author': self._get_entry_author(entry),
                'recipients': self._get_entry_recipients(entry),
                'parent_delivery_id': self._get_standard_child(entry, 'package:parent_delivery_id'),
            }
            packages.append(package)
        return packages

    def _get_entry_author(self, entry):
        author = entry.findChild('author')
        return {
            'name': self._get_standard_child(author, 'name'),
            'email': self._get_standard_child(author, 'email')
        }

    def _get_entry_recipients(self, entry):
        recipient_list = []
        recipients = entry.find_all('package:to')
        for recipient in recipients:
            data = {
                'name': self._get_standard_child(recipient, 'package:name'),
                'email': self._get_standard_child(recipient, 'package:email'),
                'delivery_id': self._get_standard_child(recipient, 'package:recipient_delivery_id')
            }
            recipient_list.append(data)
        return recipient_list

    @staticmethod
    def _get_standard_child(entry, tag):
        return entry.findChild(tag).text

    def _build_cmd(self, sub_command, flags=None):
        cmd = [self.aspera_executable_path, 'faspex', sub_command, '--host', self.url, '--username', self.user,
               '--password', self.password, '-U', self.url_prefix]
        if flags:
            cmd += flags
        return [str(i) for i in cmd]

    @staticmethod
    def _call_faspex(cmd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=False
        )
        stdout, stderr = process.communicate()
        return stdout, stderr
